#! /usr/bin/env python3

import sys
import math
import time
import socket
import struct
import ssl
import websockets
import asyncio
import json

from smbus2 import SMBus, i2c_msg

cur_framenum = 0
cur_img_for_web = [0] * 768

wss_port = 18801


bus = SMBus(1)

cam_addr = 0x33

def i2c_read(addr, count):
    wr = i2c_msg.write(cam_addr, 
                       [(addr >> 8) & 0xff, 
                        addr & 0xff])
    rd = i2c_msg.read(cam_addr, count * 2)
    bus.i2c_rdwr(wr, rd)
    ret = list()
    hilo = True
    for val in rd:
        if hilo:
            hi = val
            hilo = False
        else:
            ret.append((hi << 8) | val)
            hilo = True
    return ret
            
def i2c_write(addr, val):
    wr = i2c_msg.write(cam_addr, [(addr >> 8) & 0xff, 
                                  addr & 0xff,
                                  (val >> 8) & 0xff,
                                  val & 0xff])
    bus.i2c_rdwr(wr)

params = dict()

eedata = None

def sext(val, sign):
    if val & sign:
        val -= 2 * sign
    return val




SCALEALPHA = 0.000001


def extract_easy_params():
    params['kVdd'] = sext((eedata[0x33] >> 8) & 0xff, 0x80) * 32
    params['vdd25'] = ((eedata[0x33] & 0xff) - 256) * 32 - 8192

    params['KvPTAT'] = sext((eedata[0x32] >> 10) & 0x3f, 0x20) / 4096.0
    params['KtPTAT'] = sext(eedata[0x32] & 0x3ff, 0x200) / 8.0
    params['vPTAT25'] = eedata[0x31]
    params['alphaPTAT'] = (eedata[0x10] >> 12) / 4.0 + 8

    params['gainEE'] = sext(eedata[0x30], 0x8000)

    params['tgc'] = sext(eedata[0x3c] & 0xff, 0x80) / 32.0

    params['resolutionEE'] = (eedata[0x38] >> 12) & 3

    params['KsTa'] = sext ((eedata[0x3c] >> 8) & 0xff, 0x80) / 8192.0

    step = ((eedata[0x3f] >> 12) & 3) * 10

    ct = dict()
    ct[0] = -40
    ct[1] = 0
    ct[2] = ((eedata[0x3f] >> 4) & 0xf) * step
    ct[3] = ct[2] + ((eedata[0x3f] >> 8) & 0xf) * step
    ct[4] = 400
    params['ct'] = ct

    KsToScale = 1.0 * (1 << ((eedata[0x3f] & 0xf) + 8))

    ksTo = dict()
    ksTo[0] = sext(eedata[0x3d] & 0xff, 0x80) / KsToScale
    ksTo[1] = sext((eedata[0x3d] >> 8) & 0xff, 0x80) / KsToScale
    ksTo[2] = sext(eedata[0x3e] & 0xff, 0x80) / KsToScale
    ksTo[3] = sext((eedata[0x3e] >> 8) & 0xff, 0x80) / KsToScale
    ksTo[4] = -0.0002
    params['ksTo'] = ksTo

    cpOffset = dict()
    cpOffset[0] = sext(eedata[0x3a] & 0x3ff, 512)
    cpOffset[1] = sext((eedata[0x3a] >> 10) & 0x3f, 32) + cpOffset[0]
    params['cpOffset'] = cpOffset

    alpha_scale = ((eedata[0x20] >> 12) & 0xf) + 27
    alpha_factor = pow(2, alpha_scale)
    cpAlpha = dict()
    cpAlpha[0] = sext (eedata[0x39] & 0x3ff, 512) * alpha_factor
    cpAlpha[1] = ((1 + sext (eedata[0x39] >> 10, 32) / 128.0) 
                  * cpAlpha[0])
    params['cpAlpha'] = cpAlpha

    val = sext(eedata[0x3b] & 0xff, 128)
    ktaScale1 = ((eedata[0x38] >> 4) & 0xf) + 8
    params['cpKta'] = val / pow(2, ktaScale1)

    val = sext((eedata[0x3b] >> 8) & 0xff, 128)
    kvScale = (eedata[0x38] >> 8) & 0xf
    params['cpKv'] = val / pow(2, kvScale)
    
def extract_alpha_params():
    accRemScale = eedata[0x20] & 0xf
    accColumnScale = (eedata[0x20] >> 4) & 0xf
    accRowScale = (eedata[0x20] >> 8) & 0xf
    # different from above!
    alphaScale = ((eedata[0x20] >> 12) & 0xf) + 30
    alphaRef = eedata[0x21]

    accRow = dict()
    for i in range(6):
        accRow[i*4] = sext(eedata[0x22 + i] & 0xf, 8)
        accRow[i*4 + 1] = sext((eedata[0x22 + i] >> 4) & 0xf, 8)
        accRow[i*4 + 2] = sext((eedata[0x22 + i] >> 8) & 0xf, 8)
        accRow[i*4 + 3] = sext((eedata[0x22 + i] >> 12) & 0xf, 8)
        
    accColumn = dict()
    for i in range(8):
        accColumn[i*4] = sext(eedata[0x28 + i] & 0xf, 8)
        accColumn[i*4 + 1] = sext((eedata[0x28 + i] >> 4) & 0xf, 8)
        accColumn[i*4 + 2] = sext((eedata[0x28 + i] >> 8) & 0xf, 8)
        accColumn[i*4 + 3] = sext((eedata[0x28 + i] >> 12) & 0xf, 8)
        
    alphaTemp = dict()
    for i in range(24):
        for j in range(32):
            p = 32 * i + j

            val = sext((eedata[0x40 + p] >> 4) & 0x3f, 32)
            val *= pow(2, accRemScale)
            
            val += (alphaRef 
                    + (accRow[i] << accRowScale) 
                    + (accColumn[j] << accColumnScale))
            val /= pow(2, alphaScale)
            val -= (params['tgc'] 
                    * (params['cpAlpha'][0] + params['cpAlpha'][1])/2)

            alphaTemp[p] = SCALEALPHA / val

    temp = max(alphaTemp.values())
    
    # reused again
    alphaScale = 0
    while temp < 32767.4:
        temp *= 2
        alphaScale += 1

    alpha_factor = pow(2, alphaScale)
    alpha = dict()
    for i in range(24*32):
        alpha[i] = math.floor(alphaTemp[i] * alpha_factor + 0.5)

    params['alpha'] = alpha
    params['alphaScale'] = alphaScale

def extract_offset_params():
    occRemScale = eedata[0x10] & 0xf
    occColumnScale = (eedata[0x10] >> 4) & 0xf
    occRowScale = (eedata[0x10] >> 8) & 0xf
    offsetRef = sext(eedata[0x11], 0x8000)

    occRow = dict()
    for i in range(6):
        p = i * 4
        occRow[p + 0] = sext(eedata[0x12 + i] & 0xf, 8)
        occRow[p + 1] = sext((eedata[0x12 + i] >> 4) & 0xf, 8)
        occRow[p + 2] = sext((eedata[0x12 + i] >> 8) & 0xf, 8)
        occRow[p + 3] = sext((eedata[0x12 + i] >> 12) & 0xf, 8)
        
    occColumn = dict()
    for i in range(8):
        p = i * 4
        occColumn[p + 0] = sext(eedata[0x18 + i] & 0xf, 8)
        occColumn[p + 1] = sext((eedata[0x18 + i] >> 4) & 0xf, 8)
        occColumn[p + 2] = sext((eedata[0x18 + i] >> 8) & 0xf, 8)
        occColumn[p + 3] = sext((eedata[0x18 + i] >> 12) & 0xf, 8)
        
    offset = dict()
    for i in range(24):
        for j in range(32):
            p = 32 * i + j
            val = sext((eedata[0x40 + p] >> 10) & 0x3f, 32)
            val *= 1 << occRemScale

            val += (offsetRef 
                    + (occRow[i] << occRowScale) 
                    + (occColumn[j] << occColumnScale))

            offset[p] = val

    params['offset'] = offset
            
def extract_kta_pixel_params():
    KtaRC = dict()
    
    KtaRoCo = sext((eedata[0x36] >> 8) & 0xff, 128)
    KtaRC[0] = KtaRoCo

    KtaReCo = sext(eedata[0x36] & 0xff, 128)
    KtaRC[2] = KtaReCo
    
    KtaRoCe = sext((eedata[0x37] >> 8) & 0xff, 128)
    KtaRC[1] = KtaRoCe

    KtaReCe = sext(eedata[0x37] & 0xff, 128)
    KtaRC[3] = KtaReCe

    ktaScale1 = ((eedata[0x38] >> 4) & 0xf) + 8
    ktaScale2 = eedata[0x38] & 0xf

    kta_factor1 = pow(2, ktaScale1)
    
    ktaTemp = dict()
    for i in range(24):
        for j in range(32):
            p = 32 * i + j
            split = 2*(p//32 - (p//64)*2) + p%2;

            val = sext((eedata[0x40 + p] >> 1) & 7, 4)
            val *= 1 << ktaScale2
            val += KtaRC[split]
            ktaTemp[p] = val / kta_factor1

    maxval = abs(ktaTemp[0])
    for _, val in ktaTemp.items():
        if abs(val) > maxval:
            maxval = abs(val)
    
    ktaScale1 = 0
    while maxval < 63.4:
        maxval *= 2
        ktaScale1 += 1
        
    factor = pow(2, ktaScale1)
    kta = dict()
    for i in range(24*32):
        temp = ktaTemp[i] * factor
        if temp < 0:
            kta[i] = math.floor(temp - 0.5)
        else:
            kta[i] = math.floor(temp + 0.5)
    
    params['kta'] = kta
    params['ktaScale'] = ktaScale1

def extract_kv_pixel_params():
    KvT = dict()
    
    KvRoCo = sext((eedata[0x34] >> 12) & 0xf, 8)
    KvT[0] = KvRoCo
    
    KvReCo = sext((eedata[0x34] >> 8) & 0xf, 8)
    KvT[2] = KvReCo

    KvRoCe = sext((eedata[0x34] >> 4) & 0xf, 8)
    KvT[1] = KvRoCe

    KvReCe = sext(eedata[0x34] & 0xf, 8)
    KvT[3] = KvReCe

    kvScale = (eedata[0x38] >> 8) & 0xf

    factor = pow(2, kvScale)
    
    kvTemp = dict()
    for i in range(24):
        for j in range(32):
            p = 32 * i + j
            split = 2*(p//32 - (p//64)*2) + p%2
            val = KvT[split]
            kvTemp[p] = val / factor
            
    maxval = abs(kvTemp[0])
    for _, val in kvTemp.items():
        if abs(val) > maxval:
            maxval = abs(val)

    kvScale = 0
    while maxval < 63.4:
        maxval *= 2
        kvScale += 1

    factor = pow(2, kvScale)
    kv = dict()
    for i in range(768):
        temp = kvTemp[i] * factor
        if temp < 0:
            kv[i] = math.floor(temp - 0.5)
        else:
            kv[i] = math.floor(temp + 0.5)

    params['kv'] = kv
    params['kvScale'] = kvScale
            
def extract_cilc_params():
    params['calibrationModeEE'] = ((eedata[0xa] >> 4) & 0x80) ^ 0x80

    ilChessC = dict()
    
    ilChessC[0] = sext(eedata[0x35] & 0x3f, 32) / 16.0
    ilChessC[1] = sext((eedata[0x35] >> 6) & 0x1f, 16) / 2.0
    ilChessC[2] = sext((eedata[0x35] >> 11) & 0x1f, 16) / 8.0

    params['ilChessC'] = ilChessC

def extract_deviating_pixels():
    brokenPixels = dict()
    outlierPixels = dict()
    
    brokenPixels = list()
    outlierPixels = list()
    
    for pixnum in range(24*32):
        if eedata[0x40 + pixnum] == 0:
            brokenPixels.append(pixnum)
        elif (eedata[0x40 + pixnum] & 1) != 0:
            outlierPixels.append(pixnum)

    params['brokenPixels'] = brokenPixels
    params['outlierPixels'] = outlierPixels


def extract_params():
    extract_easy_params()
    extract_alpha_params()
    extract_offset_params()
    extract_kta_pixel_params()
    extract_kv_pixel_params()
    extract_cilc_params()
    return extract_deviating_pixels()

def set_modes():
    refresh_rate = 2

    ret = i2c_read(0x800d, 1)
    val = ret[0]
    val &= ~(7 << 7)
    val |= refresh_rate << 7
    val |= 0x1000 # chess mode
    i2c_write(0x800d, val)

    ret = i2c_read(0x800d, 1)


def get_frame():
    vals = i2c_read(0x8000, 1)
    status_register = vals[0]
    if (status_register & 8) == 0:
        return None

    i2c_write(0x8000, 0x30)

    frame = i2c_read(0x400, 24*32)
    aux_data = i2c_read(0x700, 64)

    frame += aux_data

    vals = i2c_read(0x800d, 1)
    frame += vals # frame[832]
    frame += [status_register & 1] # frame[833]
    return frame

def get_Vdd(frame):
    vdd_raw = sext(frame[810], 0x8000)

    resolutionRam = (frame[832] >> 10) & 3
    resolutionCorrection = (pow(2, params['resolutionEE']) /
                            pow(2, resolutionRam))
    vdd = ((resolutionCorrection * vdd_raw - params['vdd25']) 
           / params['kVdd']) + 3.3
    return vdd

def get_Ta(frame):
    vdd = get_Vdd(frame)

    ptat = sext(frame[800], 0x8000)
    ptatArt_raw = sext(frame[768], 0x8000)
    ptatArt = (ptat / (ptat * params['alphaPTAT'] + ptatArt_raw)) * pow(2, 18)

    ta_raw = ptatArt / (1 + params['KvPTAT'] * (vdd - 3.3)) - params['vPTAT25']

    ta = ta_raw / params['KtPTAT'] + 25

    return ta
    
def calculate_To(frame, tr, img):
    subPage = frame[833]
    vdd = get_Vdd(frame)
    ta = get_Ta(frame)

    ta4 = (ta + 273.15);
    ta4 = ta4 * ta4;
    ta4 = ta4 * ta4;

    tr4 = (tr + 273.15);
    tr4 = tr4 * tr4;
    tr4 = tr4 * tr4;

    emissivity = 1
    taTr = tr4 - (tr4-ta4)/emissivity;

    ktaScale = pow(2, params['ktaScale'])
    kvScale = pow(2, params['kvScale'])
    alphaScale = pow(2, params['alphaScale'])
    
    alphaCorrR = dict()
    alphaCorrR[0] = 1 / (1 + params['ksTo'][0] * 40)
    alphaCorrR[1] = 1
    alphaCorrR[2] = 1 + params['ksTo'][1] * params['ct'][2]
    alphaCorrR[3] = alphaCorrR[2] * (1 + 
                                     params['ksTo'][2] * (params['ct'][3] - 
                                                          params['ct'][2]))
    
    # gain calculation
    gain = params['gainEE'] / sext(frame[778], 0x8000)
    
    # To calculation
    mode = (frame[832] >> 5) & 0x80
    
    irDataCP = dict()
    irDataCP[0] = sext(frame[776], 0x8000) * gain
    irDataCP[1] = sext(frame[808], 0x8000) * gain

    irDataCP[0] -= (params['cpOffset'][0] 
                    * (1 + params['cpKta'] * (ta - 25)) 
                    * (1 + params['cpKv'] * (vdd - 3.3)))

    if mode == params['calibrationModeEE']:
        irDataCP[1] -= (params['cpOffset'][1]
                        * (1 + params['cpKta'] * (ta - 25)) 
                        * (1 + params['cpKv'] * (vdd - 3.3)))
    else:
        irDataCP[1] -= ((params['cpOffset'][1] + params['ilChessC'][0]) 
                        * (1 + params['cpKta'] * (ta - 25)) 
                        * (1 + params['cpKv'] * (vdd - 3.3)))

    for pixelNumber in range(768):
        ilPattern = pixelNumber // 32 - (pixelNumber // 64) * 2 
        chessPattern = ilPattern ^ (pixelNumber - (pixelNumber//2)*2)

        conversionPattern = ((pixelNumber + 2) // 4 
                             - (pixelNumber + 3) // 4 
                             + (pixelNumber + 1) // 4 
                             - pixelNumber // 4) * (1 - 2 * ilPattern)
        
        if mode == 0:
          pattern = ilPattern; 
        else:
          pattern = chessPattern

        if pattern == frame[833]:
            irData = sext(frame[pixelNumber], 0x8000) * gain
            
            kta = params['kta'][pixelNumber]/ktaScale
            kv = params['kv'][pixelNumber]/kvScale

            irData -= (params['offset'][pixelNumber]
                       * (1 + kta*(ta - 25))
                       * (1 + kv*(vdd - 3.3)))
            
            if mode != params['calibrationModeEE']:
                irData += (params['ilChessC'][2] * (2 * ilPattern - 1)
                           - (params['ilChessC'][1] * conversionPattern))
    
            irData -= params['tgc'] * irDataCP[subPage]
            irData /= emissivity
            
            alphaCompensated = (SCALEALPHA
                                * alphaScale
                                / params['alpha'][pixelNumber]
                                * (1 + params['KsTa'] * (ta - 25)))
                        
            factor = (pow(alphaCompensated, 3) 
                      * (irData + alphaCompensated * taTr))
            Sx = pow(factor, 0.25) * params['ksTo'][1]
            
            To_prelim = pow(irData 
                            / (alphaCompensated 
                               * (1 - params['ksTo'][1] * 273.15)
                               + Sx) 
                            + taTr, 
                            0.25) - 273.15

            if isinstance(To_prelim, complex):
                To_prelim = 0

            if To_prelim < params['ct'][1]:
                To_range = 0;
            elif To_prelim < params['ct'][2]:
                To_range = 1;            
            elif To_prelim < params['ct'][3]:
                To_range = 2;            
            else:
                To_range = 3;            
            
            To = pow(irData 
                     / (alphaCompensated 
                        * alphaCorrR[To_range] 
                        * (1 + params['ksTo'][To_range]
                           * (To_prelim - params['ct'][To_range])))
                     + taTr, 
                     0.25) - 273.15

            if isinstance(To, complex):
                To = 25.0

            img[pixelNumber] = To

class pixavg:
    def __init__(self):
        self.acc = 0
        self.count = 0

    def addpix(self, img, row, col):
        if (0 <= row and row < 32
            and 0 <= col and col < 24):
            self.acc += img[row * 32 + col]
            self.count += 1
            
    def val(self):
        if self.count == 0:
            return 0
        return self.acc / self.count

def bad_pixels_correction(img, pixels):
    for pixnum in pixels:
        row = pixnum // 32
        col = pixnum % 32

        avg = pixavg()
        avg.addpix(img, row - 1, col - 1)
        avg.addpix(img, row - 1, col + 1)
        avg.addpix(img, row + 1, col - 1)
        avg.addpix(img, row + 1, col + 1)
        
        img[row * 32 + col ] = avg.val()
                

def cam_setup():
    global eedata
    eedata = i2c_read(0x2400, 832)
    extract_params()
    set_modes()
    global img
    img = [0.0]*768

def cam_get():
    frame = get_frame()
    if frame is None:
        return None

    ta = get_Ta(frame)
    calculate_To (frame, ta, img)
    bad_pixels_correction(img, params['brokenPixels'])
    bad_pixels_correction(img, params['outlierPixels'])
    global cur_framenum
    cur_framenum += 1

    global cur_img_for_web
    for pixnum in range(768):
        cur_img_for_web[pixnum] = math.floor(img[pixnum] * 9 / 5 + 32)

    return img

maddr = ("239.134.242.175", 63704)
IRMAGIC = 0x20200630

def net_setup():
    global udp_sock
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def net_send(img):
    max_in_pkt = (1400 - 14) // 4

    togo = 24*32

    offset = 0
    while togo > 0:
        thistime = togo
        if thistime > max_in_pkt:
            thistime = max_in_pkt

        magic = IRMAGIC
        width = 32
        height = 24
        start_row = offset // 32
        start_col = offset % 32
        npix = thistime
        pad = 0

        pkt = struct.pack(f"!IHHHHHH{thistime}f", magic, 
                          width, height, 
                          start_row, start_col, 
                          npix, pad,
                          *img[offset:offset+thistime])

        ret = udp_sock.sendto (pkt, maddr)

        togo -= thistime
        offset += thistime
        

async def collect_images():
    while True:
        img = cam_get()
        if img is not None:
            net_send(img)

        await asyncio.sleep(0.1)

async def send_images(websocket):
    remote = websocket.remote_address
    last_framenum = 0
    try:
        while True:
            if cur_framenum != last_framenum:
                last_framenum = cur_framenum
                msg = dict()
                msg['framenum'] = cur_framenum
                msg['img'] = cur_img_for_web
                await websocket.send(json.dumps(msg))
            await asyncio.sleep(.1)
    except websockets.exceptions.ConnectionClosed as err:
        print("client closed", remote)


async def wss_client(websocket, path):
    remote = websocket.remote_address
    print("new client", remote)

    await send_images(websocket)


def run():
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_context.load_cert_chain("/etc/apache2/wildcard.pacew.org.crt",
                                "/etc/apache2/wildcard.pacew.org.key")
    wss_server = websockets.serve(wss_client, 
                                    port=wss_port,
                                    ssl=ssl_context)

    print(f"wss port {wss_port}")

    asyncio.get_event_loop().run_until_complete(wss_server)
    asyncio.get_event_loop().run_until_complete(collect_images())
    asyncio.get_event_loop().run_forever()


def main():
    cam_setup()
    net_setup()
    
    if False:
        print("ready")
        while True:
            img = cam_get()
            if img is None:
                time.sleep(.1)
            else:
                print(img[0], img[1])
                net_send(img)
    else:
        run()


main()



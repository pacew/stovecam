#! /usr/bin/env python3

import sys
import math

from smbus2 import SMBus, i2c_msg

bus = SMBus(1)

cam_addr = 0x33

def i2c_read(addr, count):
    wr = i2c_msg.write(cam_addr, [(addr >> 8) & 0xff, addr & 0xff])
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

    ksto = dict()
    ksto[0] = sext(eedata[0x3d] & 0xff, 0x80) / KsToScale
    ksto[1] = sext((eedata[0x3d] >> 8) & 0xff, 0x80) / KsToScale
    ksto[2] = sext(eedata[0x3e] & 0xff, 0x80) / KsToScale
    ksto[3] = sext((eedata[0x3e] >> 8) & 0xff, 0x80) / KsToScale
    ksto[4] = -0.0002
    params['ksto'] = ksto

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

#    params['alpha'] = alpha
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
        for j in range(24):
            p = 32 * i + j
            val = sext((eedata[0x40 + p] >> 10) & 0x3f, 32)
            val *= 1 << occRemScale

            val += (offsetRef 
                    + (occRow[i] << occRowScale) 
                    + (occColumn[j] << occColumnScale))

            offset[p] = val

#    params['offset'] = offset
            
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
    
#    params['kta'] = kta
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

#    params['kv'] = kv
    params['kvScale'] = kvScale
            
    print(kv[0])
    print(kv[1])
    print(kv[2])
    print(kv[3])


def extract_params():
    extract_easy_params()
    extract_alpha_params()
    extract_offset_params()
    extract_kta_pixel_params()
    extract_kv_pixel_params()

eedata = i2c_read (0x2400, 832)
extract_params()
print(params)




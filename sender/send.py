#! /usr/bin/env python3

from smbus2 import SMBus, i2c_msg

bus = SMBus(1)

cam_addr = 0x33

def i2c_read(addr, count):
    wr = i2c_msg.write(cam_addr, [(addr >> 8) & 0xff, addr & 0xff])
    rd = i2c_msg.read(cam_addr, count)
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






def extract_params():
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
    
    accRemScale = eedata[0x20] & 0xf
    accColumnScale = (eedata[0x20] >> 4) & 0xf
    accRowScale = (eedata[0x20] >> 8) & 0xf
    # different from above!
    alpha_scale = ((eedata[0x20] >> 12) & 0xf) + 30
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
        
    
    
    

eedata = i2c_read (0x2400, 832)
extract_params()
print(params)



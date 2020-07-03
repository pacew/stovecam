/**
 * @copyright (C) 2017 Melexis N.V.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 *
 */
#include "MLX90640_I2C_Driver.h"
#include <unistd.h>
#include <stdio.h>
#include <fcntl.h>
#include <string.h>
#include <err.h>
#include <stdlib.h>
#include <sys/ioctl.h>
#include <sys/types.h>
#include <sys/stat.h>

#include <linux/i2c.h>
#include <linux/i2c-dev.h>

int i2c_fd = 0;
const char *i2c_device = "/dev/i2c-1";

void MLX90640_I2CInit()
{
}

int MLX90640_I2CRead(uint8_t slaveAddr, uint16_t startAddress, uint16_t nMemAddressRead, uint16_t *data)
{
  if(!i2c_fd){
    i2c_fd = open(i2c_device, O_RDWR);
  }

  uint16_t *p = data;
  int togo = nMemAddressRead;

  while (togo > 0) {
    int thistime = togo;
    if (thistime > 16)
      thistime = 16;

    unsigned char cmd[2] = {(unsigned char)(startAddress >> 8), 
			    (unsigned char)(startAddress & 0xFF)};
    unsigned char buf[1664];
    struct i2c_msg i2c_messages[2];
    struct i2c_rdwr_ioctl_data i2c_messageset[1];

    i2c_messages[0].addr = slaveAddr;
    i2c_messages[0].flags = 0;
    i2c_messages[0].len = 2;
    i2c_messages[0].buf = cmd;

    i2c_messages[1].addr = slaveAddr;
    i2c_messages[1].flags = I2C_M_RD | I2C_M_NOSTART;
    i2c_messages[1].len = thistime * 2;
    i2c_messages[1].buf = buf;

    i2c_messageset[0].msgs = i2c_messages;
    i2c_messageset[0].nmsgs = 2;

    memset(buf, 0, thistime * 2);

    if (ioctl(i2c_fd, I2C_RDWR, &i2c_messageset) < 0) {
      printf("I2C Read Error!\n");
      return -1;
    }

    for(int count = 0; count < thistime; count++){
      int i = count << 1;
      *p++ = ((uint16_t)buf[i] << 8) | buf[i+1];
    }

    togo -= thistime;
    startAddress += thistime;
  }

  return 0;
} 

void MLX90640_I2CFreqSet(int freq)
{
}

int MLX90640_I2CWrite(uint8_t slaveAddr, uint16_t writeAddress, uint16_t data)
{ 
  if(!i2c_fd){
    i2c_fd = open(i2c_device, O_RDWR);
  }

  unsigned char cmd[4] = {(unsigned char)(writeAddress >> 8), (unsigned char)(writeAddress & 0x00FF), (unsigned char)(data >> 8), (unsigned char)(data & 0x00FF)};

  struct i2c_msg i2c_messages[1];
  struct i2c_rdwr_ioctl_data i2c_messageset[1];

  i2c_messages[0].addr = slaveAddr;
  i2c_messages[0].flags = 0;
  i2c_messages[0].len = 4;
  i2c_messages[0].buf = cmd;

  i2c_messageset[0].msgs = i2c_messages;
  i2c_messageset[0].nmsgs = 1;

  if (ioctl(i2c_fd, I2C_RDWR, &i2c_messageset) < 0) {
    printf("I2C Write Error!\n");
    return -1;
  }

  return 0;
}

int MLX90640_I2CGeneralReset(void)
{
  return (0);
}


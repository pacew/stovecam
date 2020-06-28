#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <fcntl.h>
#include <memory.h>
#include <sys/ioctl.h>

#include <i2c/smbus.h>
#include <linux/i2c-dev.h>

#include "i2c.h"

int i2c_fd;

void
i2c_init (void)
{
	if ((i2c_fd = open ("/dev/i2c-1", O_RDWR)) < 0) {
		perror ("i2c open");
		exit (1);
	}
}

int
i2c_general_reset (void)
{
	/* 00 06 */
	ioctl (i2c_fd, I2C_SLAVE, 0);
	i2c_smbus_write_byte (i2c_fd, 6);
	return (0);
}

void 
i2c_frequency(int freq)
{
}

/*
 * send 16 bit start_addr to device, then read couint_uint16
 * big endian 16 bit values and store in buf
 */
int
i2c_read (uint8_t slave_addr, uint16_t start_addr, 
	  uint16_t count_uint16, uint16_t *outbuf)
{
	struct i2c_smbus_ioctl_data msg;
	union i2c_smbus_data data;
	
	if (ioctl (i2c_fd, I2C_SLAVE, slave_addr) < 0)
		return (-1);

	data.block[0] = start_addr >> 8;
	data.block[1] = start_addr;

	memset (&msg, 0, sizeof msg);
	msg.read_write = I2C_SMBUS_WRITE;
	msg.command = start_addr;
	msg.size = I2C_SMBUS_I2C_BLOCK_DATA;
	memset (&data, 0, sizeof data);
	data.byte = 2;
	msg.data = &data;
	if (ioctl (i2c_fd, I2C_SMBUS, &msg) < 0) {
		perror ("ioctl smbus");
		return (-1);
	}


	memset (&msg, 0, sizeof msg);
	msg.read_write = I2C_SMBUS_READ;
	msg.command = start_addr;
	msg.size = I2C_SMBUS_I2C_BLOCK_DATA;
	memset (&data, 0, sizeof data);
	data.byte = count_uint16 * 2;
	msg.data = &data;
	if (ioctl (i2c_fd, I2C_SMBUS, &msg) < 0) {
		perror ("ioctl smbus");
		return (-1);
	}

	unsigned char *up = msg.data->block;
	for (int i = 0; i < count_uint16; i++) {
		outbuf[i] = (up[0] << 8) | up[1];
		up += 2;
	}

	return (0);
}

int
i2c_write (uint8_t slave_addr, uint16_t write_addr, uint16_t wdata)
{
	struct i2c_smbus_ioctl_data msg;
	union i2c_smbus_data data;
	
	data.block[0] = write_addr >> 8;
	data.block[1] = write_addr;
	data.block[2] = wdata >> 8;
	data.block[3] = wdata;

	if (ioctl (i2c_fd, I2C_SLAVE, slave_addr) < 0)
		return (-1);

	memset (&msg, 0, sizeof msg);
	msg.read_write = I2C_SMBUS_WRITE;
	msg.command = slave_addr;
	msg.size = I2C_SMBUS_I2C_BLOCK_DATA;
	memset (&data, 0, sizeof data);
	data.byte = 4; /* byte count */
	msg.data = &data;
	if (ioctl (i2c_fd, I2C_SMBUS, &msg) < 0) {
		perror ("ioctl smbus");
	}

	uint16_t check;
	if (i2c_read (slave_addr, write_addr, 1, &check) < 0)
		return (-1);

	if (check != wdata)
		return (-2);

	return (0);
}


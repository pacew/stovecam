#include <stdio.h>
#include <stdint.h>

#include "MLX90640_API.h"
#include "MLX90640_I2C_Driver.h"
#include "i2c.h"

#define MLX_I2C_ADDR (0x33)

int
main (int argc, char **argv)
{
//	static uint16_t eeMLX90640[832];
	uint16_t buf[1000];
	int i;

	MLX90640_I2CRead(MLX_I2C_ADDR, 0x2400, 16, buf);

	for (i = 0; i < 16; i++) {
		printf ("%04x ", buf[i]);
	}
	printf ("\n");

	MLX90640_I2CRead(MLX_I2C_ADDR, 0x2404, 16, buf);

	for (i = 0; i < 16; i++) {
		printf ("%04x ", buf[i]);
	}
	printf ("\n");


//	MLX90640_DumpEE(MLX_I2C_ADDR, eeMLX90640);

	return (0);
}

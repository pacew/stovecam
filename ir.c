#include <stdio.h>
#include <stdint.h>

#include "MLX90640_API.h"

#define MLX_I2C_ADDR 0x33

int
main (int argc, char **argv)
{
	static uint16_t eeMLX90640[832];

	MLX90640_DumpEE(MLX_I2C_ADDR, eeMLX90640);

	return (0);
}

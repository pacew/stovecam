#include <stdio.h>
#include <stdint.h>

#include "MLX90640_API.h"
#include "MLX90640_I2C_Driver.h"
#include "i2c.h"

#define MLX_I2C_ADDR (0x33)

#define ANSI_COLOR_RED     "\x1b[31m"
#define ANSI_COLOR_GREEN   "\x1b[32m"
#define ANSI_COLOR_YELLOW  "\x1b[33m"
#define ANSI_COLOR_BLUE    "\x1b[34m"
#define ANSI_COLOR_MAGENTA "\x1b[35m"
#define ANSI_COLOR_CYAN    "\x1b[36m"
#define ANSI_COLOR_NONE    "\x1b[30m"
#define ANSI_COLOR_RESET   "\x1b[0m"

#define BLOCK "\u2588\u2588"

void
putblock (char *color)
{
	printf("%s%s%s", color, BLOCK, ANSI_COLOR_RESET);
}

int
main (int argc, char **argv)
{
	static uint16_t eeMLX90640[832];

	MLX90640_SetRefreshRate(MLX_I2C_ADDR, 0b010);
	MLX90640_SetChessMode(MLX_I2C_ADDR);
	printf("Configured...\n");

	paramsMLX90640 mlx90640;
	MLX90640_DumpEE(MLX_I2C_ADDR, eeMLX90640);
	MLX90640_ExtractParameters(eeMLX90640, &mlx90640);

	int refresh = MLX90640_GetRefreshRate(MLX_I2C_ADDR);
    
	printf ("refresh %d\n", refresh);

	int subpage;
	static float mlx90640To[768];
	uint16_t frame[834];
	float eTa;
	float emissivity = 1;

    
	while (1){
		MLX90640_GetFrameData(MLX_I2C_ADDR, frame);
		// MLX90640_InterpolateOutliers(frame, eeMLX90640);
		eTa = MLX90640_GetTa(frame, &mlx90640);
		subpage = MLX90640_GetSubPageNumber(frame);
		MLX90640_CalculateTo(frame, &mlx90640,
				     emissivity, eTa, mlx90640To);

		MLX90640_BadPixelsCorrection((&mlx90640)->brokenPixels,
					     mlx90640To, 1, &mlx90640);
		MLX90640_BadPixelsCorrection((&mlx90640)->outlierPixels, 
					     mlx90640To, 1, &mlx90640);

		printf("Subpage: %d\n", subpage);
		//MLX90640_SetSubPage(MLX_I2C_ADDR,!subpage);

		for(int x = 0; x < 32; x++){
			for(int y = 0; y < 24; y++){
				float val = mlx90640To[32 * (23-y) + x];
				if(val > 99.99) val = 99.99;
				if(val > 32.0){
					putblock (ANSI_COLOR_MAGENTA);
				} else if(val > 29.0){
					putblock (ANSI_COLOR_RED);
				} else if (val > 26.0){
					putblock (ANSI_COLOR_YELLOW);
				} else if ( val > 20.0 ){
					putblock (ANSI_COLOR_NONE);
				} else if (val > 17.0) {
					putblock (ANSI_COLOR_GREEN);
				} else if (val > 10.0) {
					putblock (ANSI_COLOR_CYAN);
				} else {
					putblock (ANSI_COLOR_BLUE);
				}
			}
			printf ("\n");
		}
		printf("\x1b[33A");
	}

	return (0);
}

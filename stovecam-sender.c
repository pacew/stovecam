#include <stdio.h>
#include <stdint.h>
#include <memory.h>
#include <unistd.h>
#include <stdlib.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>

#include "MLX90640_API.h"
#include "MLX90640_I2C_Driver.h"

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

#define IRMAGIC 0x20200630

struct hdr {
	uint32_t magic;
	uint16_t width;
	uint16_t height;
	uint16_t start_row;
	uint16_t start_col;
	uint16_t npix;
	float data[0];
};

int udp_sock;
struct sockaddr_in xmit_addr;

void
net_init (void)
{
	udp_sock = socket (AF_INET, SOCK_DGRAM, 0);

	memset (&xmit_addr, 0, sizeof xmit_addr);
	xmit_addr.sin_family = AF_INET;
	inet_aton ("224.0.0.1", &xmit_addr.sin_addr);
	xmit_addr.sin_port = htons (15318);
}

void
xmit (float *arr, int width, int height)
{
	union {
		struct hdr hdr;
		unsigned char xbuf[1400];
	} u;

	int max_in_pkt = (sizeof u.xbuf - sizeof u.hdr) / 4;

	int in_idx = 0;
	int togo = width * height;

	int row = 0;
	int col = 0;
	while (togo > 0) {
		int thistime = togo;
		if (thistime > max_in_pkt)
			thistime = max_in_pkt;

		u.hdr.magic = htonl (IRMAGIC);
		u.hdr.width = htons (width);
		u.hdr.height = htons (height);
		u.hdr.start_row = htons (row);
		u.hdr.start_col = htons (col);
		u.hdr.npix = htons (thistime);
		for (int i = 0; i < thistime; i++) {
			u.hdr.data[i] = arr[in_idx];
			in_idx++;
			col++;
			if (col >= width) {
				col = 0;
				row++;
			}
		}

		int n = sizeof u.hdr + thistime * 4;
		sendto (udp_sock, u.xbuf, n, 0,
			(struct sockaddr *)&xmit_addr, sizeof xmit_addr);

		togo -= thistime;
	}
}



void
putblock (char *color)
{
	printf("%s%s%s", color, BLOCK, ANSI_COLOR_RESET);
}

int quiet;

void
usage (void)
{
	fprintf (stderr, "usage: stovecam-sender [-q]\n");
	exit (1);
}

int
main (int argc, char **argv)
{
	static uint16_t eeMLX90640[832];
	int c;

	while ((c = getopt (argc, argv, "q")) != EOF) {
		switch (c) {
		case 'q':
			quiet = 1;
			break;
		default:
			usage ();
		}
	}

	net_init ();

	MLX90640_SetRefreshRate(MLX_I2C_ADDR, 0b010);
	MLX90640_SetChessMode(MLX_I2C_ADDR);

	paramsMLX90640 mlx90640;
	MLX90640_DumpEE(MLX_I2C_ADDR, eeMLX90640);
	MLX90640_ExtractParameters(eeMLX90640, &mlx90640);

	// int refresh = MLX90640_GetRefreshRate(MLX_I2C_ADDR);
    
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

		if (! quiet) {
			printf("Subpage: %d\n", subpage);

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
				
		float flat[32 * 24];
		int idx = 0;
		for(int x = 0; x < 32; x++){
			for(int y = 0; y < 24; y++){
				flat[idx++] = mlx90640To[x * 24 + y];
			}
		}
		xmit (flat, 32, 24);
	}

	return (0);
}

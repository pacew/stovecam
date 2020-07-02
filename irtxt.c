#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <memory.h>
#include <sys/socket.h>
#include <netinet/in.h>

void
usage (void)
{
	fprintf (stderr, "usage: irtxt\n");
	exit (1);
}

struct hdr {
	uint32_t magic;
	uint16_t width;
	uint16_t height;
	uint16_t start_row;
	uint16_t start_col;
	uint16_t npix;
	float data[0];
};

int sock;

#define IRMAGIC 0x20200630

#define IR_WIDTH 32
#define IR_HEIGHT 24

float temps[IR_WIDTH * IR_HEIGHT];

void
dump_ir (void)
{
	int row, col;

	printf ("\033[H");
	for (row = 0; row < IR_HEIGHT; row++) {
		for (col = 0; col < IR_WIDTH; col++) {
			float degc = temps[row * IR_WIDTH + col];
			float degf = degc * 9 / 5 + 32;

			printf ("%3.0f ", degf);
		}
		printf ("\033[K\n");
	}
	printf ("\033[J\n");
}


int
main (int argc, char **argv)
{
	int c;
	struct sockaddr_in addr;
	int n;
	union {
		struct hdr hdr;
		unsigned char buf[1400];
	} u;

	while ((c = getopt (argc, argv, "")) != EOF) {
		switch (c) {
		default:
			usage ();
		}
	}

	sock = socket (AF_INET, SOCK_DGRAM, 0);

	memset (&addr, 0, sizeof addr);
	addr.sin_port = htons (15318);
	bind (sock, (struct sockaddr *)&addr, sizeof addr);;

	while (1) {
		if ((n = recv (sock, u.buf, sizeof u.buf, 0)) < 0) {
			perror ("recv");
			exit (1);
		}

		if (ntohl (u.hdr.magic) != IRMAGIC) {
			printf ("bad magic\n");
			continue;
		}

		if (ntohs (u.hdr.width) != IR_WIDTH) {
			printf ("bad width\n");
			continue;
		}
		
		if (ntohs (u.hdr.height) != IR_HEIGHT) {
			printf ("bad height %d\n", ntohs (u.hdr.height));
			continue;
		}
			
		int npix = ntohs (u.hdr.npix);
		int avail = (n - sizeof u.hdr) / 4;
		if (npix != avail) {
			printf ("bad npix %d\n", npix);
			continue;
		}

		int row = ntohs (u.hdr.start_row);
		int col = ntohs (u.hdr.start_col);

		if (row < 0 || row >= IR_HEIGHT
		    || col < 0 || col >= IR_WIDTH) {
			printf ("bad start r,c\n");
			continue;
		}

		for (int pnum = 0; pnum < npix; pnum++) {
			float pix = u.hdr.data[pnum];
			temps[row * IR_WIDTH + col] = pix;
			col++;
			if (col >= IR_WIDTH) {
				col = 0;
				row++;
			}
		}
			
		if (row == IR_HEIGHT && col == 0) {
			printf ("dump\n");
			dump_ir ();
		}

	}

	return (0);
}

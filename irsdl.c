#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <memory.h>
#include <fcntl.h>
#include <signal.h>
#include <sys/socket.h>
#include <netinet/in.h>

#include <SDL2/SDL.h>

void
usage (void)
{
	fprintf (stderr, "usage: irsdl\n");
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


void
ir_setup (void)
{
	struct sockaddr_in addr;
	
	sock = socket (AF_INET, SOCK_DGRAM, 0);

	memset (&addr, 0, sizeof addr);
	addr.sin_port = htons (15318);
	bind (sock, (struct sockaddr *)&addr, sizeof addr);;
	fcntl (sock, F_SETFL, O_NONBLOCK);
	

}

void
ir_step (void)
{
	int n;
	union {
		struct hdr hdr;
		unsigned char buf[1400];
	} u;


	while ((n = recv (sock, u.buf, sizeof u.buf, 0)) > 0) {
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
			temps[row * IR_WIDTH + (IR_WIDTH - col - 1)] = pix;
			col++;
			if (col >= IR_WIDTH) {
				col = 0;
				row++;
			}
		}
	}
}




SDL_Window *window;
SDL_Surface *surface;

#define PIXEL_MULT 20

#define SCREEN_WIDTH (IR_WIDTH * PIXEL_MULT)
#define SCREEN_HEIGHT (IR_HEIGHT * PIXEL_MULT)

/*
 * 0 <= h <= 360
 * 0 <= s <= 1
 * 0 <= v <= 1
 */

void
hsvtorgb (double h, double s, double v, double *rp, double *gp, double *bp)
{
	int i;
	double f, m, n, k;
	double r, g, b;
	if (s == 0) {
		*rp = v;
		*gp = v;
		*bp = v;
		return;
	}

	
	if (h == 360)
		h = 0;
	h = h/60;
	i = floor(h);
	f = h - i;
	m = v * (1 - s);
	n = v * ( 1 - s * f);
	k = v * ( 1 - s * (1 - f));
	switch (i) {
	case 0: r = v; g = k; b = m; break;
	case 1: r = n; g = v; b = m; break;
	case 2: r = m; g = v; b = k; break;
	case 3: r = m; g = n; b = v; break;
	case 4: r = k; g = m; b = v; break;
	case 5: r = v; g = m; b = n; break;
	}
	*rp = r;
	*gp = g;
	*bp = b;
}

/* linear scale */
float
lscale_clamp (float val, float from_left, float from_right, float to_left, float to_right)
{
        if (from_left == from_right)
                return (to_right);

        float x = (val - from_left)
                / (from_right - from_left)
                * (to_right - to_left)
                + to_left;
        if (to_left < to_right) {
                if (x < to_left)
                        x = to_left;
                if (x > to_right)
                        x = to_right;
        } else {
                if (x < to_right)
                        x = to_right;
                if (x > to_left)
                        x = to_left;
        }
        return (x);

}

float
lscale (float val, float from_left, float from_right, float to_left, float to_right)
{
        if (from_left == from_right)
                return (to_right);

        return ((val - from_left)
                / (from_right - from_left)
                * (to_right - to_left)
                + to_left);
}

void
redraw (void)
{
	ir_step ();
	
	if (surface->w != SCREEN_WIDTH
	    || surface->h != SCREEN_HEIGHT
	    || surface->format->format != SDL_PIXELFORMAT_RGB888
	    || surface->format->BytesPerPixel != 4) {
		printf ("unexpected sdl surface format\n");
		exit (1);
	}

	int ir, ig, ib;

	printf ("\033[H");

	for (int ir_row = 0; ir_row < IR_HEIGHT; ir_row++) {
		for (int rm = 0; rm < PIXEL_MULT; rm++) {
			int row = ir_row * PIXEL_MULT + rm;
			int off = row * surface->pitch;
			uint32_t *outp = (uint32_t *)(surface->pixels + off);
			for (int ir_col = 0; ir_col < IR_WIDTH; ir_col++) {
				double t = temps[ir_row * IR_WIDTH + ir_col];
				if (rm == 0) {
					if (t >= 30)
						printf ("** ");
					else
						printf ("%2.0f ", t);
				}
				ir = lscale_clamp (t, 25, 30, 100, 255);
				ig = ir;
				ib = ir;

				for (int cm = 0; cm < PIXEL_MULT; cm++) {
					*outp++ = (ir << 16) | (ig << 8) | ib;
				}
			}
		}
		printf ("\033[K\n");
	}

	printf ("\033[J");
	fflush(stdout);
	SDL_UpdateWindowSurface(window);
}

void
do_mouse (int x, int y, int state)
{
}

void
sdl_step (void)
{
	SDL_Event e;

	while (SDL_PollEvent(&e)) {
		int ch;
		switch (e.type) {
		case SDL_QUIT:
			exit (1);
			break;
		case SDL_KEYDOWN:
			ch = e.key.keysym.sym; 
			switch (ch) {
			case 'c':
			case 'q':
			case 'w':
				exit (0);
				break;
			default:
				break;
			}
			break;
			
		case SDL_MOUSEBUTTONDOWN:
			do_mouse (e.button.x, e.button.y, 1);
			break;
		case SDL_MOUSEBUTTONUP:
			do_mouse (e.button.x, e.button.y, 0);
			break;
			
		}
	}
	
	redraw();

	SDL_Delay (10);
}

void
sdl_init (void)
{
	if(SDL_Init(SDL_INIT_VIDEO) != 0) {
		printf ("sdl error\n");
		exit (1);
	}

	window = SDL_CreateWindow("sdl", 
				  0, 0,
				  SCREEN_WIDTH, SCREEN_HEIGHT, 
				  0);
	if (window == NULL) {
		printf ("sdl error\n");
		exit (1);
	}

	surface = SDL_GetWindowSurface(window);
}

static void
sigint (int sig)
{
	printf ("SIGINT\n");
	exit (1);
}


int
main (int argc, char **argv)
{
	signal (SIGINT, sigint);

	sdl_init ();
	ir_setup ();

	while (1) {
		sdl_step ();
	}
}


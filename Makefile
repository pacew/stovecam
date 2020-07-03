CFLAGS = -g -Wall -I. `pkg-config --cflags sdl2 SDL2_ttf`
LIBS = `pkg-config --libs sdl2 SDL2_ttf`

all: sdl

sdl: sdl.o
	$(CC) $(CFLAGS) -o sdl sdl.o $(LIBS) -lm

clean:
	rm -f *.o sdl


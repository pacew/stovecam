CPPFLAGS = -g -Wall -I.
CFLAGS = -g -Wall -I.

all: stovecam-sdl stovecam-txt

STOVECAM_SENDER_OBJS = stovecam-sender.o MLX90640_API.o \
	MLX90640_LINUX_I2C_Driver.o
stovecam-sender: $(STOVECAM_SENDER_OBJS)
	$(CC) $(CFLAGS) -o stovecam-sender $(STOVECAM_SENDER_OBJS) -li2c -lm

stovecam-sdl: stovecam-sdl.o
	$(CC) $(CFLAGS) -o stovecam-sdl stovecam-sdl.o -lSDL2 -lm

stovecam-txt: stovecam-txt.o
	$(CC) $(CFLAGS) -o stovecam-txt stovecam-txt.o

install-service: stovecam-sender stovecam.service
	sudo cp stovecam.service /etc/systemd/system/
	sudo systemctl enable stovecam
	sudo systemctl daemon-reload

clean:
	rm -f *.o stovecam-sender stovecam-sdl stovecam-txt


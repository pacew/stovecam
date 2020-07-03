CPPFLAGS = -g -Wall -I.
CFLAGS = -g -Wall -I.

all: stovecam-sender

STOVECAM_SENDER_OBJS = stovecam-sender.o MLX90640_API.o \
	MLX90640_LINUX_I2C_Driver.o
stovecam-sender: $(STOVECAM_SENDER_OBJS)
	$(CC) $(CFLAGS) -o stovecam-sender $(STOVECAM_SENDER_OBJS) -li2c -lm

install-service: stovecam-sender stovecam.service
	sudo cp stovecam.service /etc/systemd/system/
	sudo systemctl enable stovecam
	sudo systemctl daemon-reload

clean:
	rm -f *.o stovecam-sender


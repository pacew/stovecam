CPPFLAGS = -g -Wall -I.
CFLAGS = -g -Wall -I.

LIBS = -li2c -lm

OBJS = ir.o MLX90640_API.o MLX90640_LINUX_I2C_Driver.o

all: ir irtxt

ir: $(OBJS)
	$(CC) $(CFLAGS) -o ir $(OBJS) $(LIBS)

irtxt: irtxt.o
	$(CC) $(CFLAGS) -o irtxt irtxt.o

clean:
	rm -f *.o ir

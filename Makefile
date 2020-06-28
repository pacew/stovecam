CPPFLAGS = -g -Wall -I.
CFLAGS = -g -Wall -I.

LIBS = -li2c -lm

OBJS = ir.o i2c.o i2c-glue.o MLX90640_API.o 

ir: $(OBJS)
	$(CC) $(CFLAGS) -o ir $(OBJS) $(LIBS)

clean:
	rm -f *.o ir

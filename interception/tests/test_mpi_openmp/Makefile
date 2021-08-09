
CC = mpicc
OP = -g -O3 -fopenmp
LINK = -fopenmp

all:
	$(CC) -c $(OP) main.c
	$(CC) $(LINK) -o main main.o

clean:
	rm -rf *.o main *.yaml

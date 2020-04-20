CC=g++
CFLAGS=-Wall -Wextra -g
CPPFLAGS=-Wall -Wextra -g

all: typescript2txtcol

typescript2txt: typescript2txtcol.o

clean:
	-rm -f *.o typescript2txtcol 

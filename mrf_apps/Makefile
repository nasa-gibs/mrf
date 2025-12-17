
# The Makefile.lcl needs to define PREFIX and GDAL_ROOT for this system
# For example, it should contain these two linel -al
# PREFIX=/home/ec2-user
# GDAL_ROOT=$(PREFIX)/src/gdal/gdal
#
include ../Makefile.lcl

TARGETS = can mrf_insert jxl
GDAL_INCLUDE = -I $(PREFIX)/include -I $(GDAL_ROOT)
LIBDIR = $(PREFIX)/lib
BINDIR = $(PREFIX)/bin
CP=cp
BRUNSLI_LIBS = -lbrunslienc-c -lbrunslidec-c

INCLUDES = $(GDAL_INCLUDE)

all: $(TARGETS)

mrf_insert: mrf_insert.cpp
	$(CXX) $(CXXFLAGS) $(INCLUDES) -o $@ $< -L $(LIBDIR) -lgdal

can: can.cpp
	$(CXX) $(CXXFLAGS) $(INCLUDES) -o $@ $<

brn: brn.cpp
	$(CXX) $(CXXFLAGS) $(INCLUDES) -o $@ $< -L $(LIBDIR) $(BRUNSLI_LIBS)
	
install: $(TARGETS)
	$(CP) $^ $(BINDIR)

clean:
	$(RM) $(TARGETS)


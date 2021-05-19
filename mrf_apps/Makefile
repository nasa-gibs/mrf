
# The Makefile.lcl needs to define PREFIX and GDAL_ROOT for this system
# For example, it should contain these two linel -al
# PREFIX=/home/ec2-user
# GDAL_ROOT=$(PREFIX)/src/gdal/gdal
#
include Makefile.lcl

TARGETS = can mrf_insert
GDAL_INCLUDE = -I $(PREFIX)/include -I $(GDAL_ROOT)
LIBDIR = $(PREFIX)/lib
BINDIR = $(PREFIX)/bin
CP=cp

INCLUDES = $(GDAL_INCLUDE)

all: $(TARGETS)

mrf_insert: mrf_insert.cpp
	$(CXX) $(CXXFLAGS) $(INCLUDES) -o $@ $< -L $(LIBDIR) -lgdal

can: can.cpp
	$(CXX) $(CXXFLAGS) $(INCLUDES) -o $@ $<

jxl: jxl.cpp
	$(CXX) $(CXXFLAGS) $(INCLUDES) -o $@ $< -L $(LIBDIR) -lbrunslienc-c
	
install: $(TARGETS)
	$(CP) $^ $(BINDIR)

clean:
	$(RM) $(TARGETS) jxl


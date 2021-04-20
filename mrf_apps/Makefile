
# The Makefile.lcl needs to define PREFIX and GDAL_ROOT for this system
# For example, it should contain these two linel -al
# PREFIX=/home/ec2-user
# GDAL_ROOT=$(PREFIX)/src/gdal/gdal
#
include Makefile.lcl

TARGETS = can mrf_insert
GDAL_INCLUDE = -I $(PREFIX)/include -I $(GDAL_ROOT) -I /build/build/rpmbuild/BUILDROOT/gibs-gdal-2.4.4-3.el8.x86_64/usr/include/ -I /build/build/rpmbuild/BUILD/gibs-gdal-2.4.4/build/gdal/
LIBDIR = /build/build/rpmbuild/BUILDROOT/gibs-gdal-2.4.4-3.el8.x86_64/usr/lib64
BINDIR = /build/build/rpmbuild/BUILDROOT/gibs-gdal-2.4.4-3.el8.x86_64/usr/bin/
CP=cp

INCLUDES = $(GDAL_INCLUDE)

all: $(TARGETS)

mrf_insert: mrf_insert.cpp
	$(CXX) -std=c++11 $(CXXFLAGS) $(INCLUDES) -o $@ $< -L $(LIBDIR) -lgdal

can: can.cpp
	$(CXX) -std=c++11 $(CXXFLAGS) $(INCLUDES) -o $@ $<

install: $(TARGETS)
	$(CP) $^ $(BINDIR)

clean:
	$(RM) $(TARGETS)


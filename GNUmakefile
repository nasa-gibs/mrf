GDAL_VERSION=1.10.1
GDAL_ARTIFACT=gdal-$(GDAL_VERSION).tar.gz
GDAL_HOME=http://download.osgeo.org/gdal
GDAL_URL=$(GDAL_HOME)/$(GDAL_VERSION)/$(GDAL_ARTIFACT)

POSTGRES_VERSION=9.2

PREFIX=/usr/local
SMP_FLAGS=-j $(shell cat /proc/cpuinfo | grep processor | wc -l)
LIB_DIR=$(shell \
	[ "$(shell arch)" == "x86_64" ] \
		&& echo "lib64" \
		|| echo "lib" \
)
RPMBUILD_FLAGS=-ba

all: 
	@echo "Use targets gdal-rpm"

gdal: gdal-unpack mrf-overlay gdal-patch gdal-compile

#-----------------------------------------------------------------------------
# Download
#-----------------------------------------------------------------------------

download: gdal-download 

gdal-download: upstream/$(GDAL_ARTIFACT).downloaded

upstream/$(GDAL_ARTIFACT).downloaded: 
	mkdir -p upstream
	rm -f upstream/$(GDAL_ARTIFACT)
	( cd upstream ; wget $(GDAL_URL) )
	touch upstream/$(GDAL_ARTIFACT).downloaded

#-----------------------------------------------------------------------------
# Compile
#-----------------------------------------------------------------------------

gdal-unpack: build/gdal/VERSION

build/gdal/VERSION:
	mkdir -p build/gdal
	tar xf upstream/$(GDAL_ARTIFACT) -C build/gdal \
		--strip-components=1 --exclude=.gitignore

mrf-overlay:
	cp -r src/gdal_mrf/* build/gdal

gdal-patch: build/gdal/swig/python/GNUmakefile

build/gdal/swig/python/GNUmakefile: deploy/gibs-gdal/python-install.patch
# 	Python install does not respect DESTDIR
	( cd build/gdal ; \
		patch -p0 < ../../deploy/gibs-gdal/python-install.patch )
# 	Use external libtool
	sed -i 's|@LIBTOOL@|/usr/bin/libtool|g' build/gdal/GDALmake.opt.in

#	Patch gcore/overview.cpp	
	( cd build/gdal/gcore ; \
		patch < ../../../deploy/gibs-gdal/overview.patch )

gdal-compile:
	( cd build/gdal ; ./configure \
		--prefix=$(PREFIX) \
		--libdir=$(PREFIX)/$(LIB_DIR) \
		--mandir=$(PREFIX)/share/man \
		--with-threads \
		--without-bsb \
		--with-geotiff=internal \
		--with-libtiff=internal \
		--without-ogdi \
		--with-libz \
		--with-netcdf \
		--with-hdf4 \
		--with-hdf5 \
		--with-geos \
		--with-jasper \
		--with-png \
		--with-gif \
		--with-jpeg \
		--with-odbc \
		--with-sqlite3 \
		--with-mysql \
		--with-curl \
		--with-python \
		--with-pcraster \
		--with-xerces \
		--with-xerces-lib='-lxerces-c' \
		--with-xerces-inc=/usr/include \
		--with-jpeg12=no \
		--enable-shared \
		--with-gdal-ver=$(GDAL_VERSION) \
		--disable-rpath \
		--with-pg=/usr/pgsql-$(POSTGRES_VERSION)/bin/pg_config \
		--with-expat \
	)
	$(MAKE) -C build/gdal $(SMP_FLAGS) all man
	$(MAKE) -C build/gdal/frmts/mrf plugin

#-----------------------------------------------------------------------------
# Install
#-----------------------------------------------------------------------------
install: gdal-install

gdal-install:
	$(MAKE) -C build/gdal install install-man PREFIX=$(PREFIX)
	$(MAKE) -C build/gdal/mrf_apps install

#-----------------------------------------------------------------------------
# Local install
#-----------------------------------------------------------------------------
local-install: gdal-local-install

gdal-local-install: 
	mkdir -p build/install
	$(MAKE) gdal-install DESTDIR=$(PWD)/build/install

#-----------------------------------------------------------------------------
# Artifacts
#-----------------------------------------------------------------------------
artifacts: gdal-artifact

gdal-artifact: 
	mkdir -p dist
	rm -f dist/gibs-gdal-$(GDAL_VERSION).tar.bz2
	tar cjvf dist/gibs-gdal-$(GDAL_VERSION).tar.bz2 \
		--transform="s,^,gibs-gdal-$(GDAL_VERSION)/," \
		src/gdal_mrf deploy/gibs-gdal GNUmakefile

#-----------------------------------------------------------------------------
# RPM
#-----------------------------------------------------------------------------
rpm: gdal-rpm

gdal-rpm: gdal-artifact 
	mkdir -p build/rpmbuild/SOURCES
	mkdir -p build/rpmbuild/BUILD	
	mkdir -p build/rpmbuild/BUILDROOT
	rm -f dist/gibs-gdal*.rpm
	cp \
		upstream/gdal-$(GDAL_VERSION).tar.gz \
		dist/gibs-gdal-$(GDAL_VERSION).tar.bz2 \
		build/rpmbuild/SOURCES
	rpmbuild \
		--define _topdir\ "$(PWD)/build/rpmbuild" \
		-ba deploy/gibs-gdal/gibs-gdal.spec 
	mv build/rpmbuild/RPMS/*/gibs-gdal*.rpm dist
	mv build/rpmbuild/SRPMS/gibs-gdal*.rpm dist

#-----------------------------------------------------------------------------
# Mock
#-----------------------------------------------------------------------------
mock: gdal-mock

gdal-mock:
	mock --clean
	mock --root=gibs-epel-6-$(shell arch) \
		dist/gibs-gdal-$(GDAL_VERSION)-*.src.rpm

#-----------------------------------------------------------------------------
# Clean
#-----------------------------------------------------------------------------
clean: rm -rf build

distclean: clean
	rm -rf dist
	rm -rf upstream



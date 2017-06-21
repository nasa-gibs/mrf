%global gdal_version 2.1.3
%global gdal_release 1%{?dist}
%global mrf_version 1.1.2
%global mrf_release 1%{?dist}

Name:		gibs-gdal
Version:	%{gdal_version}
Release:	%{gdal_release}
Summary:	GIS file format library

Group:		System Environment/Libraries
License:	MIT
URL:		http://www.gdal.org/
Source0:	gibs-gdal-%{gdal_version}.tar.bz2
Source1:	http://download.osgeo.org/gdal/%{gdal_version}/gdal-%{gdal_version}.tar.gz
Source2:	https://pypi.python.org/packages/source/n/numpy/numpy-1.10.4.tar.gz

BuildRequires:	libtool pkgconfig
BuildRequires:	python-devel xerces-c-devel
BuildRequires:	libpng-devel libungif-devel
BuildRequires:	libjpeg-devel
BuildRequires:	libtiff-devel
BuildRequires:	jpackage-utils
BuildRequires:	jasper-devel cfitsio-devel libdap-devel librx-devel 
BuildRequires:	hdf-static hdf-devel
BuildRequires:	unixODBC-devel mysql-devel sqlite-devel 
BuildRequires:	zlib-devel
BuildRequires:	proj-devel netcdf-devel hdf5-devel ogdi-devel 
BuildRequires:	libgeotiff-devel
BuildRequires:	curl-devel
BuildRequires:	perl(ExtUtils::MakeMaker)
BuildRequires:	chrpath
BuildRequires:	swig 
BuildRequires:	doxygen
BuildRequires:	expat-devel
BuildRequires:  python-setuptools
BuildRequires:  geos-devel >= 3.3.2
Requires:	proj-devel
Requires:	gcc-c++
Requires:	python-devel
Requires:	python-pycxx-devel
Requires:	geos >= 3.3.2
Conflicts:  numpy < 1.10.4

Provides:	gdal = %{gdal_version}-%{gdal_release}
Obsoletes:	gdal < 1.11
Provides:	gdal-python = %{gdal_version}-%{gdal_release}
Obsoletes:	gdal-python < 1.11
	
%description
The GDAL library provides support to handle multiple GIS file formats.

This build includes the MRF driver for GIBS.


%package devel
Summary:	Development libraries for the GDAL library
Group:		Development/Libraries               
Requires:	%{name} = %{gdal_version}-%{gdal_release}

%description devel
Development libraries for the GDAL library

%prep
%setup -q
mkdir upstream
cp %{SOURCE1} upstream
cp %{SOURCE2} upstream

%build
make gdal PREFIX=/usr


%install
rm -rf %{buildroot}
make gdal-install DESTDIR=%{buildroot} PREFIX=/usr

# Man files are not being placed in the correct location
install -m 755 -d %{buildroot}/%{_mandir}
mv %{buildroot}/usr/man/* %{buildroot}/%{_mandir}

# Remove documentation that somehow made it into the bin directory
rm -f %{buildroot}/%{_bindir}/*.dox

# gdal doesn't respect the lib64 directory
install -m 755 -d %{buildroot}/usr/lib/gdalplugins

# Remove SWIG samples
rm -rf swig/python/samples

# Remove gdal-bash-completion if it exists
%if 0%{?centos}  == 7
rm -rf %{buildroot}/usr/etc/bash_completion.d/gdal-bash-completion.sh
%endif


%clean
rm -rf %{buildroot}


%files
%defattr(-,root,root,-)
%doc build/gdal/COMMITERS 
%doc build/gdal/LICENSE.TXT 
%doc build/gdal/NEWS 
%doc build/gdal/PROVENANCE.TXT
%doc build/gdal/VERSION
%{_bindir}/*
%exclude %{_bindir}/gdal-config
%{_libdir}/*.so.*
%{_datadir}/gdal
%{_mandir}/man1/*.1*
%{python_sitearch}/*.egg-info
%{python_sitearch}/gdal*
%{python_sitearch}/ogr*
%{python_sitearch}/osr*
%{python_sitearch}/osgeo
%{_libdir}/pkgconfig/gdal.pc
%dir /usr/lib/gdalplugins
%{_datadir}/numpy

%files devel
%defattr(-,root,root,-)
%{_bindir}/gdal-config
%{_includedir}/*
%{_libdir}/*.a
%{_libdir}/*.la
%{_libdir}/*.so

%post 
cd %{_datadir}/numpy/
python setup.py build
python setup.py install
/sbin/ldconfig

%postun -p /sbin/ldconfig


%changelog
* Wed Apr 12 2017 Joe T. Roberts <joe.t.roberts@jpl.nasa.gov> - 2.1.3-1
- New upstream GDAL version

* Wed Dec 21 2016 Joe T. Roberts <joe.t.roberts@jpl.nasa.gov> - 2.1.2-1
- New upstream GDAL version

* Fri Sep 2 2016 Joe T. Roberts <joe.t.roberts@jpl.nasa.gov> - 2.1.1-1
- Transition to GDAL version 2

* Mon Apr 25 2016 Joe T. Roberts <joe.t.roberts@jpl.nasa.gov> - 1.11.4-1
- New upstream GDAL version

* Tue Mar 8 2016 Joe T. Roberts <joe.t.roberts@jpl.nasa.gov> - 1.11.2-3
- Added numpy and removed plugin-mrf package 

* Tue Feb 2 2016 Joshua Rodriguez <jdrodrig@jpl.nasa.gov> - 1.11.2-2
- Remove PostgreSQL dependency 

* Tue Oct 14 2014 Mike McGann <mike.mcgann@nasa.gov> - 1.11.1-1
- New upstream GDAL version

* Fri Aug 8 2014 Mike McGann <mike.mcgann@nasa.gov> - 1.11.0-2
- Updates for building on EL7

* Fri Jul 18 2014 Mike McGann <mike.mcgann@nasa.gov> - 1.11.0-1
- New upstream GDAL version

* Wed Apr 30 2014 Joe T. Roberts <joe.t.roberts@jpl.nasa.gov> - 1.10.1-5
- Changed MRF version to 0.3.1

* Tue Apr 1 2014 Joe T. Roberts <joe.t.roberts@jpl.nasa.gov> - 1.10.1-4
- Changed MRF version to 0.3.0

* Tue Feb 18 2014 Joe T. Roberts <joe.t.roberts@jpl.nasa.gov> - 1.10.1-3
- Changed MRF version to 0.2.4 to be consistent with project release

* Thu Sep 5 2013 Mike McGann <mike.mcgann@nasa.gov> - 1.10.1-2
- Rebuild with PostgreSQL 9.2 and Expat support
- Added correct Obsoletes/Provides for devel package

* Wed Sep 4 2013 Mike McGann <mike.mcgann@nasa.gov> - 1.10.1-1
- New upstream version
- Rebuild with official MRF code

* Fri Aug 23 2013 Mike McGann <mike.mcgann@nasa.gov> - 1.10.0-7
- Obsoletes/Provides now correct and includes gdal-python

* Wed Jul 24 2013 Mike McGann <mike.mcgann@nasa.gov> - 1.10.0-6
- Corrections for mrf_insert from Lucian.

* Thu Jul 11 2013 Mike McGann <mike.mcgann@nasa.gov> - 1.10.0-5
- Link failure discovered in chroot build. Back to dynamic linking of
  proj with a dependency on the devel package.

* Mon Jul 8 2013 Mike McGann <mike.mcgann@nasa.gov> - 1.10.0-4
- Statically linking libproj for now since it is looking for the non-versioned
  shared object that is in the devel package.
- Added Lucian artifact which adds insert support for MRFs.

* Thu Jun 6 2013 Mike McGann <mike.mcgann@nasa.gov> - 1.10.0-3
- Split out MRF plugin into a separate package.

* Sat May 11 2013 Mike McGann <mike.mcgann@nasa.gov> - 1.10.0-2
- Combined python package into main since it is required to run many of
  the gdal utilities.

* Wed Apr 24 2013 Mike McGann <mike.mcgann@nasa.gov> - 1.10.0-1
- Initial package

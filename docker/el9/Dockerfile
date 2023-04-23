FROM rockylinux:9.1

COPY rpms/gibs-gdal-*.el9.*.rpm /rpms/

RUN yum install -y epel-release && yum clean all
RUN yum install -y /rpms/gibs-gdal-*.el9.*.rpm

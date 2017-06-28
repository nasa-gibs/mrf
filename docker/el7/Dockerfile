FROM centos:7

COPY rpms/gibs-gdal-*.el7.*.rpm /rpms/

RUN yum install -y epel-release && yum clean all
RUN yum install -y /rpms/gibs-gdal-*.el7.*.rpm

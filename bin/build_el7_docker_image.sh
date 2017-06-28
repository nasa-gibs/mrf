#!/bin/sh

set -evx

TAG="$1"
[ -z "$TAG" ] && TAG="gibs/gibs-gdal"

mkdir -p docker/el7/rpms
cp dist/gibs-gdal-*.el7.*.rpm docker/el7/rpms/
rm -f docker/el7/rpms/gibs-gdal-*.el7.*.src.rpm

(
  set -evx
  cd docker/el7
  docker build -t "$TAG" .
)

rm -rf docker/el7/rpms

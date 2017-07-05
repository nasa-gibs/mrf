#!/bin/sh

set -evx

TAG="$1"

mkdir -p docker/el7/rpms
cp dist/gibs-gdal-*.el7.*.rpm docker/el7/rpms/
rm -f docker/el7/rpms/gibs-gdal-*.el7.*.src.rpm

(
  set -evx
  cd docker/el7

  if [ -z "$TAG" ]; then
    docker build .
  else
    docker build -t "$TAG" .
  fi
)

rm -rf docker/el7/rpms

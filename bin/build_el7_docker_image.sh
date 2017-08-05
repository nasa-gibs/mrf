#!/bin/sh

set -e

if ! ls dist/gibs-gdal-*.el7.*.rpm >/dev/null 2>&1; then
  echo "No RPMs found in ./dist/" >&2
  exit 1
fi

TAG="$1"

mkdir -p docker/el7/rpms
cp dist/gibs-gdal-*.el7.*.rpm docker/el7/rpms/
rm -f docker/el7/rpms/gibs-gdal-*.el7.*.src.rpm

(
  set -e
  cd docker/el7

  if [ -z "$TAG" ]; then
    docker build .
  else
    docker build -t "$TAG" .
  fi
)

rm -rf docker/el7/rpms

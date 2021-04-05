#!/bin/sh

set -e

if ! ls dist/gibs-gdal-*.el8.*.rpm >/dev/null 2>&1; then
  echo "No RPMs found in ./dist/" >&2
  exit 1
fi

TAG="$1"

mkdir -p docker/el8/rpms
cp dist/gibs-gdal-*.el8.*.rpm docker/el8/rpms/
rm -f docker/el8/rpms/gibs-gdal-*.src.rpm
rm -f docker/el8/rpms/gibs-gdal-*debuginfo-*.rpm

(
  set -e
  cd docker/el8

  if [ -z "$TAG" ]; then
    docker build .
  else
    docker build -t "$TAG" .
  fi
)

rm -rf docker/el8/rpms

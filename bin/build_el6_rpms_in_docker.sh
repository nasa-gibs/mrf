#!/bin/sh

set -evx

mkdir -p dist

cat > dist/build_rpms.sh <<EOS
#!/bin/sh

set -evx

yum install -y epel-release
yum install -y \
  @buildsys-build \
  rsync \
  wget \
  yum-utils

mkdir -p /build
rsync -av --exclude .git /source/ /build/

(
  set -evx
  cd /build
  yum-builddep -y deploy/gibs-gdal/gibs-gdal.spec
  make download
  make gdal-rpm
)

cp /build/dist/gibs-gdal-*.rpm /artifacts/
chown "${DOCKER_UID}:${DOCKER_GID}" /artifacts/gibs-gdal-*.rpm
EOS
chmod +x dist/build_rpms.sh

docker run \
  --rm \
  --env "DOCKER_UID=$(id -u)" \
  --env "DOCKER_GID=$(id -g)" \
  --volume "$(pwd):/source:ro" \
  --volume "$(pwd)/dist:/dist" \
  centos:6 /dist/build_rpms.sh

rm dist/build_rpms.sh

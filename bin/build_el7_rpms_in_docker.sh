#!/bin/sh

set -evx

mkdir -p dist

cat > dist/build_rpms.sh <<EOS
#!/bin/sh

set -evx

yum install -y https://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm
sed -i \
  -e 's/^mirrorlist=/#mirrorlist=/' \
  -e 's/^#baseurl=/baseurl=/' \
  /etc/yum.repos.d/epel.repo
yum clean all
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

cp /build/dist/gibs-gdal-*.rpm /dist/
chown "${DOCKER_UID}:${DOCKER_GID}" /dist/gibs-gdal-*.rpm
EOS
chmod +x dist/build_rpms.sh

docker run \
  --rm \
  --env "DOCKER_UID=$(id -u)" \
  --env "DOCKER_GID=$(id -g)" \
  --volume "$(pwd):/source:ro" \
  --volume "$(pwd)/dist:/dist" \
  centos:7 /dist/build_rpms.sh

rm dist/build_rpms.sh

#!/bin/sh

set -evx

DOCKER_UID=$(id -u)
DOCKER_GID=$(id -g)
mkdir -p dist
cat > dist/build_rpms.sh <<EOS
#!/bin/sh

set -evx

yum install -y epel-release

dnf install -y 'dnf-command(config-manager)'
dnf config-manager --set-enabled crb

yum install -y \
  ccache \
  wget \
  rpmdevtools \
  mock \
  rsync 

mkdir -p /build
rsync -av --exclude .git /source/ /build/
chown -R root:root /build

(
  set -evx
  cd /build
  dnf builddep -y deploy/gibs-gdal/gibs-gdal.spec
  make download gdal-rpm
)

cp /build/dist/gibs-gdal-*.rpm /dist/
EOS
chmod +x dist/build_rpms.sh

docker run \
  --rm \
  --volume "$(pwd):/source:ro" \
  --volume "$(pwd)/dist:/dist" \
  rockylinux:9.1 /dist/build_rpms.sh

rm dist/build_rpms.sh

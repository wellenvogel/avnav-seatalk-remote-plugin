#! /bin/sh
pdir=`dirname $0`
pdir=`readlink -f "$pdir"`
set -x
docker run  --rm   -v "$pdir":/tmp/pkg   --user `id -u`:`id -g` -w /tmp/pkg goreleaser/nfpm pkg -p deb -f package.yaml

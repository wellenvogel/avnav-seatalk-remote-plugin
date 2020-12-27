#! /bin/sh
#package build using https://github.com/goreleaser/nfpm on docker
pdir=`dirname $0`
pdir=`readlink -f "$pdir"`
set -x
config=package.yaml
if [ "$1" != "" ] ; then
  #version given
  tmpf=package$$.yaml
  rm -f $tmpf
  sed "s/^ *version:.*/version: \"$1\"/" $config > $tmpf
  config=$tmpf
fi
#docker run  --rm   -v "$pdir":/tmp/pkg   --user `id -u`:`id -g` -w /tmp/pkg goreleaser/nfpm pkg -p deb -f $config
touch avnav-seatalk-remote-plugin_$1_all.deb
rt=$?
if [ "$tmpf" != "" ] ; then
  rm -f $tmpf
fi
exit $rt

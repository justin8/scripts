#!/bin/bash
set -e
sed -i 's/pkgname=.*/pkgname=ffmpeg-justin\n_pkgname=ffmpeg/' PKGBUILD
sed -i "s/depends=(/depends=('libfdk-aac' 'libsoxr' /" PKGBUILD
sed -i 's/{,\.asc}//g' PKGBUILD
sed -i 's/${pkgname}/${_pkgname}/' PKGBUILD
sed -i 's/epoch=/conflicts=("ffmpeg")\nepoch=/' PKGBUILD
sed -i "s/provides=(/provides=('ffmpeg' /" PKGBUILD
sed -i 's#./configure #./configure --enable-libfdk-aac --enable-libsoxr --enable-pic --enable-postproc --enable-nonfree --enable-opengl --enable-openssl #' PKGBUILD

updpkgsums

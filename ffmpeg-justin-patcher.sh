#!/bin/bash
set -e
sed -i 's/pkgname=.*/pkgname=ffmpeg-justin\n_pkgname=ffmpeg/' PKGBUILD
sed -i "s/depends=(/depends=('libaacplus' 'faac' 'libfdk-aac' 'libsoxr' 'vo-aacenc' 'vo-amrwbenc' /" PKGBUILD
sed -i 's/{,\.asc}//g' PKGBUILD
sed -i '/md5sums/s/$/)/' PKGBUILD
sed -i '/SKIP/d' PKGBUILD
sed -i 's/$pkgname/$_pkgname/' PKGBUILD
sed -i 's/epoch=/conflicts=ffmpeg\nepoch=/' PKGBUILD
sed -i "s/provides=(/provides=('ffmpeg' /" PKGBUILD
sed -i 's#./configure #./configure --enable-libaacplus --enable-libfaac --enable-libfdk-aac --enable-libsoxr --enable-libvo-aacenc --enable-libvo-amrwbenc --enable-pic --enable-postproc --enable-nonfree --enable-opengl --enable-openssl #' PKGBUILD
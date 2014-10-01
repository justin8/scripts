#!/bin/bash
pkgdir=/var/cache/pacman/pkg
dbpath=/tmp/pacman-db

mkdir -p "$dbpath"
pacman -Sy --noprogress --dbpath "$dbpath"

for package in $(ls -1 "$pkgdir" | grep -oP '^[a-z0-9]+(?:[-_][a-z][a-z0-9]*)*' | uniq)
do
	pacman -Sw --noconfirm --noprogress --cachedir "$pkgdir" "$package"
       #	2>&1 | grep '^downloading'
done

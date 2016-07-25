#!/bin/bash
# TODO: usage
# TODO: check sanity
# TODO: test this at least once

NAME=$1
shift
# folders = $@

for i in "$@"; do
	number="$(grep -Eo '[0-9]{4}')"
	filename="$NAME - $number"
	zip -j "$filename" "$i"/*
	mv "$filename.zip" "$filename.cbz"
done

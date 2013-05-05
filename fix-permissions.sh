#!/bin/bash

if [ $# -lt 3 ] ; then
	echo "Usage: fix-permissions.sh <folder> <dir permissions> <file permissions>"
	exit 1
fi

find $1 -type d -exec chmod $2 "{}" \;
find $1 -type f -exec chmod $3 "{}" \;

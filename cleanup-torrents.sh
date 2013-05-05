#!/bin/bash
mkdir -p /tmp/torrents
find /raid/shares/public -iname .added -exec mv {} /tmp/torrents \;
exit 0

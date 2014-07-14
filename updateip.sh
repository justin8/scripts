#!/bin/bash
LOG="/var/log/$(basename "$(readlink -f "$0")")"

exec >> $LOG 2>&1

echo -n "$(date +'%Y-%m%d %H:%M:%S'): "
curl -Ss --retry 400 "http://ipv4.cloudns.net/api/dynamicURL/?q=NzU4MTE6MzI1ODcxNzo0MWE1NmRiZTFkMmY2ODc1ZmVjZjdiZDkxOGM5ZDc3M2JmOTkxNWUxOGE3ODNkYTc4ZWFmZDJhNTMzOTQ2MzFk"
echo

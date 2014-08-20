#!/bin/zsh
while read line
do
	if echo "$line" | grep -q ':git'
	then
		repo=$(echo "$line" | cut -d'"' -f2)
		echo "[submodule \"modules/${repo#*/puppet*-}\"]"
		echo "	path = modules/${repo#*/puppet*-}"
		test=${${${${repo#git://}#git@}}//github.com:/github.com\/}
		echo "	url = https://$test"
	fi
done < $1

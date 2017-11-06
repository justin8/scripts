#!/bin/bash
set -ex

apt-get update

apt-get dist-upgrade -y

echo "You should probably reboot now if this is the first time you've run this script, and then re-run this. Press enter to continue anyway"
read

# Install lots of random stuff
apt-get install -y cmake ctags git golang jq jruby llvm mercurial python python-flake8 python-pip python3 python3-pip rsync silversearcher-ag vim virtualenvwrapper zsh apt-transport-https ca-certificates curl gnupg2 software-properties-common build-essential python-dev zlib1g zlibc zlib1g-dev libbz2-dev libreadline-dev libssl-dev bc libncurses5-dev curl network-manager

apt-get dist-upgrade -y

# Install docker
curl -fsSL https://download.docker.com/linux/debian/gpg | sudo apt-key add -

sudo add-apt-repository \
   "deb [arch=armhf] https://download.docker.com/linux/ubuntu \
   $(lsb_release -cs) \
   stable"

apt-get update

apt-get install -y docker-ce docker-compose


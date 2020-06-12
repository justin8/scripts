#!/bin/bash

# FTB Infinity
VERSION=1.11.2
INFILE=http://ftb.cursecdn.com/FTB2/modpacks/FTBInfinity/${VERSION//./_}/FTBInfinityServer.zip
OUTFILE=FTBInfinity-${VERSION}.zip
export FTB_SRVDIR=/srv/minecraft
export FTB_WORLD=world
export FTB_MAXHEAP=800M
export FTB_MINHEAP=400M
export FTB_GCTHREADS=2
export FTB_SERVERJAR='set later'

apt_install() {
	dpkg -l $1 &>/dev/null || apt-get install -y $1
}

### Hacky ubuntu install shit ###
for package in openjdk-8-jre-headless unzip; do
	apt_install $package
done

if ! [[ -d $FTB_SRVDIR ]]; then
	mkdir $FTB_SRVDIR
	cd $FTB_SRVDIR
	wget -O "$OUTFILE" "$INFILE"
	unzip "$OUTFILE"
	echo 'eula=true' > eula.txt
	bash FTBInstall.sh
fi

FTB_SERVERJAR=$(ls $FTB_SRVDIR|grep 'minecraft.*jar')

if ps aux|grep 'java.*-jar.*minecraft.*jar' | grep -v grep; then
	echo -e '\e[31;1mMinecraft appears to already be running!\e[0m'
	exit 1
fi
screen -dmS "minecraft" -- java -Xmx${FTB_MAXHEAP} -Xms${FTB_MINHEAP} -d64 -XX:+UseParNewGC -XX:+CMSIncrementalPacing -XX:+CMSClassUnloadingEnabled -XX:ParallelGCThreads=${FTB_GCTHREADS} -XX:MinHeapFreeRatio=5 -XX:MaxHeapFreeRatio=10 -jar ${FTB_SRVDIR}/${FTB_SERVERJAR} nogui

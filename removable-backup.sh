#!/bin/bash

BACKUPDIR="/mnt/backup"
LOG="/var/log/backup"
DATE=`date +%Y-%m-%d`
DEVICE="/dev/disk/by-label/backup"

#Exclusion list (for shares only):
cat << EOF > /tmp/backup-exclusion-list.txt
anime
console/Sony/PSX
documentaries
game-installers/steamapps
movies
recordings
tv
EOF

if [[ $EUID -ne 0 ]]; then
	echo "This script must be run as root" 1>&2
	exit 1
fi

LOCK=/run/lock/`basename $0`
exec 200>${LOCK}
if flock -xn 200; then

	exec > >(tee ${LOG})
	echo "" > ${LOG}

	echo "${DATE} Starting in 5 seconds..."
	sleep 5

	echo "${DATE} Mounting backup drive..."
	mount ${DEVICE} ${BACKUPDIR}
	return=$?
	if [ ${return} -ne 0 ]
	then
		if [ ${return} -eq 32 ]
		then
			echo "${DATE} Drive is already mounted. Continuing backup..."
		else
			echo "${DATE} Mounting failed; aborting backup"
			exit 1
		fi
	fi

	if [ -f /tmp/donotbackup ]
	then
		echo "${DATE} Skipping backup due to /tmp/donotbackup existing"
		exit 1
	fi

	echo "${DATE} Rsync-ing everything..."
	rsync -av --delete /etc ${BACKUPDIR}
	rsync -av --delete --exclude=.abachi.swap --exclude=downloads /raid/server-files ${BACKUPDIR}
	rsync -av --delete /raid/home ${BACKUPDIR}
	rsync -av --delete --exclude-from='/tmp/backup-exclusion-list.txt' /raid/shares ${BACKUPDIR}

	echo "${DATE} Syncing filesystems..."
	sync

	echo "${DATE} Backup completed. Unmounting drive and cleaning up..."
	umount -f ${BACKUPDIR}
	rm -f ${DEVICE}
	rm /tmp/backup-exclusion-list.txt
fi

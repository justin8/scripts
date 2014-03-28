#!/bin/bash
set -e
LOG="/var/log/vmware-to-racktables.log"

exitfunc()
{
	rc=$?
	if [[ $rc != 0 ]]
	then
		echo "An error has occurred!"
	fi
	exit $rc
}

exec > $LOG
trap exitfunc EXIT

if [[ ! -d /opt/rh/python27 ]]
then
	echo "vmware_to_racktables requires python27 to be installed!"
	exit 1
fi

source /opt/rh/python27/enable
cd "$(dirname "$(readlink -f "$0")")"
/root/.virtualenvs/vmware_to_racktables/bin/python2 vmware_to_racktables.py -vv

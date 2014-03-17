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

source /opt/rh/python27/enable
cd "$(dirname "$(readlink -f "$0")")"
/root/.virtualenvs/vmware_to_racktables/bin/python2 vmware_to_racktables.py -vv

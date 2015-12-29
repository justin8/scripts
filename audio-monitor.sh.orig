#!/bin/bash

audio=$(pactl list | grep -A2 '^Sink' | grep RUNNING)

for i in {1..60}; do
	if [[ $audio ]]; then
		dconf write /org/gnome/settings-daemon/plugins/power/sleep-inactive-ac-type "'nothing'"
		exit 0
	fi
	sleep 1
done

dconf write /org/gnome/settings-daemon/plugins/power/sleep-inactive-ac-type "'suspend'"

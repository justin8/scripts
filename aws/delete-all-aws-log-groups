#!/bin/bash

log_groups="$(aws logs describe-log-groups)"
log_group_names="$(echo "$log_groups" | jq .logGroups[].logGroupName -r)"


echo "$log_group_names"|while read i; do
	aws logs delete-log-group --log-group-name $i
done

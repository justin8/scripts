#!/bin/bash

# A bash script to update a Cloudflare DNS A record with the external IP of the source machine
# Used to provide DDNS service for my home
# Needs the DNS record pre-creating on Cloudflare


# Cloudflare zone is the zone which holds the record, e.g. example.com
zone=$1
# dnsrecord is the A record which will be updated, e.g. foo.example.com
dns_record=$2

## Cloudflare authentication details; either update the script to store here or input via CLI
cloudflare_api_key=$3

if [[ -z $zone ]] || [[ -z $dns_record ]] || [[ -z $cloudflare_api_key ]]; then
	echo "Error: Please provide the zone, DNS record and Cloudflare API key!"
	echo
	echo "Usage: cloudflare-ddns-update.sh example.com foo.example.com MyKeyXYZ"
	exit 1
fi


function cloudflare_api() {
	method=$1
	api_path=$2
	shift; shift

	curl -s -X $method "https://api.cloudflare.com/client/v4/$api_path" \
		-H "Authorization: Bearer $cloudflare_api_key" \
		-H "Content-Type: application/json" $@
}

# Get the current external IP address
ip=$(curl -s -X GET https://checkip.amazonaws.com)

echo "Current IP is $ip"

if host $dns_record 1.1.1.1 | grep "has address" | grep "$ip"; then
  echo "$dns_record is currently set to $ip; no changes needed"
  exit
fi

# if here, the dns record needs updating

# get the zone id for the requested zone
zone_id=$(cloudflare_api GET "zones?name=$zone&status=active" | jq -r '{"result"}[] | .[0] | .id')

echo "Zone ID for $zone is $zone_id"

# get the dns record id
dns_record_id=$(cloudflare_api GET "zones/$zone_id/dns_records?type=A&name=$dns_record" | jq -r '{"result"}[] | .[0] | .id')

echo "DNS record ID for $dns_record is $dns_record_id"

# update the record
cloudflare_api PUT "zones/$zone_id/dns_records/$dns_record_id" --data "{\"type\":\"A\",\"name\":\"$dns_record\",\"content\":\"$ip\",\"ttl\":1,\"proxied\":false}" | jq

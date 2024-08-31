#!/bin/bash

# A bash script to update a Cloudflare DNS A record with the external IP of the source machine
# Used to provide DDNS service for my home
# Needs the DNS record pre-created on Cloudflare

# Settings:
ttl=60

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
	shift
	shift

	curl -s -X "$method" "https://api.cloudflare.com/client/v4/$api_path" \
		-H "Authorization: Bearer $cloudflare_api_key" \
		-H "Content-Type: application/json" $@
}

# Get the current external IP address
ip4=$(curl -s -X GET -4 https://ifconfig.co/)
ip6=$(curl -s -X GET -6 https://ifconfig.co/)

echo "Current IP4 is $ip4"
echo "Current IP6 is $ip6"

update4=true
update6=true
host_response="$(host "$dns_record" 1.1.1.1)"

if echo "$host_response" | grep "has address" | grep "$ip4"; then
	echo "$dns_record A is currently set to $ip4; no changes needed"
	update4=false
fi

if echo "$host_response" | grep "has IPv6 address" | grep "$ip6"; then
	echo "$dns_record AAAA is currently set to $ip6; no changes needed"
	update6=false
fi

if [[ $update4 == true ]] || [[ $update6 == true ]]; then
	zone_id=$(cloudflare_api GET "zones?name=$zone&status=active" | jq -r '{"result"}[] | .[0] | .id')

	echo "Zone ID for $zone is $zone_id"
fi

if [[ $update4 == true ]]; then
	dns_record_id_4=$(cloudflare_api GET "zones/$zone_id/dns_records?type=A&name=$dns_record" | jq -r '{"result"}[] | .[0] | .id')
	echo "IPv4 DNS record ID for $dns_record is $dns_record_id_4"

	cloudflare_api PUT "zones/$zone_id/dns_records/$dns_record_id_4" --data "{\"type\":\"A\",\"name\":\"$dns_record\",\"content\":\"$ip4\",\"ttl\":$ttl,\"proxied\":false}" | jq
fi

if [[ $update6 == true ]]; then
	dns_record_id_6=$(cloudflare_api GET "zones/$zone_id/dns_records?type=AAAA&name=$dns_record" | jq -r '{"result"}[] | .[0] | .id')
	echo "IPv6 DNS record ID for $dns_record is $dns_record_id_6"

	cloudflare_api PUT "zones/$zone_id/dns_records/$dns_record_id_6" --data "{\"type\":\"AAAA\",\"name\":\"$dns_record\",\"content\":\"$ip6\",\"ttl\":$ttl,\"proxied\":false}" | jq
fi

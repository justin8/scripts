#!/bin/bash
dir=$(dirname "$(readlink -f "${0}")")

for infile in $dir/to-be-encoded/*
do
	outfile=$(basename "$infile")
	outfile=${outfile%.*}
	ffmpeg -i "$infile" -vcodec libx264 -crf 23 -preset veryslow -acodec libfdk_aac -ab 128k -ac 2 "$dir/complete/${outfile}.mkv"
	[[ $? == 0 ]] && rm "$infile"
done

#!/bin/bash
dir=$(dirname "$(readlink -f "${0}")")

for infile in $dir/to-be-encoded/*
do
	outfile=$(basename "$infile")
	outfile=${outfile%.*}
	ffmpeg -i "$infile" -vcodec libx264 -crf 23 -preset veryslow -acodec libfdk_aac -ab 128k -ac 2 "$dir/complete/${outfile}.mkv"
	rc=$?
	if [[ $rc == 0 ]]
	then
		echo -e "\e[32;1mCompleted encoding $infile\e[0m\n\n\n"
		rm "$infile"
	else
		echo -e "\e[31;1mFailed to encode $infile. (RC=$rc)\e[0m\n\n\n"
	fi
done

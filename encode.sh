#!/bin/bash
dir=$(dirname "$(readlink -f "${0}")")

if [[ ! -d $dir/to-be-encoded ]]
then
	dir=$(pwd)
fi

if [[ ! -d $dir/to-be-encoded ]]
then
	echo "Unable to find to-be-encoded directory! Aborting."
	exit 1
fi

tempdir="$dir/temp"
outdir="$dir/complete"
indir="$dir/to-be-completed"
faildir="$dir/failed"
LOCK="$dir/.lock"

mkdir -p "$tempdir" "$outdir" "$indir" "$faildir"

#LOCK
#clear temp
exec 200>"$LOCK"

if flock -xn 200
then
	for infile in $indir/*
	do
		outfile=$(basename "$infile")
		outfile="${outfile%.*}.mkv"

		if [[ -f "$outdir/$outfile" ]]
		then
			echo "$infile has already been processed!"
		else

			ffmpeg -i "$infile" -vcodec libx264 -crf 23 -preset veryslow -acodec libfdk_aac -ab 128k -ac 2 "$tempdir/${outfile}.mkv"
			rc=$?
			if [[ $rc == 0 ]]
			then
				echo -e "\e[32;1mCompleted encoding $infile\e[0m\n\n\n"
				rm "$infile"
				mv "$tempdir/${outfile}.mkv" "$outdir"
			else
				echo -e "\e[31;1mFailed to encode $infile. (RC=$rc)\e[0m\n\n\n"
				mv "$infile" "$dir/failed"
			fi
		fi
	done
fi

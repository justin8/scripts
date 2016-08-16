#!/bin/bash
dir=$(dirname "$(readlink -f "${0}")")

usage() {
	cat <<-EOF

	Usage: $(basename "$(readlink -f "$0")") [options]

	Put files in a 'to-be-encoded' directory in the current folder.
	Failed conversions will go to ./failed
	Successful conversions will go to ./complete

	OPTIONS:
		--help -h          This help
		--width=1280       Set the width (with automatic height)
		--extra-args=...   Any extra args to pass directly to ffmpeg
		--quality=20       CRF quality (Default: $quality)
		--preset=veryslow  The preset to use (Default: $preset)
	EOF
	exit 0
}

# Defaults
quality=21
preset=veryslow
scale=''
extra=''

for ARG in "$@"; do
	case $ARG in
		--help|-h) usage ;;
		--width=*) scale="-vf scale=${ARG#*=}:-2" ;;
		--extra-args=*) extra="${ARG#*=}" ;;
		--quality=*) quality="${ARG#*=}" ;;
		--preset=*) preset="${ARG#*=}" ;;
	esac
	shift
done

# auto-detect dir
if [[ ! -d $dir/to-be-encoded ]]
then
	dir=$(pwd)
fi

if [[ ! -d $dir/to-be-encoded ]]
then
	echo "Unable to find to-be-encoded directory! Aborting."
	exit 1
fi

TEMPDIR="$dir/temp"
OUTDIR="$dir/complete"
INDIR="$dir/to-be-encoded"
FAILDIR="$dir/failed"
LOCK="$dir/.lock"

mkdir -p "$TEMPDIR" "$OUTDIR" "$INDIR" "$FAILDIR"

#LOCK
exec 200>"$LOCK"

if flock -xn 200
then
	rm -rf "${TEMPDIR:?}"/*
	for infile in $INDIR/*
	do
		outfile="$(basename "$infile")"
		outfile="${outfile%.*}.mkv"

		if [[ -f "$OUTDIR/$outfile" ]]
		then
			echo "$infile has already been processed!"
		else

			ffmpeg -i "$infile" -vcodec libx265 -crf $quality $scale $extra -preset $preset -acodec aac -ab 128k -ac 2 "$TEMPDIR/${outfile}"
			rc=$?
			if [[ $rc == 0 ]]
			then
				echo -e "\e[32;1mCompleted encoding $infile\e[0m\n\n\n"
				rm "$infile"
				mv "$TEMPDIR/${outfile}" "$OUTDIR"
			else
				echo -e "\e[31;1mFailed to encode $infile. (RC=$rc)\e[0m\n\n\n"
				mv "$infile" "$FAILDIR"
			fi
		fi
	done
	rm -rf "$TEMPDIR"
fi

#!/usr/bin/env python3

from multiprocessing.pool import ThreadPool
import argparse
import os
import re
import shutil
import tempfile
import time

import ffmpy
from pymediainfo import MediaInfo
from colorama import Fore, Back, Style, init

# Init colorama
init()


def cprint(colour, message):
    colours = {
            "green": Fore.GREEN,
            "blue": Fore.BLUE,
            "red": Fore.RED
            }
    print(colours[colour] + str(message) + Style.RESET_ALL)


def list_non_x265_items(directory):
    codec_map = get_codec_map(directory)

    output_list = []
    for k, v in codec_map.items():
        if v != "HEVC":
            output_list.append(k)

    print()
    cprint("green", "### Files that are not in x265: ")
    cprint("blue", output_list)

    return output_list


def get_codec_map(directory):
    videos = get_videos_in_dir(directory)
    codec_map = get_codecs_of_files(videos)

    cprint("green", "### Map of files and codecs:")
    cprint("blue", codec_map)
    return codec_map


# TODO: This needs to cache the results of all HVEC files somewhere so we don't re-check those. Should make this much faster
def get_codecs_of_files(videos):
    cprint("green", "### Checking codecs used in remaining videos")
    pool = ThreadPool(processes=4)
    t0 = time.time()
    temp_codec_map = pool.map(get_codec, videos)
    cprint("blue", "Gathering list of codecs in files took %s seconds" % (time.time() - t0))

    # Recombine the list of dicts in to a dict
    codec_map = {}
    for item in temp_codec_map:
        for k, v in item.items():
            codec_map[k] = v
    return codec_map


# This speeds things up, no point checking if converted videos already exist
def remove_converted_videos_from_list(videos):
    output = []
    cprint("green", "###  Checking if any videos found have already been converted")
    for video in videos:
        if not re.match(".* - x265\.mkv", video):
            if not os.path.exists(get_renamed_video_name(video)):
                cprint("blue", "%s has not already been convered" % video)
                output.append(video)
            else:
                cprint("blue", "%s has a renamed file in the same folder" % video)
        else:
            cprint("blue", "%s is a converted and renamed file" % video)
    return output


def get_renamed_video_name(filename):
    split_filename = filename.split('.')
    return "%s - x265.mkv" % split_filename[0]


def change_extension_to_mkv(filename):
    split_filename = filename.split('.')
    return "%s.mkv" % split_filename[0]


def get_videos_in_dir(directory):
    files = (os.path.abspath(os.path.join(directory, filename)) for filename in os.listdir(directory))
    raw_videos = []
    cprint("green", "### Testing to see if files are videos...")
    for f in files:
        if is_video(f):
            raw_videos.append(f)

    videos = remove_converted_videos_from_list(raw_videos)
    return videos


def is_video(f):
    result = re.match(".*\.(avi|mkv|mp4|m4v|mpg|mpeg|mov|flv|ts|wmv)", f, re.IGNORECASE)
    if result:
        cprint("blue", "File '%s' is a video" % f)
    else:
        cprint("blue", "File '%s' is NOT a video" % f)
    return result


def get_codec(file_path):
    metadata = MediaInfo.parse(os.path.join(file_path))
    for track in metadata.tracks:
        if track.track_type == "Video":
            return {file_path: track.format}
    raise Exception("No video track found")


def main(args):
    non_x265_items = list_non_x265_items(args.directory)

    scale = "-vf scale=%s:-2" % args.width if args.width else ""

    if not non_x265_items:
        cprint("green", "No files found that were not already x265")
    for infile in non_x265_items:
        cprint("green", "######################################")
        cprint("green", "Starting to convert '%s'" % infile)
        outfile = tempfile.mkstemp(suffix=".mkv")[1]
        cprint("blue", "Transcoding to '%s'" % outfile)
        ff = ffmpy.FFmpeg(
                inputs={infile: None},
                outputs={outfile: "-y -threads 0 -strict -vcodec libx265 -crf %s %s %s -preset %s -acodec aac -ab 160k -ac 2" % (args.quality, scale, args.extra_args, args.preset)})

        try:
            cprint("green", "Running ffmpeg command: '%s'" % ff.cmd)
            ff.run()
            cprint("green", "######################################")
            cprint("green", "Successfully converted '%s'" % infile)
            renamed_file = get_renamed_video_name(infile)
            cprint("blue", "Moving to '%s'..." % renamed_file)
            shutil.move(outfile, renamed_file)
            if args.in_place:
                new_filename = change_extension_to_mkv(infile)
                cprint("blue", "Removing original file '%s'" % infile)
                os.remove(infile)
                cprint("blue", "Renaming to '%s'" % new_filename)
                shutil.move(renamed_file, new_filename)
        except Exception as e:
            cprint("red", "ffmpeg failed! No files will be overwritten")
            print(e)
        if os.path.exists(outfile):
            os.remove(outfile)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose",
                        help="Print more verbose messages",
                        action="store_true")
    parser.add_argument("-w", "--width",
                        help="Set the width if you would like to resize the video",
                        action="store")
    parser.add_argument("-q", "--quality",
                        help="Quality quantizer",
                        default=23,
                        action="store")
    parser.add_argument("-p", "--preset",
                        help="Encoding preset to use",
                        default="slow",
                        action="store")
    parser.add_argument("-e", "--extra-args",
                        help="Any extra arguments to pass to ffmpeg",
                        default="",
                        action="store")
    parser.add_argument("-i", "--in-place",
                        help="Replace files in-place instead of appending ' x265' to the end",
                        default="",
                        action="store_true")
    parser.add_argument("directory",
                        help="The directory to read files from",
                        action="store")

    args = parser.parse_args()

    global VERBOSE
    VERBOSE = args.verbose

    main(args)

#!/usr/bin/env python3

import argparse
import os
import pickle
import re
from copy import deepcopy

from pprint import pprint
from pymediainfo import MediaInfo
from colorama import Fore, Style, init
from tqdm import tqdm

init()


def vprint(colour, message):
    if VERBOSE > 0:
        cprint(colour, message)


def vvprint(colour, message):
    if VERBOSE > 1:
        cprint(colour, message)


def cprint(colour, message):
    colours = {
            "green": Fore.GREEN,
            "blue": Fore.BLUE,
            "red": Fore.RED,
            "yellow": Fore.YELLOW
            }
    print(colours[colour] + str(message) + Style.RESET_ALL)


def is_video(f):
    result = re.match(".*\.(avi|mkv|mp4|m4v|mpg|mpeg|mov|flv|ts|wmv)", f, re.IGNORECASE)
    return result


def get_quality(track):
    if track.width >= 1910 and track.width <= 1930:
        return "1080p"
    if track.width >= 1270 and track.width <= 1290:
        return "720p"
    if track.width < 1000:
        return "SD"
    return "Unknown"


def get_codec(track):
    if track.format == "HEVC":
        return "x265"
    if track.format == "AVC":
        return "x264"
    return "Other"


def parse_season(filename):
    shortname = os.path.basename(filename)
    return re.findall("- (\d+)x\d+ -", shortname)[0]


def parse_per_season_statistics(filemap):
    statistics = {}
    for show in filemap:
        statistics[show] = {}
        for filename, metadata in filemap[show].items():
            season = parse_season(filename)
            if season not in statistics[show]:
                statistics[show][season] = {"episodes": 0, "quality": {}, "codec": {}}
            statistics[show][season]["episodes"] += 1

            for stat in ["quality", "codec"]:
                if not metadata[stat] in statistics[show][season][stat]:
                    statistics[show][season][stat][metadata[stat]] = 0
                statistics[show][season][stat][metadata[stat]] += 1

    return statistics


def parse_per_show_statistics(filemap):
    statistics = {}
    for show in filemap:
        for filename, metadata in filemap[show].items():
            if show not in statistics:
                statistics[show] = {"episodes": 0, "quality": {}, "codec": {}}
            statistics[show]["episodes"] += 1

            for stat in ["quality", "codec"]:
                if not metadata[stat] in statistics[show][stat]:
                    statistics[show][stat][metadata[stat]] = 0
                statistics[show][stat][metadata[stat]] += 1

    return statistics


def parse_global_statistics(show_statistics):
    statistics = {"episodes": 0, "codec": {}, "quality": {}}
    for metadata in show_statistics.values():
        statistics["episodes"] += metadata["episodes"]
        for stat in ["quality", "codec"]:
            for item in metadata[stat]:
                if item not in statistics[stat]:
                    statistics[stat][item] = 0
                statistics[stat][item] += metadata[stat][item]
    return statistics


def get_codec_colour(codec):
    if codec == "x265":
        return "green"
    return "red"


def get_quality_colour(quality):
    if quality == "1080p":
        return "green"
    if quality == "720p":
        return "yellow"
    return "red"


def print_metadata(metadata, indent=0):
    indent = ' ' * indent
    cprint("blue", "%sEpisodes: %s" % (indent, metadata["episodes"]))
    cprint("blue", "%sQuality:" % indent)
    for quality, count in metadata["quality"].items():
        colour = get_quality_colour(quality)
        cprint(colour, "%s  %s: %s (%s)" % (indent, quality, count, '{:.1%}'.format(count / metadata["episodes"])))

    cprint("blue", "%sCodec:" % indent)
    for codec, count in metadata["codec"].items():
        colour = get_codec_colour(codec)
        cprint(colour, "%s  %s: %s (%s)" % (indent, codec, count, '{:.1%}'.format(count / metadata["episodes"])))


def print_season_totals(season_statistics):
    print("SEASON TOTALS:")
    for show, show_metadata in season_statistics.items():
        cprint("green", "  %s" % show)
        for season, season_metadata in show_metadata.items():
            print("    Season %s" % season)
            print_metadata(season_metadata, indent=6)
        print()


def print_show_totals(show_statistics):
    print("SHOW TOTALS:")
    for show, metadata in show_statistics.items():
        cprint("green", "  %s" % show)
        print_metadata(metadata, indent=4)
        print()


def print_global_totals(global_statistics):
    print("GLOBAL TOTALS:")
    print_metadata(global_statistics, indent=2)


def get_videos_in_list(filenames):
    videos = []
    for video in filenames:
        if is_video(video):
            videos.append(video)
    videos.sort()
    return videos


def prune_filemap(filemap):
    tempmap = deepcopy(filemap)
    for dirpath in tempmap:
        for video in tempmap[dirpath]:
            videopath = os.path.join(dirpath, video)
            if not os.path.exists(videopath):
                vprint("blue", "Removing %s from cache" % videopath)
                del filemap[dirpath][video]
    return filemap


def update_filemap(data_file, filemap, directory):
    cprint("green", "Checking for deleted files...")
    filemap = prune_filemap(filemap)
    for dirpath, dirnames, filenames in os.walk(directory, followlinks=True):
        cprint("green", "Working in directory: %s" % dirpath)

        videos = get_videos_in_list(filenames)
        vprint("blue", "Total videos in %s: %s" % (dirpath, len(videos)))

        current_video = 0
        if VERBOSE == 0:
            videos = tqdm(videos)
        for video in videos:
            if dirpath not in filemap:  # Only create if there are videos for this path
                filemap[dirpath] = {}
            video_path = os.path.join(dirpath, video)
            video_size = os.stat(video_path).st_size
            current_video += 1
            if video in filemap[dirpath]:
                vvprint("blue", "Found %s in cache..." % video)
                if filemap[dirpath][video]["size"] == video_size:
                    vprint("blue", "Using cache (%s/%s) %s" % (current_video, len(videos), video))
                    continue
                vvprint("blue", "Filesize differs. Invalidating cache")
            vprint("blue", "Parsing (%s/%s) %s" % (current_video, len(videos), video))
            metadata = MediaInfo.parse(video_path)
            for track in metadata.tracks:
                if track.track_type == "Video":
                    quality = get_quality(track)
                    codec = get_codec(track)
                    break
            filemap[dirpath][video] = {
                        "size": os.stat(video_path).st_size,
                        "quality": quality,
                        "codec": codec
                    }
            if VERBOSE >= 2:
                cprint("blue", "Video details:")
                pprint(filemap[dirpath][video])
                print('---------------')
        vprint("green", "Saving out partial filemap...")
        with open(data_file, "wb") as f:
            pickle.dump(filemap, f)
    return filemap


def main(args):
    data_file = os.path.join(os.path.expanduser("~"), ".simple-report-data")

    filemap = {}
    if os.path.exists(data_file) and not args.ignore_cache:
        vprint("green", "Loading from cache...")
        with open(data_file, "rb") as f:
            filemap = pickle.load(f)

    filemap = update_filemap(data_file, filemap, os.path.realpath(args.directory))

    if VERBOSE >= 2:
        cprint("green", "Complete map of files:")
        pprint(filemap)

    show_statistics = parse_per_show_statistics(filemap)
    season_statistics = parse_per_season_statistics(filemap)
    global_statistics = parse_global_statistics(show_statistics)

    if VERBOSE >= 2:
        cprint("green", "Show statistics:")
        pprint(show_statistics)
        cprint("green", "Season statistics:")
        pprint(season_statistics)
        cprint("green", "Global statistics:")
        pprint(global_statistics)

    print('\n')
    print_season_totals(season_statistics)
    print()
    print_show_totals(show_statistics)
    print()
    print_global_totals(global_statistics)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-v", "--verbose",
                        help="Print more verbose messages",
                        default=0,
                        action="count")
    parser.add_argument("-i", "--ignore-cache",
                        help="Ignore the cache and rebuild it",
                        action="store_true")
    parser.add_argument("directory",
                        help="The directory to read files from",
                        action="store")

    args = parser.parse_args()

    global VERBOSE
    VERBOSE = args.verbose

    main(args)

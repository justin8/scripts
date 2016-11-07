#!/usr/bin/env python3

import argparse
import os
import pickle
import re
import tempfile

from pprint import pprint
from pymediainfo import MediaInfo
from colorama import Fore, Style, init

init()


def vprint(colour, message):
    if VERBOSE:
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
    for filename, metadata in filemap.items():
        season = parse_season(filename)
        if season not in statistics:
            statistics[season] = {"episodes": 0, "quality": {}, "codec": {}}
        statistics[season]["episodes"] += 1

        for stat in ["quality", "codec"]:
            if not metadata[stat] in statistics[season][stat]:
                statistics[season][stat][metadata[stat]] = 0
            statistics[season][stat][metadata[stat]] += 1

    return statistics


def print_season_totals(statistics):
    for season, metadata in statistics.items():
        print("Season %s" % season)
        cprint("blue", "  Quality:")
        for quality, count in statistics[season]["quality"].items():
            colour = "red"
            if quality == "1080p":
                colour = "green"
            if quality == "720p":
                colour = "yellow"
            cprint(colour, "    %s: %s" % (quality, '{:.1%}'.format(count / metadata["episodes"])))
        cprint("blue", "  Codec:")
        for codec, count in statistics[season]["codec"].items():
            colour = "red"
            if codec == "x265":
                colour = "green"
            cprint(colour, "    %s: %s" % (codec, '{:.1%}'.format(count / metadata["episodes"])))


def print_series_totals(statistics):
    totals = {"episodes": 0}

    for item in statistics:
        totals["episodes"] += statistics[item]["episodes"]

    for stat in ["quality", "codec"]:
        totals[stat] = {}
        for item in statistics:
            for k, v in statistics[item][stat].items():
                if k not in totals[stat]:
                    totals[stat][k] = 0
                totals[stat][k] += v

    cprint("green", "TOTALS:")
    cprint("blue", "  Episodes: %s" % totals["episodes"])

    cprint("blue", "  Quality:")
    for item in totals["quality"]:
        colour = "red"
        if item == "1080p":
            colour = "green"
        if item == "720p":
            colour = "yellow"
        cprint(colour, "    %s: %s (%s)" % (item, totals["quality"][item], '{:.1%}'.format(totals["quality"][item] / totals["episodes"])))

    cprint("blue", "  Codec:")
    for item in totals["codec"]:
        colour = "red"
        if item == "x265":
            colour = "green"
        cprint(colour, "    %s: %s (%s)" % (item, totals["codec"][item], '{:.1%}'.format(totals["codec"][item] / totals["episodes"])))


def main(args):
    filemap = {}
    data_file = os.path.join(tempfile.gettempdir(), os.path.basename(args.directory))

    if os.path.exists(data_file) and not args.ignore_cache:
        vprint("green", "Loading from cache...")
        with open(data_file, "rb") as f:
            filemap = pickle.load(f)
    else:
        for dirpath, dirnames, filenames in os.walk(args.directory):
            vprint("green", "Working in directory: %s" % dirpath)
            videos = []
            for video in filenames:
                if is_video(video):
                    videos.append(os.path.join(dirpath, video))
            videos.sort()

            videos_in_folder = len(videos)
            vprint("blue", "Total videos in %s: %s" % (dirpath, videos_in_folder))

            current_video = 0
            for video in videos:
                current_video += 1
                vprint("blue", "Parsing (%s/%s) %s" % (current_video, videos_in_folder, os.path.basename(video)))
                metadata = MediaInfo.parse(video)
                for track in metadata.tracks:
                    if track.track_type == "Video":
                        quality = get_quality(track)
                        codec = get_codec(track)
                        break
                filemap[video] = {
                            "quality": quality,
                            "codec": codec
                        }
                if VERBOSE:
                    cprint("blue", "Video details:")
                    pprint(filemap[video])
                    print('---------------')
                with open(data_file, "wb") as f:
                    pickle.dump(filemap, f)

    if VERBOSE:
        cprint("green", "Complete map of files:")
        pprint(filemap)

    statistics = parse_per_season_statistics(filemap)

    if VERBOSE:
        cprint("green", "Statistics:")
        pprint(statistics)
        cprint("green", "Totals:")
        pprint(statistics)

    print_season_totals(statistics)
    print()
    print_series_totals(statistics)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-v", "--verbose",
                        help="Print more verbose messages",
                        action="store_true")
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

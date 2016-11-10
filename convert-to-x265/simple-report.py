#!/usr/bin/env python3

from copy import deepcopy
import argparse
import hashlib
import os
import pickle
import re

from colorama import Fore, Style, init
from pprint import pprint
from pymediainfo import MediaInfo
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
    video_extensions = ("avi", "mkv", "mp4", "mpg", "mpeg", "mov", "m4v", "flv", "ts", "wmv")
    return f.endswith(video_extensions)


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
    result = re.findall("[\s\.](?:(\d+)x\d+(?:[x-]\d+){0,2}|S(\d\d?)E\d\d?)[\s\.\-]", shortname)
    return result[0][0] if result[0][0] else result[0][1]


def parse_per_season_statistics(filemap):
    statistics = {}
    for show in filemap:
        statistics[show] = {}
        vprint("green", "Working in directory: %s" % show)
        for filename, metadata in filemap[show].items():
            vprint("blue", "Parsing per-season statistics for %s" % filename)
            season = parse_season(filename)
            if season not in statistics[show]:
                statistics[show][season] = {"episodes": 0, "size": 0, "quality": {}, "codec": {}}
            statistics[show][season]["episodes"] += 1
            statistics[show][season]["size"] += metadata["size"]

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
                statistics[show] = {"episodes": 0, "size": 0, "quality": {}, "codec": {}}
            statistics[show]["episodes"] += 1
            statistics[show]["size"] += metadata["size"]

            for stat in ["quality", "codec"]:
                if not metadata[stat] in statistics[show][stat]:
                    statistics[show][stat][metadata[stat]] = 0
                statistics[show][stat][metadata[stat]] += 1

    return statistics


def parse_global_statistics(show_statistics):
    statistics = {"episodes": 0, "size": 0, "codec": {}, "quality": {}}
    for metadata in show_statistics.values():
        statistics["episodes"] += metadata["episodes"]
        statistics["size"] += metadata["size"]
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


def save_html(show_statistics, global_statistics):
    with open("simple-report.html", "w") as f:
        f.write('<html><head><title>TV Shows codec report</title><style> \
                 #shows {font-family: "Trebuchet MS", Arial, Helvetica, sans-serif; border-collapse: collapse; width: 100%; } \
                 #shows td {border: 1px solid \
                 #ddd; padding: 8px; text-align: right} \
                 #shows td.left {text-align: left} \
                 #shows td.center {text-align: center} \
                 #shows th {border: 1px solid #ddd; padding: 8px; text-align: center; padding-top: 12px; padding-bottom: 12px; background-color: #4CAF50; color: white; } \
                 #shows tr:nth-child(even){background-color: #f2f2f2;} \
                 #shows tr:hover {background-color: #ddd;}</style> \
                 <script type="text/javascript" src="http://www.kryogenix.org/code/browser/sorttable/sorttable.js"></script></head>')
        f.write('<html><body><table class="sortable" id="shows"><tr><th>Show</th><th>Codec progress</th><th>Quality progress</th><th>Size (GB)</th><th>Episodes</th><th>1080p</th><th>720p</th><th>SD</th><th>Unknown</th><th>x265</th><th>x264</th><th>Other</th></tr>')

        for show, metadata in show_statistics.items():
            f.write(metadata_to_table_row(show, metadata))

        f.write('<tfoot><tr>%s%s%s%s%s%s%s%s%s%s%s%s</tr></tfoot>' % (
            html_cell("TOTALS"),
            html_cell(html_progress(global_statistics["codec"]["x265"] if "x265" in global_statistics["codec"] else 0, global_statistics["episodes"])),
            html_cell(html_progress(global_statistics["quality"]["1080p"] if "1080p" in global_statistics["quality"] else 0, global_statistics["quality"])),
            html_cell("%3.1f %s" % (global_statistics["size"] / 1024 / 1024 / 1024, "GiB")),
            html_cell(global_statistics["episodes"]),
            html_cell(global_statistics["quality"]["1080p"] if "1080p" in global_statistics["quality"] else 0),
            html_cell(global_statistics["quality"]["720p"] if "720p" in global_statistics["quality"] else 0),
            html_cell(global_statistics["quality"]["SD"] if "SD" in global_statistics["quality"] else 0),
            html_cell(global_statistics["quality"]["Unknown"] if "Unknown" in global_statistics["quality"] else 0),
            html_cell(global_statistics["codec"]["x265"] if "x265" in global_statistics["codec"] else 0),
            html_cell(global_statistics["codec"]["x264"] if "x264" in global_statistics["codec"] else 0),
            html_cell(global_statistics["codec"]["Other"] if "Other" in global_statistics["codec"] else 0)))
        f.write('</table></body></html>')


def html_cell(data):
    return "<td>%s</td>" % data


def html_progress(value, maximum):
    return '<progress value="%s" max="%s"/>' % (value, maximum)


def metadata_to_table_row(show, metadata):
    out = "<tr>"
    out += html_cell(os.path.basename(show))
    out += html_cell(html_progress(metadata["codec"]["x265"] if "x265" in metadata["codec"] else 0, metadata["episodes"]))
    out += html_cell(html_progress(metadata["quality"]["1080p"] if "1080p" in metadata["quality"] else 0, metadata["episodes"]))
    out += html_cell("%3.1f %s" % (metadata["size"] / 1024 / 1024 / 1024, "GiB"))
    out += html_cell(metadata["episodes"])
    out += html_cell(metadata["quality"]["1080p"] if "1080p" in metadata["quality"] else 0)
    out += html_cell(metadata["quality"]["720p"] if "720p" in metadata["quality"] else 0)
    out += html_cell(metadata["quality"]["SD"] if "SD" in metadata["quality"] else 0)
    out += html_cell(metadata["quality"]["Unknown"] if "Unknown" in metadata["quality"] else 0)
    out += html_cell(metadata["codec"]["x265"] if "x265" in metadata["codec"] else 0)
    out += html_cell(metadata["codec"]["x264"] if "x264" in metadata["codec"] else 0)
    out += html_cell(metadata["codec"]["Other"] if "Other" in metadata["codec"] else 0)
    out += "</tr>"
    return out


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
        changes = False
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
            changes = True
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
        if changes:
            vprint("green", "Saving out partial filemap...")
            with open(data_file, "wb") as f:
                pickle.dump(filemap, f)
    return filemap


def main(args):
    directory = os.path.realpath(args.directory)
    data_file_name = hashlib.md5(bytes(directory, 'ascii')).hexdigest()
    data_file_path = os.path.join(os.path.expanduser("~"), ".simple-report-data")
    data_file = os.path.join(data_file_path, data_file_name)

    if not os.path.exists(data_file_path):
        os.mkdir(data_file_path)

    filemap = {}
    if os.path.exists(data_file) and not args.ignore_cache:
        vprint("green", "Loading from cache...")
        with open(data_file, "rb") as f:
            filemap = pickle.load(f)

    if not args.output_only:
        filemap = update_filemap(data_file, filemap, os.path.realpath(directory))

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

    save_html(show_statistics, global_statistics)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-v", "--verbose",
                        help="Print more verbose messages",
                        default=0,
                        action="count")
    parser.add_argument("-i", "--ignore-cache",
                        help="Ignore the cache and rebuild it",
                        action="store_true")
    parser.add_argument("-o", "--output-only",
                        help="Just read the cache but don't update it at all",
                        default=False,
                        action="store_true")
    parser.add_argument("directory",
                        help="The directory to read files from",
                        action="store")

    args = parser.parse_args()

    global VERBOSE
    VERBOSE = args.verbose

    main(args)

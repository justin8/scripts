#!/usr/bin/env python3

from dataclasses import dataclass
from collections.abc import Sequence
from bs4 import BeautifulSoup
import bs4
from urllib.request import Request, urlopen, urlretrieve
import re
import argparse
import os
from pathlib import Path

@dataclass
class Song:
    title: str
    url: str

    def filename(self):
        return "".join(x for x in self.title if (x.isalnum() or x in "._-–[]() ")) + ".zip"

class urlBuilder():
    iterations = 0
    base_url = "https://bsaber.com/songs/new/?bookmarked_by=%s"
    numbered_url = "https://bsaber.com/songs/new/page/%s/?bookmarked_by=%s"

    def __init__(self, username: str):
        self.username = username
    
    def next_url(self):
        if self.iterations == 0:
            self.iterations +=  1
            return self.base_url % self.username
        self.iterations += 1
        return self.numbered_url % (self.iterations, self.username)

# Parse a bsaber page
def get_songs_from_page(soup):

    rows = soup.findAll("div", {"class": "row"})
    songs: Sequence[Song] = []

    for row in rows:
        columns = row.findAll("div", {"class": "columns"})
        if len(columns) == 2:
            if columns[1].findAll("h4", {"class": "entry-title"}):
                songs.append(parse_song_from_block(columns[1]))

    print(f"Found {len(songs)} songs on page")
    return songs

def parse_song_from_block(block: bs4.element.Tag) -> Song:
    for link in block.findAll("a"):
        if "title" in link.attrs.keys():
            title = link.attrs["title"]
    
    url = block.findAll("a", {"class": "-download-zip"})[0].attrs["href"]

    return Song(title, url)


def end_of_results(soup):
    for block in soup.findAll("p"):
        if re.findall("No articles found matching your query", block.decode()):
            return True
    return False


def main():
    parser = argparse.ArgumentParser(description="Download bookmarkded songs from bsaber.com to the current directory")
    parser.add_argument("username", type=str, help="The username whose bookmarks to download")

    args = parser.parse_args()

    url_builder = urlBuilder(args.username)
    songs = []

    while True:
        url = url_builder.next_url()
        print(f"Downloading results from {url}")

        req = Request(url)
        html_page = urlopen(req)
        soup = BeautifulSoup(html_page, "lxml")

        if end_of_results(soup):
            print("Found end of results page.")
            break
        songs += get_songs_from_page(soup)

    for song in songs:
        print("")
        print("Found song:")
        print(f"Title: {song.title}")
        print(f"URL: {song.url}")
        filename = song.filename()

        if os.path.exists(filename):
            print("Status: Already downloaded")
            continue

        print("Status: Downloading...")
        urlretrieve(song.url, filename)
        filesize_mb = os.path.getsize(filename) / 1024 / 1024
        print(f"Filesize: {'{:.2f}'.format(filesize_mb)}MB")


        
if __name__ == "__main__":
    main()
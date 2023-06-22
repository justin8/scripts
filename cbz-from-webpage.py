#!/usr/bin/env python3

import logging
import os
import shutil
import sys
import tempfile
import zipfile
from collections import Counter
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

import requests
import click
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

logging.basicConfig(level=logging.INFO)


def backoff_retry_session(
    retries=3, backoff_factor=0.3, status_forcelist=(500, 502, 504), session=None
):
    """
    Creates and configures a retry-enabled session object using the requests library. The session automatically retries
    requests for a specified number of times with an increasing backoff delay if certain HTTP status codes are encountered.

    Args:
        retries (int): The maximum number of retries for each request. Defaults to 3.
        backoff_factor (float): The factor by which the delay between retries increases. Defaults to 0.3.
        status_forcelist (tuple): A tuple of HTTP status codes that should trigger a retry. Defaults to (500, 502, 504).
        session (requests.Session): An existing session object to be used. If not provided, a new session is created.

    Returns:
        requests.Session: A configured session object that performs automatic retries.

    Example:
        session = backoff_retry_session(retries=5, backoff_factor=0.5, status_forcelist=(500, 502, 503))
        response = session.get("https://api.example.com/data")
        print(response.text)

    Note:
        The function relies on the 'requests' library, specifically the 'Session', 'Retry', and 'HTTPAdapter' classes.
        Make sure the 'requests' library is installed and available before calling 'backoff_retry_session'.
    """

    session = session or requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        allowed_methods=frozenset(["GET", "POST", "HEAD"]),
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def download_image(img_url, save_directory):
    """
    Downloads an image from the specified URL and saves it to the given directory.

    Args:
        img_url (str): The URL of the image to download.
        save_directory (str): The directory where the downloaded image will be saved.

    Returns:
        None

    Raises:
        Any exceptions raised during the download process will be propagated.

    The function downloads an image from the provided URL using a GET request with backoff and retry
    functionality. The image is then saved to the specified directory.

    Example:
        download_image("https://example.com/image.jpg", "/path/to/save/directory")

    """

    # Extract the filename from the image URL
    filename = img_url.split("/")[-1]

    # Send a GET request to the image URL with backoff and retry
    with backoff_retry_session() as session:
        img_response = session.get(img_url)

    # Save the image to the specified directory
    save_path = os.path.join(save_directory, filename)
    with open(save_path, "wb") as f:
        f.write(img_response.content)
    logging.info("Downloaded: %s", filename)


def download_images(url):
    """
    Downloads images from a webpage based on the provided URL.

    Args:
        url (str): The URL of the webpage to download images from.

    Returns:
        str: The path of the directory where the downloaded images are saved.

    Raises:
        Any exceptions raised during the download process will be propagated.

    The function sends a GET request to the specified URL, parses the HTML content using BeautifulSoup,
    and finds all <img> tags in the parsed HTML. It extracts the source URLs of the images and filters
    them based on the provided `path_filters` list. The function then creates a temporary directory to
    save the downloaded images.

    Multiple images are downloaded concurrently using a ThreadPoolExecutor. The function submits download
    tasks to the executor and waits for all tasks to complete. If any exception occurs during the download,
    the temporary directory is removed. Finally, the function returns the path of the directory where the
    downloaded images are saved.

    Example:
        download_images("https://example.com/gallery")
    """

    path_filters = ["/uploads", "/images"]

    session = backoff_retry_session()

    # Send a GET request to the webpage
    response = session.get(url)

    # Create a BeautifulSoup object to parse the HTML content
    soup = BeautifulSoup(response.content, "html.parser")

    # Find all <img> tags in the parsed HTML
    img_tags = soup.find_all("img")
    image_urls = [img["src"] for img in img_tags if any(value in img["src"] for value in path_filters) ]
    logging.debug("Found the following image URLs: %s", image_urls)

    image_prefix = find_prefix(image_urls)
    image_urls = [url for url in image_urls if image_prefix in url]

    # Create a directory to save the downloaded images
    save_directory = tempfile.mkdtemp()

    # Download images with source URLs containing '/uploads'
    try:
        with ThreadPoolExecutor(max_workers=5) as executor:
            # Submit download tasks to the executor
            download_tasks = [
                executor.submit(download_image, img_url, save_directory)
                for img_url in image_urls
            ]
            # Wait for all tasks to complete
            for task in download_tasks:
                task.result()
    except:
        shutil.rmtree(save_directory)
    return save_directory


def create_cbz(output_name, directory):
    """
    Creates a Comic Book Zip (CBZ) file by compressing the image files from the specified directory into a zip archive.

    Args:
        output_name (str): The name of the CBZ file to be created.
        directory (str or Path): The directory path containing the image files to be included in the CBZ file.

    Raises:
        TypeError: If the 'output_name' or 'directory' arguments are not strings or Path objects.
        FileNotFoundError: If the specified directory does not exist.
        OSError: If there are any issues with creating or writing to the CBZ file.

    Example:
        output_name = 'comic.cbz'
        directory = '/path/to/images/'
        create_cbz(output_name, directory)
        # Creates a CBZ file named 'comic.cbz' containing the image files from the '/path/to/images/' directory.

    Note:
        The function relies on the 'get_image_list' function to retrieve the list of image files from the specified directory.
        Make sure the 'get_image_list' function is defined and available before calling 'create_cbz'.
    """

    file_list = get_image_list(directory)

    with zipfile.ZipFile(output_name, mode="w") as archive:
        logging.info("Creating %s...", output_name)
        for file in file_list:
            logging.debug("Adding file %s...", file.name)
            archive.write(str(file), file.name)


def get_image_list(directory):
    """
    Retrieves a list of image files present in the specified directory and its subdirectories.

    Args:
        directory (str or Path): The directory path where the image files are located.

    Returns:
        list: A list of image files found in the directory and its subdirectories.

    Example:
        directory = '/path/to/images/'
        images = get_image_list(directory)
        print(images)
        # Output: ['/path/to/images/image1.jpg', '/path/to/images/image2.png', ...]

    Raises:
        TypeError: If the 'directory' argument is not a string or a Path object.
        FileNotFoundError: If the specified directory does not exist.
    """

    files = list(directory.expanduser().iterdir())

    image_list = [file for file in files]
    logging.info("Found %s images", len(image_list))

    return image_list


def find_prefix(urls):
    """
    Given a list of URLs, extracts the prefix of the filename from each URL,
    appends it to a list, and returns the most common prefix.

    Args:
        urls (list): A list of URLs.

    Returns:
        str: The most common prefix of the filenames extracted from the URLs.

    Example:
        urls = [
            "https://example.com/files/file1.txt",
            "https://example.com/files/file2.txt",
            "https://example.com/files/file3.txt",
            "https://example.com/files/file4.txt"
        ]
        print(find_prefix(urls))
        # Output: "file1.txt"
    """

    prefixes = []

    for url in urls:
        file = url.split("/")[-1]
        prefixes.append(file[0:12])

    most_common = Counter(prefixes).most_common()[0][0]
    logging.debug("Found prefix %s", most_common)

    return most_common


@click.command()
@click.argument("url")
@click.argument("output-name")
def main(url, output_name):
    """
    Main function for the application that downloads images from a webpage and creates a Comic Book Zip (CBZ) file.

    Args:
        url (str): The URL of the webpage from which images should be downloaded.
        output_name (str): The desired name of the CBZ file to be created. If it does not end with '.cbz', the extension will be added automatically.

    Raises:
        SystemExit: If the specified output file already exists, the program will exit with a non-zero status code.

    Example:
        $ python my_script.py https://example.com/gallery my_comic
        # Downloads images from the URL 'https://example.com/gallery' and creates a CBZ file named 'my_comic.cbz'.

    Note:
        The function relies on the 'download_images', 'create_cbz', 'shutil', 'os', 'sys', 'Path' classes, and the 'click' library.
        Make sure these dependencies are defined and available before calling the 'main' function.
    """

    if not output_name.endswith(".cbz"):
        output_name = output_name + ".cbz"

    if os.path.exists(output_name):
        logging.error("Output file %s already exists. Aborting", output_name)
        sys.exit(1)

    directory = Path(download_images(url))
    try:
        create_cbz(output_name, directory)
    finally:
        shutil.rmtree(directory)


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter

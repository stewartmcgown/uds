# -*- coding: utf-8 -*-
from __future__ import print_function
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.http import MediaIoBaseUpload
from googleapiclient.http import MediaIoBaseDownload
from httplib2 import Http
from oauth2client import file, client, tools
from mimetypes import MimeTypes
from tabulate import tabulate
from io import StringIO

import sys
import base64
import math
import urllib.request
import ntpath
import mmap
import io
import os
import time
import shutil
import cryptography
import concurrent.futures
import byte_format

import Encoder

from classes import *
from API import *

DOWNLOADS_FOLDER = "downloads"
TEMP_FOLDER = "tmp"

USE_MULTITHREADED_UPLOADS = True

MAX_DOC_LENGTH = 1000000
MAX_RAM_MB = 1024
MAX_WORKERS_ALLOWED = 10
CHUNK_READ_LENGTH_BYTES = 750000


class UDS():
    def __init__(self):
        self.api = GoogleAPI()

    def build_file(self, parent_id):
        # This will fetch the Docs one by one, concatting them
        # to a local base64 file. The file will then be converted
        # from base64 to the appropriate mimetype
        items = self.api.recursive_list_folder(parent_id)

        folder = self.api.get_file(parent_id)

        if not items:
            print('No parts found.')
        else:
            # Fix part as int
            for item in items:
                item['properties']['part'] = int(item['properties']['part'])

            #print('Parts of %s:' % folder['name'])
            items.sort(key=lambda x: x['properties']['part'], reverse=False)

            f = open("%s/%s" % (get_downloads_folder(), folder['name']), "wb")

            for i, item in enumerate(items):
                #print('%s (%s)' % (item['properties']['part'], item['id']))
                progress_bar("Downloading %s" % folder['name'], i, len(items))

                encoded_part = self.download_part(item['id'])

                # Decode
                decoded_part = Encoder.decode(encoded_part)

                # Append decoded part to file
                f.write(decoded_part)

            f.close()

            progress_bar("Downloaded %s" % folder['name'], 1, 1)

    def download_part(self, part_id):
        request = self.api.export_media(part_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
        return fh.getvalue()

    # Upload a chunked part to drive and return the size of the chunk
    def upload_chunked_part(self, chunk):
        #print("Chunk %s, bytes %s to %s" % (chunk.part, chunk.range_start, chunk.range_end))

        with open(chunk.path, "r") as fd:
            mm = mmap.mmap(fd.fileno(), 0, access=mmap.ACCESS_READ)
            chunk_bytes = mm[chunk.range_start:chunk.range_end]

        encoded_chunk = Encoder.encode(chunk_bytes)

        file_metadata = {
            'name': chunk.media.name + str(chunk.part),
            'mimeType': 'application/vnd.google-apps.document',
            'parents': [chunk.parent],
            'properties': {
                'part': str(chunk.part)
            }
        }

        mediaio_file = MediaIoBaseUpload(io.StringIO(encoded_chunk),
                                         mimetype='text/plain')

        self.api.upload_single_file(mediaio_file, file_metadata)

        return len(chunk_bytes)

    def do_chunked_upload(self, path):
        # Prepare media file
        size = os.stat(path).st_size
        encoded_size = size * (4/3)

        root = self.api.get_base_folder()['id']

        media = UDSFile(ntpath.basename(path), None, MimeTypes().guess_type(urllib.request.pathname2url(path))[0],
                        byte_format.format(size), byte_format.format(encoded_size), parents=[root], size_numeric=size)

        parent = self.api.create_media_folder(media)
        print("Created parent folder with ID %s" % (parent['id']))

        # Should be the same
        no_chunks = math.ceil(size / CHUNK_READ_LENGTH_BYTES)
        no_docs = math.ceil(encoded_size / MAX_DOC_LENGTH)
        print("Requires %s chunks to read and %s docs to store." %
              (no_chunks, no_docs))

        # Append all chunks to chunk list
        chunk_list = list()
        for i in range(no_docs):
            chunk_list.append(
                Chunk(path, i, size, media=media, parent=parent['id'])
            )

        # Begin timing run
        start_time = time.time()

        total = 0

        for chunk in chunk_list:
            total = total + 1
            self.upload_chunked_part(chunk)
            elapsed_time = round(time.time() - start_time, 2)
            current_speed = round(total / (elapsed_time * 1024 * 1024), 2)
            progress_bar("Uploading %s at %sMB/s" %
                         (media.name, current_speed), total, size)

         #Concurrently execute chunk upload and report back when done.
        """with concurrent.futures.ProcessPoolExecutor(max_workers=MAX_WORKERS_ALLOWED) as executor:
            for file in executor.map(self.upload_chunked_part, chunk_list):
                total = total + file
                elapsed_time = round(time.time() - start_time, 2)
                current_speed = round(total / (elapsed_time * 1024 * 1024), 2)
                progress_bar("Uploading %s at %sMB/s" %
                             (media.name, current_speed), total, size)"""

        finish_time = round(time.time() - start_time, 1)

        progress_bar("Uploaded %s in %ss" %
                     (media.name, finish_time), total, size)


def get_downloads_folder():
    if not os.path.exists(DOWNLOADS_FOLDER):
        os.makedirs(DOWNLOADS_FOLDER)
    return DOWNLOADS_FOLDER


def characters_to_bytes(chars):
    return round((3/4) * chars)


def progress_bar(title, value, endvalue, bar_length=30):
    percent = float(value) / endvalue
    arrow = '█' * int(round(percent * bar_length))
    spaces = ' ' * (bar_length - len(arrow))

    sys.stdout.write(
        "\r"+title+": [{0}] {1}%".format(arrow + spaces, int(round(percent * 100))))
    sys.stdout.flush()


def write_status(status):
    sys.stdout.write("\r%s" % status)
    sys.stdout.flush()


def assign_property(id):
    body = {
        'key': 'uds',
        'value': 'true',
        'visibility': 'PUBLIC'
    }

    try:
        p = service.properties().insert(
            fileId=id, body=body).execute()
        return p
    except error:
        print('An error occurred: %s' % error)
    return None


def convert_file(file_id, service):
    # Get file metadata
    metadata = service.files().get(fileId=file_id, fields="name").execute()

    # Download the file and then call do_upload() on it
    request = service.files().get_media(fileId=file_id)
    path = f"{get_downloads_folder()}/{metadata['name']}"
    fh = io.FileIO(path, "wb")
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()

    print("Downloaded %s" % metadata['name'])
    do_upload(path, service)

    # An alternative method would be to use partial download headers
    # and convert and upload the parts individually. Perhaps a
    # future release will implement this.


def main():
    uds = UDS()

    # Initial look for folder and first time setup if not
    uds_root = uds.api.get_base_folder()
    BASE_FOLDER = uds_root

    # Options
    options = """
    push     Uploads a file from this computer [path_to_file]
    pull     Downloads a UDS file [id]
    list     Finds all UDS files
    delete   Deletes a UDS file [id]
    """

    if len(sys.argv) > 1:
        command = str(sys.argv[1])
        if command == "push":
            if sys.argv[2] == "--disable-multi":
                USE_MULTITHREADED_UPLOADS = False
                file_path = sys.argv[3]
            else:
                file_path = sys.argv[2]
            uds.do_chunked_upload(file_path)
        elif command == "pull":
            uds.build_file(sys.argv[2])
        elif command == "list":
            uds.api.print_list_files()
        elif command == "convert":
            if sys.argv[2] == "--delete":
                DELETE_FILE_AFTER_CONVERT = True
                id = sys.argv[3]
            else:
                id = sys.argv[2]
            convert_file(id)
        else:
            print(options)
    else:
        print(options)


if __name__ == '__main__':
    main()

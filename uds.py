# -*- coding: utf-8 -*-
from googleapiclient.http import MediaIoBaseUpload
from googleapiclient.http import MediaIoBaseDownload
from mimetypes import MimeTypes
from tabulate import tabulate
from tqdm import tqdm

import sys
import math
import urllib.request
import ntpath
import mmap
import io
import os
import Format
import json
import hashlib

import FileParts
import Encoder
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

    def delete_file(self, id, name=None, mode_=None):
        """Deletes a given file

        Use the Google Drive API to delete a file given its ID.

        Args:
            id (str): ID of the file
            name (str): Name of the file

        """
        try:
            self.api.delete_file(id)
            if name is not None:
                # If Alpha commands are used, this displays the name
                print("Deleted %s" % name)
            else:
                # If UDS commands are used, this displays the ID
                print("Deleted %s" % id)
        except IOError:
            if mode_ != "quiet":
                print("%s File was not a UDS file" % GoogleAPI.ERROR_OUTPUT)
            else:
                print("", end='')

    def build_file(self, parent_id):
        """Download a uds file

        This will fetch the Docs one by one, concatting them
        to a local base64 file. The file will then be converted
        from base64 to the appropriate mimetype.

        Args:
            parent_id (str): The ID of the containing folder
        """
        items = self.api.recursive_list_folder(parent_id)

        folder = self.api.get_file(parent_id)

        if not items:
            print('No parts found.')
            return

        # Fix part as int
        for item in items:
            item['properties']['part'] = int(item['properties']['part'])

        #print('Parts of %s:' % folder['name'])
        items.sort(key=lambda x: x['properties']['part'], reverse=False)

        f = open("%s/%s" % (get_downloads_folder(), folder['name']), "wb")
        progress_bar_chunks = tqdm(total=len(items),
                                   unit='chunks', dynamic_ncols=True, position=0)
        progress_bar_speed = tqdm(total=len(items) * CHUNK_READ_LENGTH_BYTES, unit_scale=1,
                                  unit='B', dynamic_ncols=True, position=1)

        for _, item in enumerate(items):
            encoded_part = self.download_part(item['id'])

            # Decode
            decoded_part = Encoder.decode(encoded_part)
            progress_bar_chunks.update(1)
            progress_bar_speed.update(CHUNK_READ_LENGTH_BYTES)

            # Append decoded part to file
            f.write(decoded_part)

        print(" \r")

        file_hash = self.hash_file(f.name)

        f.close()

        original_hash = folder.get("properties").get("sha256")
        if (file_hash != original_hash and original_hash is not None):
            print("Failed to verify hash\nDownloaded file had hash %s compared to original %s",
                  (file_hash[:9], original_hash[:9]))
            os.remove(f.name)

    def download_part(self, part_id):
        request = self.api.export_media(part_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
        return fh.getvalue()

    # Upload a chunked part to drive and return the size of the chunk
    def upload_chunked_part(self, chunk, api=None):
        if not api:
            api = self.api
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
        file_hash = self.hash_file(path)

        encoded_size = size * (4/3)

        root = self.api.get_base_folder()['id']

        media = FileParts.UDSFile(ntpath.basename(path), None, MimeTypes().guess_type(urllib.request.pathname2url(path))[0],
                        Format.format(size), Format.format(encoded_size), parents=[root], size_numeric=size, sha256=file_hash)

        parent = self.api.create_media_folder(media)

        # Should be the same
        no_docs = math.ceil(encoded_size / MAX_DOC_LENGTH)

        # Append all chunks to chunk list
        chunk_list = list()
        for i in range(no_docs):
            chunk_list.append(
                FileParts.Chunk(path, i, size, media=media, parent=parent['id'])
            )

        total = 0
        total_chunks = len(chunk_list)
        progress_bar_chunks = tqdm(total=total_chunks,
                                   unit='chunks', dynamic_ncols=True, position=0)
        progress_bar_speed = tqdm(total=total_chunks * CHUNK_READ_LENGTH_BYTES, unit_scale=1,
                                  unit='B', dynamic_ncols=True, position=1)

        for chunk in chunk_list:
            total += 1
            self.upload_chunked_part(chunk)
            progress_bar_speed.update(CHUNK_READ_LENGTH_BYTES)
            progress_bar_chunks.update(1)
        """# Concurrently execute chunk upload and report back when done.
        with concurrent.futures.ProcessPoolExecutor(max_workers=MAX_WORKERS_ALLOWED) as executor:
            for file in executor.map(ext_upload_chunked_part, chunk_list):
                total = total + file
                elapsed_time = round(time.time() - start_time, 2)
                current_speed = round(
                    (total) / (elapsed_time * 1024 * 1024), 2)
                progress_bar("Uploading %s at %sMB/s" %
                             (media.name, current_speed), total, size)"""

        # Print new file output
        table = [[media.name, media.size, media.encoded_size, parent['id']]]
        print(" \r")
        print("\n" + tabulate(table, headers=[
            'Name', 'Size', 'Encoded', 'ID', ]))

    def convert_file(self, file_id):
        # Get file metadata
        metadata = service.files().get(fileId=file_id, fields="name").execute()

        # Download the file and then call do_upload() on it
        request = service.files().get_media(fileId=file_id)
        path = "%s/%s" % (get_downloads_folder(), metadata['name'])
        fh = io.FileIO(path, "wb")
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            _, done = downloader.next_chunk() 

        print("Downloaded %s" % metadata['name'])
        do_upload(path, service)

        # An alternative method would be to use partial download headers
        # and convert and upload the parts individually. Perhaps a
        # future release will implement this.
    # Mode sets the mode of updating 0 > Verbose, 1 > Notification, 2 > silent
    def update(self, mode=0, opts=None):
        items = self.api.list_files(opts)
        if not items:
            print('No UDS files found.')
        elif mode != 2:  # Duplicate silent...
            table = []
            with open("data.txt", 'w') as init:  # Create data.txt if it does not exist
                init.write("{")
                init.write("}")
            for item in items:  # Show online data in form Encoded >> Size to show drive size and on disk size in order
                record = [item.name, item.encoded_size, item.size, item.id_]
                with open("data.txt", 'r') as data3:  # Read data stored offline
                    user_data = json.load(data3)
                temp_name = str(item.name)
                user_data[temp_name] = item.id_
                with open("data.txt", 'w') as data4:  # Write data to data.txt
                    json.dump(user_data, data4, indent=3)
                table.append(record)
                with open("User.txt", 'w') as user:
                    user.write(tabulate(table, headers=[
                               'Name', 'Encoded', 'Size', 'ID']))
            if mode == 0:  # Verbose
                print(tabulate(table, headers=[
                      'Name', 'Encoded', 'Size', 'ID']))
            elif mode == 1:  # Notify
                print("Data Updated!\n")
            else:  # Silent Catch
                print("", end='')
        else:
            print("", end='')

    def list(self, opts=None):
        """List UDS files

        Prints a list of all UDS files. If a query is given, only the files
        that match that query will be printed.

        Args:
            opts (str): Command line arguments
        """
        items = self.api.list_files(opts)

        if not items:
            print('No UDS files found.')
        else:
            #print('\nUDS Files in Drive:')
            table = []
            for item in items:
                record = [item.name, item.size,
                          item.encoded_size, item.id_]
                table.append(record)

            print(tabulate(table, headers=[
                  'Name', 'Size', 'Encoded', 'ID', ]))

    # Alpha command to erase file via name
    def erase(self, name, default=1, mode_=None, fallback=None):
        if fallback is not None:
            self.delete_file(fallback, name=name, mode_=mode_)
        else:
            with open("data.txt", 'r') as list_:
                data_pull = json.load(list_)
                list_.close()
            id_ = data_pull[name]
            self.delete_file(id_, name=name, mode_=mode_)
        self.update(mode=default)  # Updates files in data after being altered

    def grab(self, name, default=1, fallback=None):  # Alpha command to pull files via name
        self.update(mode=default)  # Sets update mode
        if fallback is not None:
            self.build_file(parent_id=fallback)
            print("\n")
        else:
            with open("data.txt", 'r') as list_:  # Load ID values based on file name
                data_pull = json.load(list_)
            parent_id = data_pull[name]  # Loads ID based on name
            self.build_file(parent_id)
            print("\n")

    def batch(self, part, opts=None):  # Alpha command to bulk download based on part of a file name
        self.update(mode=1)  # Sets update mode
        items = self.api.list_files(opts)
        name_space = []  # List of names based on user part
        id_space = []
        check = 0
        for item in items:  # Checks if part is in the name of any UDS file and adds them to queue
            if str(part) is not "?":
                if str(part) in str(item.name):  # The name check
                    name_space.append(item.name)
                    id_space.append(item.id_)
                    check += 1
                else:
                    print("", end='')
            elif str(part) is "?":
                name_space.append(item.name)
                id_space.append(item.id_)
            else:  # Fallback for doing nothing, not necessary, just habit
                print("", end='')
        for i in range(check):
            self.grab(fallback=id_space[i], name=name_space[i], default=2)
        # Downloads the bulk using data and names
        for names in range(len(name_space)):
            # Update data, not necessary
            self.grab(name_space[names], default=2)

    # Alpha command to bulk upload files based on file name part
    def bunch(self, file_part, path='.'):
        files = os.listdir(path)  # Make list of all files in directory
        files_upload = []
        for name in files:  # Cycles through all files
            if file_part is not "?":
                if file_part in name:  # Checks if part is in any files and adds to list
                    files_upload.append(name)
                else:
                    print("", end='')
            elif file_part is "?":
                files_upload.append(name)
            else:  # Fallback
                print("", end='')
        for name_data in range(len(files_upload)):  # Upload all files put in list
            full_path = str(path) + "/" + str(files_upload[name_data])
            self.do_chunked_upload(full_path)
        print("\n")
        self.update(mode=1)  # Necessary update to data

    def wipe(self, part, opts=None):  # Alpha command to bulk delete files based on file name part
        self.update(mode=2)  # Sets update mode
        items = self.api.list_files(opts)
        name_space = []
        id_space = []
        check = 0
        for item in items:  # Add names to list
            if str(part) is not "?":
                if str(part) in str(item.name):  # add names if they have part in them
                    name_space.append(item.name)
                    check += 1
                    id_space.append(item.id_)
                else:
                    print("", end='')
            elif str(part) is "?":
                name_space.append(item.name)
                check += 1
                id_space.append(item.id_)
            else:
                print("")
        for i in range(check):
            self.erase(fallback=id_space[i], name=name_space[i], default=2)

    def hash_file(self, path):
        sha = hashlib.sha256()

        with open(path, 'rb') as f:
            while True:
                data = f.read(CHUNK_READ_LENGTH_BYTES)
                if not data:
                    break
                sha.update(data)

        return sha.hexdigest()

    def actions(self, action, args):
        switcher = {
            "list": self.list,
            "push": self.do_chunked_upload,
            "pull": self.build_file,
            "delete": self.delete_file
        }

        switcher.get(action)(args)


def get_downloads_folder():
    if not os.path.exists(DOWNLOADS_FOLDER):
        os.makedirs(DOWNLOADS_FOLDER)
    return DOWNLOADS_FOLDER


def characters_to_bytes(chars):
    return round((3/4) * chars)


def write_status(status):
    sys.stdout.write("\r%s" % status)
    sys.stdout.flush()


def main():
    global BASE_FOLDER, USE_MULTITHREADED_UPLOADS, DELETE_FILE_AFTER_CONVERT
    uds = UDS()

    # Initial look for folder and first time setup if not
    uds_root = uds.api.get_base_folder()
    BASE_FOLDER = uds_root

    # Options
    options = """
    push     Uploads a file from this computer [path_to_file]
    bunch    Uploads files from this computer [word_in_file] [path_to_file]
    pull     Downloads a UDS file [id]
    batch    Downloads UDS files [word_in_file]
    grab     Downloads a UDS file [name]
    list     Finds all UDS files [query]
    update   Update cached UDS data
    delete   Deletes a UDS file [id]
    erase    Deletes a UDS file [name]
    wipe     Deletes UDS files [word_in_file]
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
        elif command == "bunch":
            if sys.argv[2] == "--disable-multi":
                USE_MULTITHREADED_UPLOADS = False
                if len(sys.argv) > 3:
                    path = str(sys.argv[4])
                    uds.bunch(sys.argv[3], path=path)
                else:
                    uds.bunch(sys.argv[3])
            else:
                if len(sys.argv) > 3:
                    path = str(sys.argv[3])
                    uds.bunch(sys.argv[2], path=path)
                else:
                    uds.bunch(sys.argv[2])
        elif command == "pull":
            uds.build_file(sys.argv[2])
        elif command == "grab":
            uds.grab(sys.argv[2])
        elif command == "batch":
            uds.batch(sys.argv[2])
        elif command == "list":
            arg = sys.argv[2] if len(sys.argv) > 2 else None
            uds.list(arg)
        elif command == "update":
            uds.update()
        elif command == "delete":
            uds.delete_file(sys.argv[2])
        elif command == "erase":
            uds.erase(sys.argv[2])
        elif command == "wipe":
            uds.wipe(sys.argv[2])
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


# Upload a chunked part to drive and return the size of the chunk


def ext_upload_chunked_part(chunk):
    api = GoogleAPI()
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

    api.upload_single_file(mediaio_file, file_metadata)

    return len(chunk_bytes)


if __name__ == '__main__':
    if (sys.version_info[0] < 3):
        print("%s You must use Python 3+" % GoogleAPI.ERROR_OUTPUT)
    else:
        main()

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
import concurrent.futures
from classes import *
import byte_format

DOWNLOADS_FOLDER = "downloads"
TEMP_FOLDER = "tmp"

ERROR_OUTPUT = "[ERROR]"

USE_MULTITHREADED_UPLOADS = True

MAX_DOC_LENGTH = 1000000
MAX_RAM_MB = 1024
MAX_WORKERS_ALLOWED = 10
CHUNK_READ_LENGTH_BYTES = 750000

def get_downloads_folder():
    if not os.path.exists(DOWNLOADS_FOLDER):
            os.makedirs(DOWNLOADS_FOLDER)
    return DOWNLOADS_FOLDER

def get_base_folder(service):
    # Look for existing folder
    results = service.files().list(
        q="properties has {key='udsRoot' and value='true'} and trashed=false",
        pageSize=1, 
        fields="nextPageToken, files(id, name, properties)").execute()
    folders = results.get('files', [])
    
    if len(folders) == 0:
        return create_root_folder("UDS Root", service, {'udsRoot':'true'})
    elif len(folders) == 1:
        return folders[0]
    else:
        print("%s Multiple UDS Roots found." % ERROR_OUTPUT)

def characters_to_bytes(chars):
    return round((3/4) * chars)

def progress_bar(title, value, endvalue, bar_length=30):
        percent = float(value) / endvalue
        arrow = '█' * int(round(percent * bar_length))
        spaces = ' ' * (bar_length - len(arrow))

        sys.stdout.write("\r"+title+": [{0}] {1}%".format(arrow + spaces, int(round(percent * 100))))
        sys.stdout.flush()

def write_status(status):
    sys.stdout.write("\r%s" % status)
    sys.stdout.flush()

def get_service():
    SCOPES = 'https://www.googleapis.com/auth/drive'
    store = file.Storage('credentials.json')
    creds = store.get()
    if not creds or creds.invalid:
        flow = client.flow_from_clientsecrets('client_secret.json', SCOPES)
        creds = tools.run_flow(flow, store)
    return build('drive', 'v3', http=creds.authorize(Http()))

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
        print( 'An error occurred: %s' % error)
    return None

def create_folder(media, service):

    file_metadata = {
        'name': media.name,
        'mimeType': 'application/vnd.google-apps.folder',
        'properties': {
            'uds': 'true',
            'size': media.size,
            'encoded_size': media.encoded_size
        },
        'parents': media.parents
    }

    file = service.files().create(body=file_metadata,
                                        fields='id').execute()

    return file

def create_root_folder(name, service, properties={}):
    file_metadata = {
        'name': name,
        'mimeType': 'application/vnd.google-apps.folder',
        'properties': properties,
        'parents': []
    }

    root_folder = service.files().create(body=file_metadata,
                                        fields='id').execute()

    # Hide this folder
    service.files().update(fileId=root_folder['id'],
                                    removeParents='root').execute()

    return root_folder

def upload_file_to_drive(media_file, file_metadata, service=None):
    if service == None:
        service = get_service()
    file = service.files().create(body=file_metadata, 
                                    media_body=media_file,
                                    fields='id').execute()
    
    return file, file_metadata

def encode(chunk):
    enc = base64.b64encode(chunk).decode()
    return enc

def decode(chunk):
    missing_padding = len(chunk) % 4
    if missing_padding != 0:
        chunk += b'='* (4 - missing_padding)
    return base64.decodestring(chunk)

def upload_chunked_part(chunk):
    #print("Chunk %s, bytes %s to %s" % (chunk.part, chunk.range_start, chunk.range_end))

    with open(chunk.path, "r") as fd:
        mm = mmap.mmap(fd.fileno(), 0, access=mmap.ACCESS_READ)
        chunk_bytes = mm[chunk.range_start:chunk.range_end]

    encoded_chunk = encode(chunk_bytes)

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

    upload_file_to_drive(mediaio_file, file_metadata)

    return len(chunk_bytes)


def do_chunked_upload(path, service):
    # Prepare media file
    size = os.stat(path).st_size 
    encoded_size = size * (4/3)

    root = [get_base_folder(service)['id']]

    media = UDSFile(ntpath.basename(path), None, MimeTypes().guess_type(urllib.request.pathname2url(path))[0],
                    byte_format.format(size), byte_format.format(encoded_size), parents=root)

    parent = create_folder(media, service)
    print("Created parent folder with ID %s" % (parent['id']))

    # Should be the same
    no_chunks = math.ceil(size / CHUNK_READ_LENGTH_BYTES)
    no_docs = math.ceil(encoded_size / MAX_DOC_LENGTH)
    print("Requires %s chunks to read and %s docs to store." % (no_chunks, no_docs))

    chunk_list = list()
    for i in range(no_docs):
        chunk_list.append(Chunk(path, i, size, media=media, parent=parent['id']))

    start_time = time.time()

    total = 0
    with concurrent.futures.ProcessPoolExecutor(max_workers=MAX_WORKERS_ALLOWED) as executor:
            for file in executor.map(upload_chunked_part, chunk_list):
                total = total + file
                progress_bar("Uploading %s" % media.name, total, size)   

    finish_time = round(time.time() - start_time, 1)

    progress_bar("Uploaded %s in %ss" % (media.name, finish_time), total, size)  

def build_file(parent_id,service):
    # This will fetch the Docs one by one, concatting them 
    # to a local base64 file. The file will then be converted 
    # from base64 to the appropriate mimetype
    files = service.files().list(
        q="parents in '%s'" % parent_id,
        pageSize=100, 
        fields="nextPageToken, files(id, name, properties)").execute()
    
    folder = service.files().get(fileId=parent_id).execute()

    items = files.get('files', [])
    
     
    if not items:
        print('No parts found.')
    else:
        # Fix part as int
        for item in items:
            item['properties']['part'] = int(item['properties']['part'])
   
        #print('Parts of %s:' % folder['name'])
        items.sort(key=lambda x: x['properties']['part'], reverse=False)

        f = open("%s/%s" % (get_downloads_folder(),folder['name']),"wb")

        for i,item in enumerate(items):
            #print('%s (%s)' % (item['properties']['part'], item['id']))
            progress_bar("Downloading %s" % folder['name'],i,len(items))

            encoded_part = download_part(item['id'], service)
            
            # Decode
            decoded_part = decode(encoded_part)

            # Append decoded part to file
            f.write(decoded_part)
        
        f.close()  

        progress_bar("Downloaded %s" % folder['name'],1,1)     
          
            
def download_part(part_id, service):
    request = service.files().export_media(fileId=part_id, mimeType='text/plain')
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()
    return fh.getvalue()

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

def list_files(service):
    # Call the Drive v3 API
    results = service.files().list(
        q="properties has {key='uds' and value='true'} and trashed=false",
        pageSize=1000, 
        fields="nextPageToken, files(id, name, properties)").execute()
    items = results.get('files', [])
    if not items:
        print('No UDS files found.')
    else:
        #print('\nUDS Files in Drive:')
        table = []
        for item in items:
            #print('{0} ({1}) | {2}'.format(item['name'], item['id'],item['properties']['size']))
            record = [item.get("name"), item.get("properties").get('size'), item.get('properties').get('encoded_size'), item.get('id'),item.get('properties').get('shared')]
            table.append(record)


        print(tabulate(table, headers=['Name', 'Size', 'Encoded', 'ID', 'Shared']))

def main():
    # Setup the Drive v3 API
    SCOPES = ['https://www.googleapis.com/auth/drive']
    store = file.Storage('credentials.json')
    creds = store.get()
    if not creds or creds.invalid:
        flow = client.flow_from_clientsecrets('client_secret.json', SCOPES)
        creds = tools.run_flow(flow, store)
    service = build('drive', 'v3', http=creds.authorize(Http()))

    # Initial look for folder and first time setup if not
    uds_root = get_base_folder(service)
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
            do_chunked_upload(file_path, service)
        elif command == "pull":
            build_file(sys.argv[2], service)
        elif command == "list":
            list_files(service)
        elif command == "convert":
            if sys.argv[2] == "--delete":
                DELETE_FILE_AFTER_CONVERT = True
                id = sys.argv[3]
            else:
                id = sys.argv[2]
            convert_file(id, service)
        else:
            print(options)
    else:
        print(options)


if __name__ == '__main__':
    main()
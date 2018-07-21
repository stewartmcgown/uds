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
import io
import os
import time
import shutil
import concurrent.futures

DOWNLOADS_FOLDER = "downloads"
TEMP_FOLDER = "tmp"

ERROR_OUTPUT = "[ERROR]"

class UDSFile(object):
    base64 = ""
    mime = ""
    name = ""
    size = 0
    encoded_size = 0

def byte_format(bytes):
    if bytes < 0:
        raise ValueError("!!! number_of_bytes can't be smaller than 0 !!!")

    step = 1024.

    bytes = float(bytes)
    unit = 'bytes'

    if (bytes / step) >= 1:
        bytes /= step
        unit = 'KB'

    if (bytes / step) >= 1:
        bytes /= step
        unit = 'MB'

    if (bytes / step) >= 1:
        bytes /= step
        unit = 'GB'

    if (bytes / step) >= 1:
        bytes /= step
        unit = 'TB'

    precision = 1
    bytes = round(bytes, precision)

    return str(bytes) + ' ' + unit

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


def progressBar(title, value, endvalue, bar_length=30):
        percent = float(value) / endvalue
        arrow = '█' * int(round(percent * bar_length))
        spaces = ' ' * (bar_length - len(arrow))

        sys.stdout.write("\r"+title+": [{0}] {1}%".format(arrow + spaces, int(round(percent * 100))))
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

    return file

def do_upload(path, service):
    media = UDSFile()

    with open(path, "rb") as f:
        
        data = f.read()
        enc = base64.b64encode(data).decode()

        media.size = byte_format(sys.getsizeof(data))
        media.encoded_size = byte_format(sys.getsizeof(enc))

        media.parents = [get_base_folder(service)['id']]

        enc = enc.replace("b'","")
        enc = enc.replace("'","")

        mime = MimeTypes()
        url = urllib.request.pathname2url(path) 
        mime_type = mime.guess_type(url)[0]

        media.base64 = enc
        media.mime = mime_type
        media.name = ntpath.basename(path)

    MAX_LENGTH = 1000000

    length = len(media.base64)
    no_docs = math.ceil(length / MAX_LENGTH)

    print("%s requires %s Docs to store." % (media.name, no_docs))

    # Creat folder ID
    parent = create_folder(media, service)
    print("Created parent folder with ID %s" % (parent['id']))

    parent_id = parent['id']
    
    """with concurrent.futures.ProcessPoolExecutor(max_workers=8) as executor:
        for file,part in executor.map(upload_file_to_drive, media_file_list, file_metadata_list):
            #progressBar("Uploading %s" % media.name,count,no_docs)
            #count += 1
            # This will order things correctly
            print(file['id']) """

    for i in range(no_docs):
        progressBar("Uploading %s" % media.name,i,no_docs)

        current_substr = media.base64[i * MAX_LENGTH:(i+1) * MAX_LENGTH]

        file_metadata = {
            'name': media.name + str(i),
            'mimeType': 'application/vnd.google-apps.document',
            'parents': [parent_id],
            'properties': {
                'part': str(i)
            }
        }

        media_file = MediaIoBaseUpload(io.StringIO(current_substr),
                        mimetype='text/plain')

        file = service.files().create(body=file_metadata, 
                                    media_body=media_file,
                                    fields='id').execute()    
        
    progressBar("Successfully Uploaded %s" % media.name,no_docs,no_docs)

    

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

        encoded_parts = ""

        for i,item in enumerate(items):
            #print('%s (%s)' % (item['properties']['part'], item['id']))
            progressBar("Downloading %s" % folder['name'],i,len(items))

            encoded_part = reassemble_part(item['id'], service)
            encoded_parts = encoded_parts + encoded_part
        
        progressBar("Downloaded %s" % folder['name'],1,1)

        # Change string so it works with base64decode (legacy at this point)
        encoded_parts = encoded_parts.replace("b\"\\xef\\xbb\\xbfb'","")
        encoded_parts = encoded_parts.replace("b'\\xef\\xbb\\xbf","")
        encoded_parts = encoded_parts.replace("'\"","")
        encoded_parts = encoded_parts.replace("'","")
        
        

        t = open("%s/%s.download" % (get_downloads_folder(),folder['name']),"w+")
        t.write(encoded_parts)
        t.close()

        decoded_part = base64.b64decode(encoded_parts)

        f = open("%s/%s" % (get_downloads_folder(),folder['name']),"wb")
        f.write(decoded_part)
        f.close()  

        # Tidy up temp files
        try:
             os.remove("%s/%s.download" % (get_downloads_folder(),folder['name']))   
        except OSError as e: 
            print ("Failed with: %s" % e.strerror)
            print ("Error code: %s" % e.code)
          
            

def reassemble_part(part_id, service):
    request = service.files().export_media(fileId=part_id, mimeType='text/plain')
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()
    return str(fh.getvalue())

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
        pageSize=10, 
        fields="nextPageToken, files(id, name, properties)").execute()
    items = results.get('files', [])
    if not items:
        print('No UDS files found.')
    else:
        #print('\nUDS Files in Drive:')
        table = []
        for item in items:
            #print('{0} ({1}) | {2}'.format(item['name'], item['id'],item['properties']['size']))
            record = [item['name'], item['properties']['size'], item['properties']['encoded_size'], item['id']]
            table.append(record)


        print(tabulate(table, headers=['Name', 'Size', 'Encoded', 'ID']))

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
            do_upload(sys.argv[2], service)
        elif command == "pull":
            build_file(sys.argv[2], service)
        elif command == "list":
            list_files(service)
        elif command == "convert":
            convert_file(sys.argv[2], service)
        else:
            print(options)
    else:
        print(options)


if __name__ == '__main__':
    main()
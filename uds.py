from __future__ import print_function
from apiclient.discovery import build
from apiclient.http import MediaFileUpload
from apiclient.http import MediaIoBaseDownload
from httplib2 import Http
from oauth2client import file, client, tools
from mimetypes import MimeTypes
import sys
import base64
import math
import urllib.request
import ntpath
import io

class UDSFile(object):
    base64 = ""
    mime = ""
    name = ""

def progressBar(title, value, endvalue, bar_length=30):
        percent = float(value) / endvalue
        arrow = '█' * int(round(percent * bar_length))
        spaces = ' ' * (bar_length - len(arrow))

        sys.stdout.write("\r"+title+": [{0}] {1}%".format(arrow + spaces, int(round(percent * 100))))
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
        print( 'An error occurred: %s' % error)
    return None

def create_folder(name, service):
    file_metadata = {
        'name': name,
        'mimeType': 'application/vnd.google-apps.folder',
        'properties': {
            'uds': 'true',
        }
    }
    file = service.files().create(body=file_metadata,
                                        fields='id').execute()

    return file


def do_upload(path, service):
    media = UDSFile()

    with open(path, "rb") as f:
        data = f.read()
        enc = base64.b64encode(data).decode()

        mime = MimeTypes()
        url = urllib.request.pathname2url(path) 
        mime_type = mime.guess_type(url)[0]

        media.base64 = enc
        media.mime = mime_type
        media.name = ntpath.basename(path)

    MAX_LENGTH = 1000000

    length = len(media.base64)
    no_docs = math.ceil(length / MAX_LENGTH)

    print("%s will required %s Docs to store." % (media.name, no_docs))

    # Creat folder ID
    parent = create_folder(media.name, service)
    print("Created parent folder with ID %s" % (parent['id']))

    parent_id = parent['id']

    for i in range(no_docs):
        progressBar("Uploading %s" % media.name,i,no_docs)

        current_substr = media.base64[i * MAX_LENGTH:(i+1) * MAX_LENGTH]

        # Create the temp file
        f = open(".uds","w+")
        f.write(current_substr)
        f.close()
        
        file_metadata = {
            'name': media.name + str(i),
            'mimeType': 'application/vnd.google-apps.document',
            'parents': [parent_id],
            'properties': {
                'part': str(i)
            }
        }

        media_file = MediaFileUpload('.uds',
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
   
        print('Parts of %s:' % folder['name'])
        items.sort(key=lambda x: x['properties']['part'], reverse=False)

        encoded_parts = ""

        for i,item in enumerate(items):
            print('%s (%s)' % (item['properties']['part'], item['id']))
            encoded_part = reassemble_part(item['id'], service)
            encoded_parts = encoded_parts + encoded_part
            
        encoded_parts = encoded_parts.replace("b\"\\xef\\xbb\\xbfb'","")
        encoded_parts = encoded_parts.replace("'\"","")

        print(encoded_parts)

        decoded_part = base64.b64decode(encoded_parts)

        f = open("%s" % folder['name'],"wb")
        f.write(decoded_part)
        f.close()        
            

def reassemble_part(part_id, service):
    request = service.files().export_media(fileId=part_id, mimeType='text/plain')
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()
    return str(fh.getvalue())

def list_files(service):
    # Call the Drive v3 API
    results = service.files().list(
        q="properties has {key='uds' and value='true'} and trashed=false",
        pageSize=10, 
        fields="nextPageToken, files(id, name)").execute()
    items = results.get('files', [])
    if not items:
        print('No files found.')
    else:
        print('\nUDS Files in Drive:')
        for item in items:
            print('{0} ({1})'.format(item['name'], item['id']))


# Setup the Drive v3 API
SCOPES = 'https://www.googleapis.com/auth/drive'
store = file.Storage('credentials.json')
creds = store.get()
if not creds or creds.invalid:
    flow = client.flow_from_clientsecrets('client_secret.json', SCOPES)
    creds = tools.run_flow(flow, store)
service = build('drive', 'v3', http=creds.authorize(Http()))

# Do encode fomr path
command = str(sys.argv[1])
if command == "push":
    do_upload(sys.argv[2], service)
elif command == "pull":
    build_file(sys.argv[2], service)
elif command == "list":
    list_files(service)



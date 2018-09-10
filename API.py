from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.http import MediaIoBaseUpload
from googleapiclient.http import MediaIoBaseDownload
from httplib2 import Http
from oauth2client import file, client, tools
from mimetypes import MimeTypes
from tabulate import tabulate

from classes import UDSFile

class GoogleAPI():
    def __init__(self):
        # Setup the Drive v3 API
        SCOPES = ['https://www.googleapis.com/auth/drive']
        store = file.Storage('credentials.json')
        creds = store.get()
        if not creds or creds.invalid:
            flow = client.flow_from_clientsecrets(
                'client_secret.json', SCOPES)
            creds = tools.run_flow(flow, store)

        self.service = build('drive', 'v3', http=creds.authorize(Http()))

    def list_files(self):
        # Call the Drive v3 API
        results = self.service.files().list(
            q="properties has {key='uds' and value='true'} and trashed=false",
            pageSize=1000,
            fields="nextPageToken, files(id, name, properties, mimeType)").execute()

        items = results.get('files', [])

        files = []

        for f in items:
            props = f.get("properties")
            files.append(UDSFile(
                name = f.get("name"),
                base64=None,
                mime = f.get("mimeType"),
                size = f.get("size"),
                size_numeric = props.get("size_numeric"),
                encoded_size = props.get("encoded_size"),
                id_ = f.get("id"),
                shared = props.get("shared")
            ))

        return files

        
    def print_list_files(self):
        items = self.list_files()

        if not items:
            print('No UDS files found.')
        else:
            #print('\nUDS Files in Drive:')
            total = 0
            table = []
            saved_bytes = 0
            for item in items:
                record = [item.name, item.size, item.encoded_size, item.id_, item.shared]
                table.append(record)

            print(tabulate(table, headers=[
                  'Name', 'Size', 'Encoded', 'ID', 'Shared']))



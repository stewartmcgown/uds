from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.http import MediaIoBaseUpload
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.errors import HttpError
from httplib2 import Http
from oauth2client import file, client, tools
from mimetypes import MimeTypes
from tabulate import tabulate
from urllib.error import HTTPError

import time
import io

from FileParts import UDSFile


class FileNotFoundException(Exception):
    pass


class FileNotUDSException(Exception):
    pass


class GoogleAPI():
    ERROR_OUTPUT = "[ERROR]"
    CLIENT_SECRET = 'client_secret.json'

    def __init__(self):
        self.reauth()

    def reauth(self):
        # Set up the Drive v3 API
        SCOPES = ['https://www.googleapis.com/auth/drive']
        store = file.Storage('credentials.json')
        creds = store.get()
        if not creds or creds.invalid:
            try:
                flow = client.flow_from_clientsecrets(
                    GoogleAPI.CLIENT_SECRET, SCOPES)
                creds = tools.run_flow(flow, store)
            except:
                print("%s Make sure you've saved your OAuth credentials as %s" % (
                    GoogleAPI.ERROR_OUTPUT, GoogleAPI.CLIENT_SECRET))
                print(
                    "If you've already done that, then run uds.py without any arguments first.")
                exit()

        self.service = build('drive', 'v3', http=creds.authorize(Http()))
        return self.service

    def get_base_folder(self):
        # Look for existing folder
        results = self.service.files().list(
            q="properties has {key='udsRoot' and value='true'} and trashed=false",
            pageSize=1,
            fields="nextPageToken, files(id, name, properties)").execute()
        folders = results.get('files', [])

        if len(folders) == 0:
            return self.create_root_folder()
        elif len(folders) == 1:
            return folders[0]
        else:
            print("%s Multiple UDS Roots found." % GoogleAPI.ERROR_OUTPUT)

    # Creates the base UDS folder and hides it from the user's drive
    def create_root_folder(self):
        root_meta = {
            'name': "UDS Root",
            'mimeType': 'application/vnd.google-apps.folder',
            'properties': {'udsRoot': 'true'},
            'parents': []
        }

        root_folder = self.service.files().create(body=root_meta,
                                                  fields='id').execute()

        # Hide this folder
        self.service.files().update(fileId=root_folder['id'],
                                    removeParents='root').execute()

        return root_folder

    def create_media_folder(self, media):
        file_metadata = {
            'name': media.name,
            'mimeType': 'application/vnd.google-apps.folder',
            'properties': {
                'uds': 'true',
                'size': media.size,
                'size_numeric': media.size_numeric,
                'encoded_size': media.encoded_size
            },
            'parents': media.parents
        }

        file = self.service.files().create(body=file_metadata,
                                           fields='id').execute()

        return file

    def list_files(self, opts=None):
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
                name=f.get("name"),
                base64=None,
                mime=f.get("mimeType"),
                size=props.get("size"),
                size_numeric=props.get("size_numeric"),
                encoded_size=props.get("encoded_size"),
                id=f.get("id"),
                shared=props.get("shared")
            ))

        return files

    def recursive_list_folder(self, parent_id, token=None):
        all_parts = []

        while True:
            page_of_files = self.service.files().list(
                q="parents in '%s'" % parent_id,
                pageSize=100,
                pageToken=token,
                fields="nextPageToken, files(id, name, properties)").execute()

            all_parts = all_parts + (page_of_files.get("files", []))

            token = page_of_files.get("nextPageToken")

            if token == None:
                break

        return all_parts

    def delete_file(self, id):
        # Ensure the file is a UDS one
        try:
            info = self.service.files().get(fileId=id, fields="*").execute()

            if info.get("properties").get("uds"):
                return self.service.files().delete(fileId=id).execute()
            else:
                raise FileNotUDSException()
        except:
            raise FileNotFoundException()

    def get_file(self, id):
        return self.service.files().get(fileId=id).execute()

    def export_media(self, id):
        return self.service.files().export_media(fileId=id, mimeType='text/plain')

    def test_upload(self):
        file_metadata = {
            'name': "TestUDS",
            'mimeType': 'text/plain',
        }

        mediaio_file = MediaIoBaseUpload(io.StringIO("hello"),
                                         mimetype='text/plain')

        self.service.files().create(body=file_metadata, media_body=mediaio_file).execute()

    def upload_single_file(self, media_file, file_metadata):
        while True:
            try:
                file = self.service.files().create(body=file_metadata,
                                                   media_body=media_file,
                                                   fields='id').execute()
                break
            except HttpError as e:
                print(e._get_reason())
                print("Failed to upload chunk %s. Retrying... " %
                      file_metadata.get("properties").get("part"))
                time.sleep(1)
                continue

        return file, file_metadata

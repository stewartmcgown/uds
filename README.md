# UDS : Unlimited Drive Storage

UDS is a tool to split files into base64 parts small enough to fit inside a Google Doc. Compatible with Python 3+.

### Features
  - Store and list files in UDS format
  - Reassemble files to their original format

### Logic
  - Size of the encoded file is always larger than the original. Base64 encodes binary data to a ratio of about 4:3. 
  - A single google doc can store about a million characters. This is around 710KB of base64 encoded data.
  - Some experiments with multithreading the uploads, but there was no significant performance increase. 

### Authentication
  1. Head to [Google's API page](https://developers.google.com/drive/api/v3/quickstart/python) and enable the Drive API
  2. Download the configuration file as 'client_secret.json' to the UDS directory

#### Upload
```sh
> python uds.py push Ubuntu.Desktop.16.04.iso
Ubuntu.Desktop.16.04.iso will required 543 Docs to store.
Created parent folder with ID 1fc6JGpX6vUWiwflL1jBxM1YpuMHFAms8
Successfully Uploaded Ubuntu.Desktop.16.04.iso: [██████████████████████████████] 100%
```
#### List
```sh
> python uds.py list
Name                      Size   Encoded    ID
------------------------  -----  ---------  ---------------------------------
Ubuntu.Desktop.16.04.iso  810 MB  1.1 GB     1fc6JGpX6vUWiwflL1jBxM1YpuMHFAms8
```

#### Download
```sh
> python uds.py pull 
Downloaded Ubuntu.Desktop.16.04.iso: [██████████████████████████████] 100%
```
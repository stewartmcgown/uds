# :milky_way: UDS : Unlimited Drive Storage

Store files in Google Docs without counting against your quota.

sorry @ the guys from google internal forums who are looking at this

### Features

- Upload files to Google Drive without using storage space
- Download any stored files to your computer

### Logic

- Size of the encoded file is always larger than the original. Base64 encodes binary data to a ratio of about 4:3.
- A single google doc can store about a million characters. This is around 710KB of base64 encoded data.
- Some experiments with multithreading the uploads, but there was no significant performance increase.

### Authentication

1. Head to [Google's API page](https://developers.google.com/drive/api/v3/quickstart/python) and enable the Drive API
2. Download the configuration file as 'client_secret.json' to the UDS directory
3. run `python uds.py` for initial set up

### Upload

```sh
> python uds.py push Ubuntu.Desktop.16.04.iso
Ubuntu.Desktop.16.04.iso will required 543 Docs to store.
Created parent folder with ID 1fc6JGpX6vUWiwflL1jBxM1YpuMHFAms8
Successfully Uploaded Ubuntu.Desktop.16.04.iso: [██████████████████████████████] 100%
```

### List

```sh
> python uds.py list
Name                      Size   Encoded    ID
------------------------  -----  ---------  ---------------------------------
Ubuntu.Desktop.16.04.iso  810 MB  1.1 GB     1fc6JGpX6vUWiwflL1jBxM1YpuMHFAms8
```

### Update

```sh
> python uds.py update

Name       Encoded   Size 
---------  --------  -----
file_name  1.1 GB    810 MB 

"data.txt"
{
   "file0": "1fc6JGpX6vUWiwflL1jBxM1YpuMHFAms8"
   "file2": "1fc6JGpX6vUWiwflL1jBxM1YpuMHFAms9"
}
```

### Download

```sh
> python uds.py pull
Downloaded Ubuntu.Desktop.16.04.iso: [██████████████████████████████] 100%
```

### Grab

```sh
> python uds.py grab file_name
Update Successful!
Downloaded file_name: [██████████████████████████████] 100%
```

### Delete

```sh
> python uds.py delete 1fc6JGpX6vUWiwflL1jBxM1YpuMHFAms8
Deleted 1fc6JGpX6vUWiwflL1jBxM1YpuMHFAms8
```

### Erase

```sh
>python uds.py erase file_name
Update Successful!
Deleted file_name
```

**Compatible with Python 3.**

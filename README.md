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

## UDS Core

### Upload

```sh
> python uds.py push Ubuntu.Desktop.16.04.iso
Ubuntu.Desktop.16.04.iso will required 543 Docs to store.
Created parent folder with ID 1fc6JGpX6vUWiwflL1jBxM1YpuMHFAms8
Successfully Uploaded Ubuntu.Desktop.16.04.iso: [██████████████████████████████] 100%
```

```
[Layout]
python uds.py push argument

argument: Path_to_file+file_name
```

### List

```sh
> python uds.py list
Name                      Size   Encoded    ID
------------------------  -----  ---------  ---------------------------------  
Ubuntu.Desktop.16.04.iso  810 MB  1.1 GB    1fc6JGpX6vUWiwflL1jBxM1YpuMHFAms8
Ubuntu.Desktop.18.10.iso  1.1 GB  1.3 GB    1RzzVfN9goHMTkM1Hf1FUWUVS_2R3GK7D

Also supports searching with a query!

> python uds.py list "18"
Name                      Size   Encoded    ID
------------------------  -----  ---------  ---------------------------------  
Ubuntu.Desktop.18.10.iso  1.1 GB  1.3 GB    1RzzVfN9goHMTkM1Hf1FUWUVS_2R3GK7D
```

```
[Layout]
python uds.py list

arguments: query
```

### Download

```sh
> python uds.py pull 1fc6JGpX6vUWiwflL1jBxM1YpuMHFAms8
Downloaded Ubuntu.Desktop.16.04.iso: [██████████████████████████████] 100%
```

```
[Layout]
python uds.py pull argument

argument: id_of_file
```

### Delete

```sh
> python uds.py delete 1fc6JGpX6vUWiwflL1jBxM1YpuMHFAms8
Deleted 1fc6JGpX6vUWiwflL1jBxM1YpuMHFAms8
```

```
[Layout]
python uds.py delete argument

argument: id_of_file
```
## Alpha Extensions


### Grab

```sh
> python uds.py grab test.7z
Update Successful!
Downloaded test.7z: [██████████████████████████████] 100%
```

```
[Layout]
python uds.py grab argument

argument: name_of_file
```

### Erase

```sh
>python uds.py erase test2.7z
Update Successful!
Deleted test2.7z
```

```
[Layout]
python uds.py erase argument

argument: name_of_file
```

### Update

```sh
> python uds.py update

Name       Encoded   Size 
---------  --------  -----
file_name  1.1 GB    810 MB 

"User.txt"
Name       Encoded   Size 
---------  --------  -----
file_name  1.1 GB    810 MB 

"data.txt"
{
   "file0": "1fc6JGpX6vUWiwflL1jBxM1YpuMHFAms8"
   "file2": "1fc6JGpX6vUWiwflL1jBxM1YpuMHFAms9"
}
```

```
[Layout]
python uds.py update

arguments: None
```

## Bulk Extensions

### Bunch

```sh
> python uds.py bunch test
test.7z.1 will require 1337 Docs to store.
Created parent folder with ID 1fc6JGpX6vUWiwflL1jBxM1YpuMHFAm12
Successfully Uploaded test.7z.1: [██████████████████████████████] 100%
test.7z.2 will require 1337 Docs to store.
Created parent folder with ID 1fc6JGpX6vUWiwflL1jBxM1YpuQQFAm12
Successfully Uploaded test.7z.2: [██████████████████████████████] 100%
test.7z.3 will require 600 Docs to store.
Created parent folder with ID 1fc6JGpX6vTOiwflL1jBxM1YpuQQFAm12
Successfully Uploaded test.7z.3: [██████████████████████████████] 100%
```

```
[Layout]
python uds.py bunch argument[1] argument[2]

argument[1]: name_in_files, or wildcard "?" without quotes
argument[2]: directory, defualt is current directory of UDS
```


### Batch

```sh
> python uds.py batch file_name
Update Successful!
Downloaded file_name.7z.1: [██████████████████████████████] 100%
Downloaded file_name.7z.2: [██████████████████████████████] 100%
Downloaded file_name.7z.3: [██████████████████████████████] 100%
```

```
[Layout]
python uds.py batch argument

arguments: name_in_files, or wildcard "?" without quotes
```

### Wipe

```sh
>python uds.py wipe file
Update Successful!
Deleted file.7z.1
Deleted file.7z.2
Deleted file.7z.3
```

```
[Layout]
python uds.py wipe argument

arguments: name_in_files, or wildcard "?" without quotes
```


**Compatible with Python 3.**

# ABCD

*Build info* [![Build Status](https://travis-ci.org/libAtoms/abcd.svg?branch=master)](https://travis-ci.org/libAtoms/abcd)

*Docs* [![Documentation Status](https://readthedocs.org/projects/abcd/badge/?version=latest)](http://abcd.readthedocs.org/en/latest/?badge=latest)


**ABCD** is the **A**tom-**B**ased **C**onfiguration **D**atabase. Designed to
store atomistic data with an interface that makes it easy to work with 
and share your data.
 
```shell
% abcd tungsten --store *.xyz
35 configurations were inserted:
  42049fa6f48a2e1
  ebce002d9192f15
  6cf54ac7b5a6be2
  7b757bbe194668c
  849d45805f494c0
  ...

% abcd tungsten.db --show --limit 5

+---------------+-------------+-------+-------+-------+-----------+---+----------+----------+----------+----------+
|      uid      |    c_time   |formula|n_atoms|numbers|config_type|pbc|positions |   cell   |  energy  |  virial  |
+---------------+-------------+-------+-------+-------+-----------+---+----------+----------+----------+----------+
|42049fa6f48a2e1|23Mar16 17:02|   W   |   1   |  [74] | slice_sa..|TTT|[[0.0, 0..|[[3.1686..|-11.1598..|[[0.1510..|
|ebce002d9192f15|23Mar16 17:02|   W   |   1   |  [74] | slice_sa..|TTT|[[0.0, 0..|[[2.7685..|-11.0424..|[[1.4659..|
|6cf54ac7b5a6be2|23Mar16 17:02|   W   |   1   |  [74] | slice_sa..|TTT|[[0.0, 0..|[[2.7688..|-11.0080..|[[-0.611..|
|7b757bbe194668c|23Mar16 17:02|   W   |   1   |  [74] | slice_sa..|TTT|[[0.0, 0..|[[3.2516..|-11.1097..|[[-0.503..|
|849d45805f494c0|23Mar16 17:02|   W   |   1   |  [74] | slice_sa..|TTT|[[0.0, 0..|[[2.9675..|-11.0596..|[[3.5954..|
+---------------+-------------+-------+-------+-------+-----------+---+----------+----------+----------+----------+
  Rows: 5

% abcd tungsten.db 'energy<-11.1' 'config_type=slice_sample' --write-to-file out_%i.xyz
  Writing 12 file(s) to ./
```

ABCD works with several database backends (ase, mongodb) and can be extended 
to any others using a simple specification.

To use ABCD, two main steps have to be performed:

- *abcd* installation
- backend installation

## ABCD installation

- Download and manually install the development version of ASE from *https://wiki.fysik.dtu.dk/ase/download.html#latest-development-release* (min. version required 3.10.0.4590)
- Change the directory to *abcd/* and run ```python setup.py install --user``` to install the abcd package. It will install the *abcd* tool on your system.
- Specify the backend to be used under *~/.abcd_config*. The script will try to import the module by calling ```from <backend_module> import <backend_name>```.

## Backend installation
This will vary depending on the backend. For example, these are the steps required to install the ASEdb backend:

### ASEdb backend

(Note: If you will want to allow access to your databases to the outside world, create a new UNIX user (say, abcd) and install both the *abcd* and the ASEdb backend on this user.)

- Run the setup script (it will install two commands: *abcd-asedb* and *abcd-asedb-server*):

> cd backends/asedb_sqlite3  
> python setup.py install --user

- Open *~/.abcd_config* and complete it in the following way:

> [abcd]  
> opts = ''  
> backend\_module = asedb_sqlite3\_backend.asedb\_sqlite3_backend  
> backend\_name = ASEdbSQlite3Backend  

- Run the additional setup by executing ```abcd-asedb --setup```.

All your databases are stored in the *$databases/all/* directory. If you run the script locally, you have full access to the all/ directory. To allow access to your databases from the outside (which is optional):

- Execute ```abcd-asedb --add-user USER``` (replace USER with the name of a person you want to give access to). This will prompt you for a public SSH key of USER, and then add an entry in the *~/.ssh/authorized_keys* file and create folders *$databases/USER* and *$databases/USER_readonly*.

If the user queries your machine remotely, they will have access only to what is in their user folders (*$databases/USER* and *$databases/USER_readonly*). Anything under $databases/USER_readonly* is considered to be read-only, while anything under $databases/USER* is readable and writable by the USER. 

If you want to give the USER access to your database, create a symlink to this database (which is under *$databases/all*) and put this symlink either in $databases/USER* or $databases/USER_readonly*. For example:

*$databases/patrick_readonly/db1.db -> *$databases/all/db1.db*  - user *patrick* has a read-only access to the database *db1.db*.

### Examples of local usage

- ```abcd db1.db 'energy>0.7' --count``` - count the number of selected rows
- ```abcd db1.db 'energy>0.8' --remove``` - remove selected configurations
- ```abcd db1.db --store conf1.xyz conf2.xyz info.txt``` - store original files in the database
- ```abcd db1.db --store configs/``` - store the whole directory in the database
- ```abcd db1.db --keys 'key1,key2' --omit-keys --show``` - show the database, but omit keys key1 and key2

### Examples of remote usage

- ```abcd --help``` - display help
- ```abcd --remote abcd@gc121mac1 db1.db --show```  - display the database
- ```abcd --remote abcd@gc121mac1 db1.db``` - display information about available keys
- ```abcd abcd@gc121mac1:db1.db 'energy<0.6 elements~C elements~H,F,Cl'``` - querying (remote can be specified using a colon before the database name)
- ```abcd abcd@gc121mac1:db1.db --extract-original-files --path-prefix extracted_files --untar``` - extract original files to the specified folder
- ```abcd abcd@gc121mac1:db1.db --write-to-file extr%03d.xyz``` - write configurations from the database to files extr001.xyz, extr002.xyz, ...

**Note for the OSX users:** If you see the following warning when connecting to a remote:  
> Warning: No xauth data; using fake authentication data for X11 forwarding.
> X11 forwarding request failed on channel 0

You can remove it by adding the following line to the ~/.ssh/config file on your local machine:  
> ForwardX11 no

### Queries

Queries are in a form <key><operator><val1,val2,...> <key><operator><val1,val2...>. <k><op><val> expressions separated by spaces are assumed to be ANDed, while values separated by commas are assumed to be ORed. Example:  

- ```'energy<0.1 user=alice,bob test=1'``` - means "*energy* less than 0.1 AND *user* is alice or bob AND *test* is equal to 1"  

Key can be any key in the Atoms.info dictionary. Operator can be one of the ```=, !=, <, <=, >, >=, ~```, where "~" means "contains" and can be used with the special key "elements":  

- ```elements~C elements~H,F,Cl``` - means "contains C AND at least one of H, F and Cl"

Operator ```!=``` is an exception, because comma-separated values that follow it are assumed to be ANDed, not ORed:  

- ```user!=alice,bob``` - means "*user* is not alice AND not bob"

**Notes** 

- If a query contains "<" or ">" it needs to be enclosed in quotes.
- (Only for the ASEdb SQLite3 backend) If a row doesn't contain a key K, then a query ```K!=VAL``` will not show this row. This might be fixed in future versions.

### Storing ###

Use ```--store [DIR/file] [DIR/file] ...``` to store configurations. This will find all parsable files specified, parse them with ASE and insert them into a specified database. To each configuration it also attaches "original files" - a file from which the configuration came from and other, non-parsable "auxilary files". Note the following terminology:

- configuration file - ASE-parsable file that contains a configuration
- multi-coniguration file - a configuration file which contains more than one configuration
- auxilary file - non-parsable file which is related to a configuration file that will be stored

Depending on whether directories or files are specified, *--store* can have slightly different behaviour:

- ```--store DIR1``` - store all parsable files under *DIR1*, and to each configuration attach auxiliary files that are on the direct ancestral path to the configuration, and auxiliary files which are in the same directory as the configuration. The files are tarred together and the directory structure is preserved.

- ```--store DIR1 DIR2 ...``` - equivalent to calling *--store* on each directory separately.

- ```--store config1 config2 ... aux1 aux2 ...``` - store files that contain a configuration, and to each attach all auxiliary files. In this case directory structure is not preserved. For example, the first inserted row will contain files *config1, aux1, aux2, ...*; while the second will contain *config2, aux1, aux2, ...*

- ```--store DIR aux1 aux2 ...``` - This stores a directory (or many of them), and attaches additional auxiliary files specified on the command line (treating them as if they were directly inside *DIR/*).

- ```--store DIR1 DIR2 ... conf1 conf2 ... aux1 aux2 ...``` - When parsable files, directories and auxiliary files are mixed together, it is equivalent to calling the following two commands separately:

 ```abcd db1 --store conf1 conf2 ... aux1 aux2```
 ```abcd db1 --store DIR1 DIR2 ... aux1 aux2 ...```

**Note:** Multi-configuration files are **not** stored as original files (only single-confiuration files are).

### Updating ###

Use ```--update [DIR/file] [DIR/file] ...``` to update configurations. It interprets the given arguments in exactly the same way as the *--update* option (see above). However, updating has a different behaviour from storing. After *--update* parses all given configurations, it checks whether these configurations already exist in the database. This check is done using the *uid* key, which is automatically added to the configuration when inserting it into the database. If the corresponding configuration in the database is found, it has its keys updated using the following rules:

- keys which are present in the new configuration, but not in the old one, are added
- keys which are present in the old configuration, but not in the new one, are left unchanged
- keys present in both configurations have their values set to the values from the new configuration

If the corresponding configuration is not found in the database, it is skipped (nothing is added or modified). However, the behaviour of *--update* can be modified using two flags, which can be either set to True or False:

- ```--upsert``` - If True, configurations which are not yet in the database are inserted. If False, the insert is skipped. The default is False.

- ```--replace``` - If True, it replaces the existing configuration with the a one (instead of updating it). If False, it is updated. The default is False.

### Extracting configurations ##

There are two ways of extracting configurations from the databse, but they both do different things:

#### --write-to-file ####

```--write-to-file FILE``` Uses the ASE *write()* function to write configurations into files. It accepts a file name as an argument. The file format is deduced from the extension (note: specifying .xyz will use the .extxyz format). If no formatting string is used, all selected configurations are written into a single, multi-configuration file:

```--write-to-file extracted.xyz```  # Produces a single file "extracted.xyz"

However, if a formatting string is used, *abcd* writes each configuration into a separate file:

```--write-to-file extracted_%03d.xyz```  # Produces files extracted\_001.xyz, extracted\_002.xyz, ...


#### --extract-original-files ####

*--extract-original-files* extracts original files which were attached to the configuration when calling --store. It extracts auxilary files (if any were added), and configuration files (only if the "source" file was a single-configuration file). The following options can also be used:

- ```--path-prefix PATH``` - extract files to a different directory. The default is the current working directory.

- ```--no-untar``` - don't untar files when extracting. This produces a tarball with all original files. Useful when name conflicts are expected.

## Backends

All backends need to conform to the Backend class defined in abcd/backend.py. 

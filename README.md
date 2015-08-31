# ABCD
**ABCD** (**A**tom-**B**ased **C**onfiguration **D**atabase) was designed to work with any backend that conforms to the specification. To use ABCD, two main steps have to be berformed:

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

- Execute ```abcd-asedb --add-user USER``` (replace USER with the name of a person you want to give access to). This will prompt you for a public SSH key of USER, and then add an entry in the *~/.ssh/authorized_keys* file and create a folder *$databases/USER*. If you want to give this user access to your database, you should create a symlink to a corresponding file under *$databases/all*. If the user queries your machine remotely, they will have access only to what is in their user folder.

### Examples of local usage

- ```abcd db1.db 'energy>0.7' --count``` - count the number of selected rows
- ```abcd db1.db 'energy>0.8' --remove``` - remove selected configurations
- ```abcd db1.db --store conf1.xyz conf2.xyz info.txt``` - store original files in the database
- ```abcd db1.db --store configs/``` - store the whole directory in the database
- ```abcd db1.db --omit-keys 'key1,key2' --show``` - omit keys key1 and key2

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

## Backends

All backends need to conform to the Backend class defined in abcd/backend.py. 

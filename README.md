# ABCD
## Frontend
Apart from ASE (with James Kermode's patch), no additional python modules or packages are needed to query remote databases. To run the script locally a backend is needed, as well as the "prettytable" and "numpy" python packages.

### Examples of remote querying/retrieval

- ```abcd --help``` - display help
- ```abcd --remote abcd@gc121mac1 db1.db --show```  - display the database
- ```abcd --remote abcd@gc121mac1 db1.db``` - display information about available keys
- ```abcd --remote abcd@gc121mac1 db1.db 'energy<0.6 elements~C elements~H,F,Cl'``` - querying
- ```abcd --remote abcd@gc121mac1 db1.db --extract-original-files --path-prefix extracted_files``` - extract original files to the specified folder
- ```abcd --remote abcd@gc121mac1 db1.db --write-to-file extr%03d.xyz``` - write configurations from the database to files extr001.xyz, extr002.xyz, ...

### Examples of running locally

- ```abcd db1.db 'energy>0.7' --count``` - count number of selected rows
- ```abcd db1.db 'energy>0.8' --remove --no-confirmation``` - remove selected configurations, don\'t ask for confirmation
- ```abcd db1.db --store conf1.xyz conf2.xyz info.txt``` - store original files in the database
- ```abcd db1.db --store configs/``` - store the whole directory in the database
- ```abcd db1.db --omit-keys 'key1,key2' --show``` - omit keys key1 and key2

### Queries

Queries are in a form <key><operator><val1,val2,...> <key><operator><val1,val2...>. <k><op><val> expressions separated by spaces are assumed to be ANDed, while values separated by commas are assumed to be ORed. Example:  

- ```'energy<0.1 user=alice,bob test=1'``` - means "*energy* less than 0.1 AND *user* is alice or bob AND *test* is equal to 1"  

Key can be any key in the Atoms.info dictionary. Operator can be one of the ```=, !=, <, <=, >, >=, ~```, where "~" means "contains" and can be used with the special key "elements":  

- ```elements~C elements~H,F,Cl``` - means "contains C AND at least one of H, F and Cl"

Operator ```!=``` is an exception, because comma-separated values that follow it are assumed to be ANDed, not ORed:  

- ```user!=alice,bob``` - means "*user* is not alice AND not bob"

Note that if a query contains "<" or ">" it needs to be enclosed in quotes.

### Installing

No install is needed when the script is to be run only remotely. To use it locally:

- Run ```python setup.py install --user``` in the top directory to install the abcd package. It will install the abcd tool on your system.
- Install the backend by running its corresponding setup script in the same way
- If using the ASEdb backend, run the additional setup by executing "python asedb_sqlite3_backend.py --setup". asedb_sqlite3_backend.py can be found under "abcd/backends/asedb_sqlite3/asedb_sqlite3_backend/".
- The script is now ready to be used. To use it, just call ```abcd```

NOTE: It is possible that the top level setup.py script will install a fresh ase package even if one already exists (this is a bug which will hopefully soon be fixed). The new ase package will not be patched, so the script might not work properly. If this happens, you will either have to patch the new version or remove it so that only the old one is present. To test if your version of ase is patched, run ```ase-db --help```. If it has options -x and -W, you are using the patched version. 

### Allowing access to your databases from the outside
This section assumes that you have already installed the backend (see previous section for instructions how to do it). To allow remote access, you will need a separate user on your Unix machine (say, "abcd"). In the ```~/.ssh/authorized_keys``` file you should put a public key of a person you want to grant access to. Each line should be in the following format:
>command="abcd ${SSH\_ORIGINAL\_COMMAND} --ssh --user USER" ssh-rsa AAAAB3NzaC1y...QoJjD3eACfT user@email.com  

Where "USER" should be substituted for the name of the owner of the key. Each time this key is used to log into this computer, the script abcd is executed with user-specified arguments and additional arguments: --user USER and --ssh.

In the future, adding users to the authorised_keys file will handled be a script.

In case of the ASEdb backend, all your databases are stored in the $databases/all/ directory. If you run the script locally, you have full access to the all/ directory. If you want to give someone access to your files, you should create a directory with their name (which should be the same as in the *authorized_keys* file) and in it symlinks to corresponding files under $databases/all. If the user queries your machine remotely, they will have access only to files in their folder.

## Backends

All backends need to conform to the Backend class defined in abcd/backend.py. 

# ABCD
## Frontend
The command line interface is under abcd/cli.py. Apart from ASE (with James Kermode's patch), no additional python modules or packages are needed to query remote databases.  
To run the script locally a backend is needed, as well as the "prettytable" and "numpy" python packages.

### Examples of remote querying/retrieval

- ```cli.py --help``` - display help
- ```cli.py --remote abcd@gc121mac1 db1.db --show```  - display the database
- ```cli.py --remote abcd@gc121mac1 db1.db``` - display information about available keys
- ```cli.py --remote abcd@gc121mac1 db1.db 'energy<0.6,id>4'``` - querying
- ```cli.py --remote abcd@gc121mac1 db1.db --extract-original-file --target extracted``` - extract files to the specified folder
- ```cli.py --remote abcd@gc121mac1 db1.db 1 --write-to-file extr.xyz``` - write the first row to the file extr.xyz

### Examples of running locally

- ```cli.py db1.db 'energy>0.7' --count``` - count number of selected rows
- ```cli.py db1.db 'energy>0.8' --remove --no-confirmation``` - remove selected configurations, don\'t ask for confirmation
- ```cli.py db1.db --store conf1.xyz conf2.xyz info.txt``` - store original files in the database
- ```cli.py db1.db --store configs/``` - store the whole directory in the database
- ```cli.py db1.db --omit-keys 'user,id' --show``` - omit keys "user" and "id"

### Installing

No install is needed when the script is to be run only remotely. To use it locally:

- Run ```python setup.py install --user``` in the top directory to install the abcd package
- Install the backend by running its corresponding setup script in the same way
- Run the cli.py script and specify the path to the databases directory

### Allowing access to your databases from the outside
You will need a separate user on your Unix machine (say, "abcd"). In the ```~/.ssh/authorized_keys``` file you should put a public key of a person you want to grant access to. Each line should be in the following format:
>command="path/to/cli.py ${SSH\_ORIGINAL\_COMMAND} --user USER" ssh-rsa AAAAB3NzaC1y...QoJjD3eACfT user@email.com  

Where path/to/cli.py should be substituted for the path to the cli.py script, and user for the name of the owner of the key. Each time this key is used to log into this computer, the script abcd.py is executed with user-specified arguments, and also an additional argument: --user USER.

Next, create a directory databases/, with a subdirectory all/. In the all/ directory all the databases will be stored. If you run the script locally, you have full access to the all/ directory. If you want to give someone access to your files, you should create a directory with their name (which should be the same as in the authorized_keys file) and in it symlinks to corresponding files under databases/all. If the user queries your machine remotely, they will have access only to files in their folder.

## Backends

All backends need to conform to the Backend class defined in abcd/backend.py. 

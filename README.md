# ABCD for remote querying
The current version has the ase-db backend and all the arguments that can be passed to ase-db can also be passed to abcd.py. No additional modules are needed to query a remote database. The connection works via ssh - to gain access to the collection of the databases on a remote machine, your public key has to be sent to the machine's owner.

### Examples of usage
Examples below assume that abcd.py is already set up on a remote machine and the databases collection is present. We will use abcd@gc121mac1.eng.cam.ac.uk as an example.

- ```./abcd.py --remote abcd@gc121mac1.eng.cam.ac.uk --list``` - lists all databases you have access to on server abcd@gc121mac1
- ```./abcd.py --remote abcd@gc121mac1.eng.cam.ac.uk water.db``` - display the database
- ```./abcd.py --remote abcd@gc121mac1.eng.cam.ac.uk water.db 1 --json``` - show the first row of database water.db in json representation (assuming you have access to this database)
- ```./abcd.py --remote abcd@gc121mac1.eng.cam.ac.uk water.db 'energy>0.9'``` - show all the entries with energy greater than 0.9


# ABCD with local database
If you want to have your own collection of databases on your local machine, additional python modules have to be present and some setup has to be performed.

### Requirements:
- ASE installed from source (not using pip) + supplied patch
- numpy

### Installing ASE:
- Download it from https://wiki.fysik.dtu.dk/ase-files/python-ase-3.9.0.4465.tar.gz
- Apply the patch written by James Kermode (supplied here).
- execute ```python setup.py install```

### Setting up abcd
You will need a separate user on your Unix machine (say, "abcd"). In the ```~/.ssh/authorized_keys``` file you should put a public key of a person you want to grant access to. Each line should be in the following format:
>command="path/to/abcd.py ${SSH_ORIGINAL_COMMAND} --user USER" ssh-rsa AAAAB3NzaC1y...QoJjD3eACfT user@email.com  

Where path/to/abcd.py should be substituted for the path to the abcd.py script, and user for the name of the owner of the key. Each time this key is used to log into this computer, the script abcd.py is executed with user-specified arguments, and also an additional argument: --user USER.

Next, create a directory databases/, with a subdirectory all/. In the all/ directory all the databases will be stored. If you run the script locally, you have full access to the all/ directory. If you want to give someone access to your files, you should create a directory with their name (which should be the same as in the authorized_keys file) and in it symlinks to corresponding files under databases/all. If the user queries your machine remotely, they will have access only to files in their folder.

### Running abcd:
First time abcd.py is executed, it will ask you for the path to ase, and for the path to the databases directory. After you specify this, the paths will be stored in a config file which will be read each time abcd.py is executed.

### Examples of usage

- ```./abcd.py --list``` - lists all files in the databases/all/ directory
- ```./abcd.py water.db -c ++``` - display all the columns and rows of the database
- ```./abcd.py -a test.xyz test.db -Ao --unique``` - adds the test.xyz file to the test.db database. If the database does not exist yet, it is created under databases/all.
- ```./abcd.py -x water.db 1``` - extract original file from the first row of the database (if it was stored with the -o flag)


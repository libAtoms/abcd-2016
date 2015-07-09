# TODO

## Frontend

* Remote store
* remote delete
* store key=value pairs given on the command line
* --store should look for one or more files/directories and find the first file that is successfully readable into an configuration, and store all files as "original files" using tar
* copy/move files from one database to another, including a new database 
* Ability to update configurations (check out, do some calculations, update the database). For this the ids need to be sorted out (configurations can be identified by their unique_id keys).
* specify cli options in .abcd config file, overriden by actual cli args
* Add the --list option to the command line which will list all available databases
* Adding many files each containing a single configuration to the database at the same time
* Multi-column sorting on the summary table
* Add the --unique option to the command line for the summary table
* Add the --long option to the command line that will display more information about a single sonfiguration
* Translate the CLI query language to the mongodb query language
* Ability to "remove" hard-coded keys from the Atoms object
* Rename cli.py to something more sensible (problem with name shadowing of the abcd package prevents it now)
* Allow different backends to be chosen without modifying the script
* Update the mongodb backend

## asedb-based backend

* Make sure unique ids stay the same when the configurations are moved around

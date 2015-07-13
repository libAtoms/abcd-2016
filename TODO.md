# TODO

## Frontend

* Remote store
* remote delete
* ~~store key=value pairs given on the command line~~ 
* ~~--store should look for one or more files/directories and find all files that can successfully be parsed into configurations. for each file that yields a single configuration, store this file and all other files that cannot be parsed should be stored as "original files" using tar. for files that yield multiple configurations, DO NOT store the configuration file, print a warning about this, and store the non-parsable files as usual.~~ 
* copy/move files from one database to another, including a new database
* James: asedb-patch functionality should move to abcd. special properties that are stored in named asedb properties: number of atoms, cell, pbc, unique_id, ctime, mtime, user, positions, numbers
* Ability to update configurations (check out, do some calculations, update the database). For this the ids need to be sorted out (configurations can be identified by their unique_id keys).
* specify cli options in .abcd config file, overriden by actual cli args
* ~~Add the --list option to the command line which will list all available databases~~ 
* Multi-column sorting on the summary table
* Add the --unique option to the command line for the summary table
* Add the --long option to the command line that will display more information about a single sonfiguration
* Translate the CLI query language to the mongodb query language. example: "energy<3 formula=H2O,H2O2" where spaces are ANDs and commas are ORs (ORs apply to multiple values to same key)
* Rename cli.py to something more sensible (problem with name shadowing of the abcd package prevents it now)
* Allow different backends to be chosen without modifying the script

## asedb-based backend

* Make sure unique ids stay the same when the configurations are moved around

## mongodb-based backend

* Update it so it conforms to the Backend class
# TODO

## Frontend

* Ability to update configurations (check out, do some calculations, update the database). For this the ids need to be sorted out (configurations can be identified by their unique_id keys).
* James: asedb-patch functionality should move to abcd. special properties that are stored in named asedb properties: number of atoms, cell, pbc, unique_id, ctime, mtime, user, positions, numbers
* copy/move files from one database to another, including a new database
* Multi-column sorting on the summary table
* Add the --unique option to the command line for the summary table
* Add the --long option to the command line that will display more information about a single sonfiguration
* Rename cli.py to something more sensible (problem with name shadowing of the abcd package prevents it now)
* Allow different backends to be chosen without modifying the script
* specify cli options in .abcd config file, overriden by actual cli args

## asedb-based backend

* Make sure unique ids stay the same when the configurations are moved around
* Make searching of arrays contents possible.

## mongodb-based backend

* Update it so it conforms to the Backend class

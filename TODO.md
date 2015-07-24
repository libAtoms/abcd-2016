# TODO

## Frontend

* Move arguments around in the ssh config file
* Remove the ssh setup instructions from the README
* Rename cli.py to something more sensible
* Ability to update configurations (check out, do some calculations, update the database). For this the ids need to be sorted out (configurations can be identified by their unique_id keys).
* James: asedb-patch functionality should move to abcd. special properties that are stored in named asedb properties: number of atoms, cell, pbc, unique_id, ctime, mtime, user, positions, numbers
* copy/move files from one database to another, including a new database
* Multi-column sorting on the summary table
* Add the --unique option to the command line for the summary table
* Add the --long option to the command line that will display more information about a single sonfiguration
* Allow different backends to be chosen without modifying the script
* specify cli options in .abcd config file, overriden by actual cli args

## asedb-based backend

* Create a top-level script which is user-callable which does all the setup (don't do this automatically).
* Make the same script be able to add users by --user
* Make sure unique ids stay the same when the configurations are moved around
* Make searching of arrays contents possible.

## mongodb-based backend

* Update it so it conforms to the Backend class

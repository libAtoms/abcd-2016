# TODO

* Remote writing
* Storing multiple files
* Adding files from one databse to another
* Ability to update configurations (check out, do some calculations, update the database). For this the ids need to be sorted out (configurations can be identified by their unique_id keys).
* Add the --list option to the command line which will list all available databases
* Adding many files to the database at the same time
* Make sure unique ids stay the same when the configurations are moved around
* Multi-column sorting
* Add the --unique option to the command line
* Add the --long option to the command line that will display more information about a single sonfiguration
* Translate the CLI query language to the mongodb query language
* Ability to "remove" hard-coded keys from the Atoms object
* Rename cli.py to something more sensible (problem with name shadowing of the abcd package prevents it now)
* Allow different backends to be chosen without modifying the script
* Update the mongodb backend
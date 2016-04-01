# TODO

## Frontend

* Create a UI for working with configuration files.
* Create a backend abstract factory
* Add general backend tests
* Add "interactive" mode to CLI (i.e. it doesn't auto return)
* <del>Make the ASE install automatic (currently it asks the user to manually
  install the latest development version from
  https://wiki.fysik.dtu.dk/ase/download.html#latest-development-release)</del>
* copy/move files from one database to another, including a new database
* Ability to add keys with commas
* Add the --unique option to the command line for the summary table

## API

* Convert CLI into a Python class that can be interacted with using Python.
  CLI subcommands become methods.
* Relicense as LGPL?

## asedb-based backend

* 'k!=v' looks for configurations containing a key "k" which is different
  from "v", instead of looking for all configurations for which !(k=v)
  evaluates to True (so configurations not containing "k" are not returned) -
  note this is an intended behaviour on the ASEdb end, not a bug.

## mongodb-based backend

* Update it so it conforms to the Backend class

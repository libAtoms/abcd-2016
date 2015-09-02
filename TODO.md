# TODO

## Frontend

* copy/move files from one database to another, including a new database
* Multi-column sorting on the summary table (using a dictionary where keys are column names and values are either ASCENDING or DESCENDING).
* Ability to add keys with commas
* Add the --unique option to the command line for the summary table

## asedb-based backend

* 'k!=v' looks for configurations containing a key "k" which is different from "v", instead of looking for all configurations for which !(k=v) evaluates to True (so configurations not containing "k" are not returned).

## mongodb-based backend

* Update it so it conforms to the Backend class

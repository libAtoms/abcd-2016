Design Goals
============

Atom Based Computational Database
---------------------------------

Provide the following:

 * Command line tool to **store**, **interrogate** and **fetch** atomic
   configurations in a database.
 * Python API to interact with the database in an analogous way to the
   CLI client.
 * Backend specification so that the CLI and API can be interfaced with a
   wide range of database solutions.

Language and framework:

  * Written in pure Python;
  * Works flawlessly with Python 2.7 and 3.3 upwards;
  * Depends on ASE for working with `Atoms` objects.

Backends:
  * Agnostic according to defined specification.
  * `ase.db` included
  * `mongodb included
  * Aiida as a target

Design considerations
---------------------

* Command line tool inspired by “icepick”: store configurations, query,
  extract and update them and which is agnostic with respect to the back-end.
  At least two different back-ends will be created initially, one based on
  ase-db using James’ patch, and Martin will make sure Aiida can also be used
  as a back-end.

* Communication between the command line tool and the backend is via ASE:
  files to be stored are read in via ASE’s importers, and the Atoms object
  that is created (including all metadata) is passed to the backend. simple
  translators are written for Aiida using the already existing ASE importer
  (may need to be extended to pick up all metadata)

* The command line tool can be extended or built upon to do Chris’s
  fetch-compute_property-store functionality, it is up to the database
  backend to tag the config with unique IDs so that subsequent stores are
  recognised as updates, we don’t need to care about how that is done.

* queries: the command line tool needs to accept a set of predicates on the
  metadata. we can discuss and argue how general this needs to be: at the
  minimum, it is a list of predicates which are “and”-ed. the other end of
  the complexity is a complete predicate tree, allowing any combination of
  “and” and “or” relations between the predicates.

* Authentication: Martin says that Aiida is thinking about OpenID  - I think
  in addition we need something much simpler as well, and there is no harm
  in multiple auth methods. I looked at how gitolite uses ssh keys, and it’s
  simple: a single unix user is created on the system, and a number of keys
  can be placed in its .ssh/authorised_keys file. Each key in this file is
  associate with a command, e.g. “/usr/local/bin/abcd <user>” and an argument
  to this command is the user name. The database is queried using ssh, e.g

             ssh abcd@gc121mac1.eng.cam.ac.uk --command --line --arguments --and --query --predicates

  and when the user authenticates, instead of the shell, the /usr/local/bin/abcd
  command gets executed with the first argument being the <user> and the
  subsequent arguments are taken from the above ssh command. So if I want to
  give someone access, all I have to do is to put their ssh key into this
  authorized_keys file. We can also permit anonymous access by having no
  password on this account, and the /usr/local/bin/abcd program would then
  execute without a <user> argument, which would give access to those database
  objects that are tagged for anonymous access


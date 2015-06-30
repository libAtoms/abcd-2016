#! /usr/bin/env python

import os
import sys
import argparse
import subprocess

description = """Selection is a comma-separated list of
selections where each selection is of the type "ID", "key" or
"key=value".  Instead of "=", one can also use "<", "<=", ">=", ">"
and  "!=" (these must be protected from the shell by using quotes).
Special keys: id, user, calculator, age, natoms, energy, magmom,
and charge.  Chemical symbols can also be used to select number of
specific atomic species (H, He, Li, ...)."""

examples = ['''
./abcd.py --remote remote@remote.com --list   - list all databases that you have access to
        at remote@remote.com
./abcd.py --remote remote@remote.com water.db   - display the contents of the database water.db
./abcd.py --list   - list all local databases
./abcd.py -a test.xyz test.db -Ao --unique   - add the test.xyz file to the test.db database. 
        If the database does not exist yet, it is created under databases/all''']

def main(args = sys.argv[1:]):
    if isinstance(args, str):
        args = args.split(' ')
    parser = argparse.ArgumentParser(usage = 'Usage: %(prog)s [db-name] [selection] [options]',
                        description = description,
                        epilog = 'Selection examples: ' + ', '.join(examples) + '.',
                        formatter_class=argparse.RawTextHelpFormatter)

    # Display usage if no arguments are supplied
    if len(sys.argv)==1:
        parser.print_usage()
        sys.exit(1)
    
    add = parser.add_argument
    add('-v', '--verbose', action='store_true', default=False)
    add('-q', '--quiet', action='store_true', default=False)
    add('-n', '--count', action='store_true',
        help='Count number of selected rows.')
    add('-l', '--long', action='store_true',
        help='Long description of selected row')
    add('-i', '--insert-into', metavar='db-name',
        help='Insert selected rows into another database.')
    add('-a', '--add-from-file', metavar='(type:)filename...',
        help='Add results from file.')
    add('-o', '--store-original-file', action='store_true',
                    help='When adding files with --add-from-file, include original filename \nand full contents')
    add('-x', '--extract-original-file', action='store_true',
        help='Extract an original file stored with -o/--store-original-file')
    add('-W', '--write-to-file', metavar='(type:)filename',
        help='Write selected rows to file(s). Include format string for multiple \nfiles, e.g. file_%%03d.xyz')
    add('-A', '--all-data', action='store_true', default=False,
        help="Include atoms.info and atoms.arrays dictionaries in key_value_pairs and data")
    add('-k', '--add-key-value-pairs', metavar='key1=val1,key2=val2,...',
        help='Add key-value pairs to selected rows.  Values must be numbers '
        'or strings and keys \nmust follow the same rules as keywords.')
    add('-L', '--limit', type=int, default=500, metavar='N',
        help='Show only first N rows (default is 500 rows).  Use --limit=0 '
        'to show all.')
    add('--offset', type=int, default=0, metavar='N',
        help='Skip first N rows.  By default, no rows are skipped')
    add('--delete', action='store_true',
        help='Delete selected rows.')
    add('--delete-keys', metavar='key1,key2,...',
        help='Delete keys for selected rows.')
    add('-y', '--yes', action='store_true',
        help='Say yes.')
    add('--explain', action='store_true',
        help='Explain query plan.')
    add('-c', '--columns', metavar='col1,col2,...',
        help='Specify columns to show.  Precede the column specification \n'
        'with a "+" in order to add columns to the default set of columns. \n '
        'Precede by a "-" to remove columns.  Use "++" for all.')
    add('-s', '--sort', metavar='column', default='id',
        help='Sort rows using column.  Use -column for a descendin sort.  '
        'Default is to sort after id.')
    add('--cut', type=int, default=35, help='Cut keywords and key-value '
        'columns after CUT characters.  Use --cut=0 \nto disable cutting. '
        'Default is 35 characters')
    #add('-p', '--plot', metavar='[a,b:]x,y1,y2,...',
        #help='Example: "-p x,y": plot y row against x row. Use '
        #'"-p a:x,y" to make a plot for each value of a.')
    add('--csv', action='store_true',
        help='Write comma-separated-values file.')
    #add('-w', '--open-web-browser', action='store_true',
        #help='Open results in web-browser.')
    add('--no-lock-file', action='store_true', help="Don't use lock-files")
    add('--analyse', action='store_true',
        help='Gathers statistics about tables and indices to help make '
        'better query planning choices.')
    add('-j', '--json', action='store_true',
        help='Write json representation of selected row.')
    add('--unique', action='store_true',
        help='Give rows a new unique id when using --insert-into.')
    add('--list', action = 'store_true', help = 'Lists all the databases you have access to')
    add('--remote', help = 'Specify the remote')
    add('-u', '--user', help = argparse.SUPPRESS)
    add('database', nargs = '?', help = 'Specify the database')
    add('query', nargs = '?', default = '', help = 'Query')
    args = parser.parse_args()

    verbosity = 1 - args.quiet + args.verbose

    try:
        run(args, verbosity)
    except Exception as x:
        if verbosity < 2:
            print('{0}: {1}'.format(x.__class__.__name__, x))
            sys.exit(1)
        else:
            raise

def run(args, verbosity):

    # Try to import the interface. If it fails, the script only has limited
    # functionality (only remote querying without saving).
    try:
        from asedb_sqlite3_interface import asedb_sqlite3_interface
        interface_enabled = True
    except ImportError:
        interface_enabled = False
    
    # User specified the "user" argument, quit.
    if args.user and args.remote:
        print 'Unknown option --user. Terminating'
        sys.exit()

    # Query to the remote server. Remove the --remote argumnet and 
    # send the commmand via ssh. Mode: remote
    elif not args.user and args.remote:

        ssh_call = 'ssh {} '.format(args.remote)

        # Remove the 'remote' argument
        for arg in ['--remote', '-remote', '--r', '-r']:
            while arg in sys.argv:
                pos = sys.argv.index(arg)
                sys.argv = sys.argv[:pos] + sys.argv[pos + 2:]

        arguments = ' '.join(sys.argv[1:])
        arguments = '\' {}\''.format(arguments)
        command = ssh_call + arguments
        
        # Execute the ssh command, capture the output
        try:
            output = subprocess.check_output(command, shell=True)
        except subprocess.CalledProcessError as e:
            print e.output
            sys.exit()

        if interface_enabled:
            interface = asedb_sqlite3_interface(args, verbosity, mode = 'remote')
            if args.write_to_file:
                interface.write_to_file(contents = output)
            else:
                print output
        else:
            print output

    else:
        if not args.user and not args.remote:
            interface = asedb_sqlite3_interface(args, verbosity, mode = 'local')
        else:
            interface = asedb_sqlite3_interface(args, verbosity, mode = 'incoming')

        # Can be used without any database specified
        if args.list:
            interface.list()
        
        # Database has to be specified as an argument
        if interface.database:
            if args.analyse:
                interface.analyse()
            elif args.count:
                interface.count()
            elif args.explain:
                interface.explain()
            elif args.add_from_file:
                interface.add_from_file()
            elif args.add_key_value_pairs or args.delete_keys:
                interface.modify_keys()
            elif args.delete:
                interface.delete()
            elif args.insert_into:
                interface.insert_into()
            elif args.write_to_file:
                interface.write_to_file()
            elif args.extract_original_file:
                interface.extract_original_file()
            else:
                if args.long:
                    interface.long()
                elif args.json:
                    interface.json()
                else:
                    interface.default()

main()

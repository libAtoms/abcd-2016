#! /usr/bin/env python

import os
import sys
import optparse
from subprocess import call

description = """Selecton is a comma-separated list of
selections where each selection is of the type "ID", "key" or
"key=value".  Instead of "=", one can also use "<", "<=", ">=", ">"
and  "!=" (these must be protected from the shell by using quotes).
Special keys: id, user, calculator, age, natoms, energy, magmom,
and charge.  Chemical symbols can also be used to select number of
specific atomic species (H, He, Li, ...)."""

examples = ['calculator=nwchem',
            'age<1d',
            'natoms=1',
            'user=alice',
            '2.2<bandgap<4.1',
            'Cu>=10']

def main(args = sys.argv[1:]):
    if isinstance(args, str):
        args = args.split(' ')
    parser = optparse.OptionParser(
        usage = 'Usage: %prog db-name [selection] [options]',
        description = description,
        epilog = 'Selection examples: ' + ', '.join(examples) + '.')
    
    add = parser.add_option
    add('-v', '--verbose', action='store_true', default=False)
    add('-q', '--quiet', action='store_true', default=False)
    add('-n', '--count', action='store_true',
        help='Count number of selected rows.')
    add('-l', '--long', action='store_true',
        help='Long description of selected row')
    add('-i', '--insert-into', metavar='db-name',
        help='Insert selected rows into another database.')
    add('-a', '--add-from-file', metavar='[type:]filename...',
        help='Add results from file.')
    add('-o', '--store-original-file', action='store_true',
        help='When adding files with --add-from-file, include original filename and full contents')    
    add('-x', '--extract-original-file', action='store_true',
        help='Extract an original file stored with -o/--store-original-file')
    add('-W', '--write-to-file', metavar='[type:]filename',
        help='Write selected rows to file(s). Include format string for multiple files, e.g. file_%03d.xyz')
    add('-A', '--all-data', action='store_true', default=False,
        help="Include atoms.info and atoms.arrays dictionaries in key_value_pairs and data")
    add('-k', '--add-key-value-pairs', metavar='key1=val1,key2=val2,...',
        help='Add key-value pairs to selected rows.  Values must be numbers '
        'or strings and keys must follow the same rules as keywords.')
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
        help='Specify columns to show.  Precede the column specification '
        'with a "+" in order to add columns to the default set of columns.  '
        'Precede by a "-" to remove columns.  Use "++" for all.')
    add('-s', '--sort', metavar='column', default='id',
        help='Sort rows using column.  Use -column for a descendin sort.  '
        'Default is to sort after id.')
    add('--cut', type=int, default=35, help='Cut keywords and key-value '
        'columns after CUT characters.  Use --cut=0 to disable cutting. '
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
    add('-u', '--user', help = optparse.SUPPRESS_HELP)
    opts, args = parser.parse_args(args)

    verbosity = 1 - opts.quiet + opts.verbose

    try:
        run(opts, args, verbosity)
    except Exception as x:
        if verbosity < 2:
            print('{0}: {1}'.format(x.__class__.__name__, x))
            sys.exit(1)
        else:
            raise

def run(opts, args, verbosity):

    # Query to the remote server. Remove the --remote argumnt and send the commmand
    # via ssh
    if not opts.user and opts.remote:

        ssh_call = 'ssh {} '.format(opts.remote)

        # Remove the 'remote' argument
        for arg in ['--remote', '-remote', '--r', '-r']:
            while arg in sys.argv:
                pos = sys.argv.index(arg)
                sys.argv = sys.argv[:pos] + sys.argv[pos + 2:]

        arguments = ' '.join(sys.argv[1:])
        arguments = '\' {}\''.format(arguments)
        command = ssh_call + arguments
        
        call(command, shell=True)
        return

    # User specified the user argument, quit
    if opts.user and opts.remote:
        print 'Unknown option --user. Terminating'
        sys.exit()

    from asedb_sqlite3_interface import asedb_sqlite3_interface
    api = asedb_sqlite3_interface(opts, args, verbosity)

    # Incoming
    if opts.user and not opts.remote:

        # Can be used without any database specified
        if opts.list:
            api.list()

        # Database has to be specified as an argument
        if api.database:
            if opts.analyse:
                api.analyse()
            elif opts.count:
                api.count()
            elif opts.explain:
                api.explain()
            else:
                if opts.long:
                    api.long()
                elif opts.json:
                    api.json()
                else:
                    api.default()

    # Local
    elif not opts.user and not opts.remote:

        # Can be used without any database specified
        if opts.list:
            api.list()
        
        # Database has to be specified as an argument
        if api.database:
            if opts.analyse:
                api.analyse()
            elif opts.count:
                api.count()
            elif opts.explain:
                api.explain()
            elif opts.add_from_file:
                api.add_from_file()
            elif opts.add_key_value_pairs or opts.delete_keys:
                api.modify_keys()
            elif opts.delete:
                api.delete()
            elif opts.insert_into:
                api.insert_into()
            elif opts.write_to_file:
                api.write_to_file()
            elif opts.extract_original_file:
                api.extract_original_file()
            else:
                if opts.long:
                    api.long()
                elif opts.json:
                    api.json()
                else:
                    api.default()

main()

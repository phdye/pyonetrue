from .package import run_cli_logic, CliOptions
from .vendor.docopt import docopt
from pathlib import Path
from .vendor.docopt import docopt
from pathlib import Path
import sys

USAGE = r"""
Usage:
  pyonetrue [options] <input>
  pyonetrue (-h | --help)
  pyonetrue --version

Flatten Python package files into a well ordered, single module.

<input> can be a python package name, a directory or a file:
  package    The <package-root> via PYTHONPATH becomes the directory.
  directory  All Python files under the directory will be flattened.
  file       It will be ordered, fixes a poor ordering.

In all cases, the module is written to the specified output file or stdout.

A main guard is a block of code that is only executed when the module
is run as a script. It is typically used to test the module or to
provide a command-line interface. The main guard is usually
written as:

    if __name__ == '__main__':
        # code to execute when the module is run as a script
        pass

<package>/__main__.py is a special module that is executed when the
package is run as a script.  It is typically used to provide a command-line
interface to the package.  If such a module is present, it will be included
at the end of without reordering unless the --no-cli option is used.  Other
__main__.py modules are not included by default.  If you want to include
one of them instead, you can use the --main-from option to specify the
sub-package from which to include __main__.py.

Default behavior is to :
* Main guards are discarded, but this can be changed with the --main-all
  or --main-from options.
* Write the output to stdout, but this can be changed with the --output
* Name clashes, duplicate top-level names, are not allowed by default.

Options:
  --output <file>      Write output to file (default: stdout).
  --no-cli             Do not include CLI code, __main__.py.
  --main-from <mod>    Include __main__.py from the specified sub-package.
                       Only one __main__.py module is allowed.
                       Overrides --no-cli.
  --all-guards         Include all __main__ guards. (default: discard)
  --guards-from <mod>  Include __main__ guards only from <mod>.
  --exclude <exclude>  Exclude specified packages or modules, comma separated.
  --include <include>  Exclude specified packages or modules, comma separated.
  --ignore-clashes     Allow duplicate top-level names without error.
  -h, --help           Show this help message.
  --version            Show version.
"""

__version__ = "0.5"

def main(argv=sys.argv):
    args = docopt(USAGE, argv=argv[1:], version=__version__)
    if args['--no-cli'] and args['--main-from']:
        raise ValueError("Invalid options: cannot specify both --no-cli and --main-from")
    opt = CliOptions(
        package_path=args['<input>'],
        output=args.get('--output') or 'stdout',
        no_cli=bool(args.get('--no-cli')),
        main_from=args.get('--main-from', '').split(',') if args.get('--main-from') else [],
        guards_all=bool(args.get('--all-guards')),
        guards_from=args.get('--guards-from', '').split(',') if args.get('--guards-from') else [],
        ignore_clashes=bool(args.get('--ignore-clashes')),
        exclude=args.get('--exclude', '').split(',') if args.get('--exclude') else [],
        include=args.get('--include', '').split(',') if args.get('--include') else [],
    )
    if len(opt.main_from) > 1:
        raise ValueError("Only one --main-from option is allowed.")
    opt.main_from = opt.main_from[0] if opt.main_from else None
    if opt.main_from:
        opt.no_cli = False
    elif not opt.no_cli:
        opt.main_from = '__main__' # primary package
    return run_cli_logic(opt)

if __name__ == "__main__":
    sys.exit(main())

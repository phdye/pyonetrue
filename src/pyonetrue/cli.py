USAGE=r"""
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
* All relative imports are eliminated. Flattened output is fully self-contained.
* Main guards are discarded, but this can be changed with the --main-all
  or --main-from options.
* Write the output to stdout, but this can be changed with the --output
* Name clashes, duplicate top-level names, are not allowed by default.
* If `__main__.py` is being included, prepend shebang.

Options:
  -s, --shebang <shebang>  Prepend <sheband> if `__main__.py` is being appended.  [default: #!/usr/bin/env python3]
  -o, --output <file>      Write output to file (default: stdout).
  --no-cli                 Do not include package's __main__.py.
  -e, --entry <entry>      Specify entry function as module[:func].  If repeated,
                           produces multiple single module programs. If no entry is
                           specified, the module's __main__ guard will be used. If 
                           --no-cli is specified, this option is ignored.
  -m, --main-from <mod>    Include __main__.py from the specified sub-package.
                           Only one __main__.py module is allowed.
                           Incompatible with --no-cli.
  -a, --all-guards         Include all __main__ guards. (default: discard)
  -g, --guards-from <mod>  Include __main__ guards only from <mod>.
  -E, --exclude <exclude>  Exclude specified packages or modules, comma separated.
  -i, --include <include>  Exclude specified packages or modules, comma separated.
  --entry <entry>          Explicitly build for the given entry point. May be
                           repeated. If omitted, all defined entry points are
                           used.
  --ignore-clashes         Allow duplicate top-level names without error.
  -h, --help               Show this help message.
  --version                Show version.
  --show-cli-args          Show the command line arguments that would be passed to the
                           CLI and exit.  This is useful for debugging.
"""

import sys

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # For Python 3.11 and earlier

try :
    from pathlib import Path
except ImportError:
    from .vendor.pathlib import Path

from .flattening import FlatteningContext
from .exceptions import CLIOptionError
from .vendor.docopt import docopt

__version__ = "0.6.8"

def discover_defined_entry_points(package_path: Path) -> list[str]:
    """Return entry point modules defined in a local pyproject.toml."""
    pyproject = package_path / "pyproject.toml"
    if not pyproject.exists():
        pyproject = package_path.parent / "pyproject.toml"
    entries = []
    if pyproject.exists():
        try:
            data = tomllib.loads(pyproject.read_text())
            scripts = data.get("project", {}).get("scripts", {})
            for target in scripts.values():
                mod = str(target).split(":", 1)[0]
                entries.append(mod)
        except Exception:
            pass
    return entries

__version__ = "0.5.4"

def main(argv=sys.argv):
    """Main entry point for the CLI tool.

    Parses command-line arguments, configures the FlatteningContext,
    executes the flattening process, and handles output.

    Args:
        argv (list of str): Command-line arguments (including program name).

    Returns:
        int: Exit code (0 on success, non-zero on error).

    Examples:
        >>> main(["pyonetrue", "my_package"])
        0
    """

    args = docopt(USAGE, argv=argv[1:], version=__version__)
    if args['--no-cli'] and args['--main-from']:
        raise CLIOptionError("cannot specify both --no-cli and --main-from")

    entries = args.get('--entry') or []
    if not isinstance(entries, list):
        entries = [entries] if entries else []
    
    entries = args.get('--entry')
    if entries and not isinstance(entries, list):
        entries = [entries]
    parsed_funcs = []
    for ent in entries or []:
        if ':' in ent:
            ent = ent.rsplit(':', 1)[1]
        elif '.' in ent:
            ent = ent.split('.')[-1]
        elif ent:
            ent = ent
        else:
            continue
        parsed_funcs.append(ent)
    ctx = FlatteningContext(
        package_path=args['<input>'],
        output=args.get('--output') or 'stdout',
        no_cli=bool(args.get('--no-cli')),
        main_from=args.get('--main-from', '').split(',') if args.get('--main-from') else [],
        guards_all=bool(args.get('--all-guards')),
        guards_from=args.get('--guards-from', '').split(',') if args.get('--guards-from') else [],
        ignore_clashes=bool(args.get('--ignore-clashes')),
        exclude=args.get('--exclude', '').split(',') if args.get('--exclude') else [],
        include=args.get('--include', '').split(',') if args.get('--include') else [],
        shebang=args.get('--shebang', '#!/usr/bin/env python3'),
        entry_points=entries,
    )

    if not ctx.entry_points:
        ctx.entry_points = discover_defined_entry_points(Path(ctx.package_path))

    ctx.main_from = ctx.main_from[0] if ctx.main_from else None
    if ctx.entry_funcs:
        ctx.no_cli = True
        ctx.main_from = None
    elif ctx.main_from:
        ctx.no_cli = False
    elif not ctx.no_cli:
        ctx.main_from = '__main__' # primary package
    if args['--show-cli-args']:
        print(f"CLI args:\n{ctx}")
        return 0

    entry_mods = ctx.entry_points or ([ctx.main_from] if ctx.main_from else [])
    if not entry_mods:
        entry_mods = [None]

    output_path = ctx.output
    if len(entry_mods) > 1 and output_path != "stdout":
        out_dir = Path(output_path)
        out_dir.mkdir(parents=True, exist_ok=True)
    else:
        out_dir = None

    for mod in entry_mods:
        sub_ctx = FlatteningContext(
            package_path=ctx.package_path,
            output=output_path,
            no_cli=ctx.no_cli,
            main_from=[mod] if mod else [],
            guards_all=ctx.guards_all,
            guards_from=ctx.guards_from,
            ignore_clashes=ctx.ignore_clashes,
            exclude=ctx.exclude,
            include=ctx.include,
            shebang=ctx.shebang,
        )

        sub_ctx.main_from = sub_ctx.main_from[0] if sub_ctx.main_from else None
        if sub_ctx.main_from:
            sub_ctx.no_cli = False
        elif not sub_ctx.no_cli:
            sub_ctx.main_from = "__main__"

        sub_ctx.discover_modules()
        sub_ctx.gather_main_guard_spans()
        spans = sub_ctx.get_final_output_spans()

        lines = []
        if sub_ctx.shebang:
            lines.append(sub_ctx.shebang.rstrip("\n") + "\n")
        lines.extend(span.text for span in spans)
        text = "".join(lines)

        if sub_ctx.output == "stdout":
            sys.stdout.write(text)
        else:
            if out_dir:
                fname = mod or "output"
                Path(out_dir / f"{fname}.py").write_text(text)
            else:
                Path(sub_ctx.output).write_text(text)

    return 0

if __name__ == "__main__":
    exit(main(sys.argv))

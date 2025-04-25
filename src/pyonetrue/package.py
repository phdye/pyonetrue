import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Union

from pyonetrue.flattening import FlatteningContext

DEBUG = False

@dataclass
class CliOptions:
    package_path       : Union[str, Path]     # dotted package name, packge root, or module path
    output             : Union[str, Path]     # output file path or 'stdout'
    include            : list
    exclude            : list
    guards_from        : list
    guards_all         : bool
    main_from          : str
    no_cli             : bool
    ignore_clashes     : bool

def build_flattening_context(cli: CliOptions):
    return FlatteningContext(cli.package_path)

def populate_flattening_context(ctx : FlatteningContext, cli: CliOptions):
    ctx.discover_modules(
        includes=cli.include,
        excludes=cli.exclude,
        no_cli=cli.no_cli,
        main_from=cli.main_from,
    )

def generate_flattened_spans(ctx, cli: CliOptions):
    return ctx.get_final_output_spans(
        include_all_guards=cli.guards_all,
        include_guards=cli.guards_from,
        main_from=cli.main_from,
        no_cli=cli.no_cli,
        ignore_clashes=cli.ignore_clashes,
    )

def write_flattened_output(spans, output_path: Union[str, Path]):
    output_path = Path(output_path)
    text = "\n".join(span.text for span in spans)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text)

def run_cli_logic(cli: CliOptions):
    if cli.no_cli and cli.main_from:
        raise ValueError("Invalid options: cannot specify both opt.no_cli and opt.main_from")
    ctx = build_flattening_context(cli)
    populate_flattening_context(ctx, cli)
    spans = generate_flattened_spans(ctx, cli)
    if DEBUG: print("DEBUG run_cli_logic : spans :\n", repr("\n".join(span.text for span in spans)), file=sys.stderr)
    if str(cli.output) == 'stdout':
        print("\n".join(span.text for span in spans))
    else:
        write_flattened_output(spans, cli.output)
    return 0

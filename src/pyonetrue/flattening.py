import sys
from pathlib import Path
import importlib.util
from dataclasses import dataclass, field
from typing import Optional, List, Union

from .extract_ast import extract_spans, Span
from .normalize_imports import normalize_imports

DEBUG = False

@dataclass
class FlatteningContext:

    package_path       : Union[Path, str]
    package_name       : str                           = field(init=False)
    type               : str                           = field(init=False)
    main_py            : tuple[str, list[Span]]        = field(init=False)
    module_spans       : list[tuple[str, list[Span]]]  = field(init=False)
    guard_sources      : dict[str, list[Span]]         = field(init=False)

    def __post_init__(self):
        if not self.package_path:
            raise ValueError("package 'package_path' cannot be empty (None, '', etc.)")
        self.module_spans = []
        self.guard_sources = {}
        self.main_py = (None, [])
        # Resolve package_path to file, dir, or package name
        path = Path(self.package_path)
        if DEBUG: print(f"DEBUG: Resolved path = {path}", file=sys.stderr)
        if path.exists():
            if path.is_dir():
                self.type = "dir"
                self.package_name = path.name
            elif path.is_file():
                self.type = "file"
                self.package_name = path.stem
            else:
                raise ValueError(f"input path '{self.package_path}' exists but is neither a file nor a directory")
        else:
            if DEBUG: print("DEBUG: package_path not   found as file/dir, trying as package name", file=sys.stderr)
            spec = importlib.util.find_spec(self.package_path)
            if spec and spec.submodule_search_locations:
                path = Path(spec.submodule_search_locations[0])
                self.package_name = path.name
                self.type = "name"
            else:
                raise ValueError(f"Cannot infer project package name from {self.package_path!r}")

        self.package_path = path

        if DEBUG: print(f"DEBUG: package_path = {self.package_path}", file=sys.stderr)
        if DEBUG: print(f"DEBUG: package_name = {self.package_name}", file=sys.stderr)

    def new_module(self, path: Path) -> "FlatteningModule":
        return FlatteningModule(self, path)


    def add_module(self, obj: Union[str, Path, "FlatteningModule"]) -> None:
        if not obj:
            raise ValueError("module 'path' cannot be empty (None, '', etc.)")
        if isinstance(obj, FlatteningModule):
            fm = obj
        elif isinstance(obj, (Path, str)):
            fm = FlatteningModule(self, Path(obj))
        else:
            raise ValueError(f"Invalid module path: {obj} -- must be str, Path, or FlatteningModule")

        if DEBUG: print(f"\nDEBUG: Adding module {fm.module = } from {fm.path = }", file=sys.stderr)

        spans = extract_spans(fm.path)
        if DEBUG: print("DEBUG add_module : spans :\n"+"\n".join(span.text for span in spans), file=sys.stderr)
        self.module_spans.append((fm.module, spans))
        for span in spans:
            if span.kind == 'main_guard':
                self.guard_sources.setdefault(fm.module, []).append(span)
        if fm.module.endswith("__main__"):
            self.main_py = (fm.module, spans)
            if DEBUG: print("DEBUG add_module : main spans :\n"+"\n".join(span.text for span in spans), file=sys.stderr)

    def discover_modules(self, includes=None, excludes=None, *, no_cli=False, main_from=None) -> None:

        # Normalize excludes/includes lists (if provided)
        if excludes:
            excludes = normalize_module_names(self.package_name, excludes)
            if includes:
                includes = normalize_module_names(self.package_name, includes)
            else:
                includes = []
        else:
            excludes = includes = []

        if self.package_path.is_file():
            self.add_module(self.package_path)
            return

        path = Path(self.package_path)

        if self.package_path.is_file():
            self.add_module(self.package_path)
            return

        if DEBUG: print(f"\nDEBUG: Discovering modules in {self.package_path = }", file=sys.stderr)

        if path.is_file():
            self.add_module(path)
            return

        # Determine exactly which __main__.py (if any) we are allowed to accept
        if no_cli:
            allowed_main = None
        elif main_from:
            allowed_main = normalize_a_module_name(main_from, self.package_name)
            if not allowed_main.endswith(".__main__"):
                allowed_main = allowed_main + ".__main__"
        else:
            allowed_main = self.package_name + ".__main__"

        if DEBUG: print(f"DEBUG: Discover - {allowed_main = }", file=sys.stderr)

        for subpath in path.rglob('*.py'):
            relpath = subpath.relative_to(path)
            dotted = str(relpath.with_suffix('')).replace('/', '.').replace('\\', '.')
            if dotted.endswith(".__init__"):
                dotted = dotted.rsplit(".", 1)[0]

            full_mod = normalize_a_module_name(dotted, self.package_name)

            if dotted_member_of(full_mod, excludes):
                if not dotted_member_of(full_mod, includes):
                    if DEBUG: print(f"DEBUG: Discover - excluded - skipping module {full_mod = }, from {subpath = }", file=sys.stderr)
                    continue

            if full_mod.endswith(".__main__"):
                if allowed_main is None:
                    if DEBUG: print(f"DEBUG: Discover - no cli - skipping module {full_mod = }, from {subpath = }", file=sys.stderr)
                    continue  # no_cli active, skip all __main__.py
                if allowed_main and full_mod != allowed_main:
                    if DEBUG: print(f"DEBUG: Discover - wrong cli - skipping module {full_mod = }, from {subpath = }", file=sys.stderr)
                    continue  # only allow exactly the requested __main__.py
                self.main_py = full_mod

            self.add_module(subpath)

    def get_final_output_spans(
        self,
        *,
        include_all_guards: bool = False,
        include_guards: Optional[List[str]] = None,
        main_from: Optional[str] = None,
        no_cli: bool = False,
        ignore_clashes: bool = False,
    ) -> list[Span]:
        (main_module, main_spans) = self.main_py
        # 3) Now walk only the non-__main__ modules
        import_spans: list[Span] = [s for s in main_spans if s.kind == "import"]
        guard_spans: list[Span] = []
        other_spans: list[Span] = []

        # If you still need to normalize include_guards to fully-qualified names, do it here
        if include_guards:
            include_guards = [ normalize_a_module_name(mod, self.package_name) 
                              for mod in include_guards ]

        # Identify the retained __all__ span (if any), only from the root module
        retained_all = None
        for module, spans in self.module_spans:
            if module == self.package_name:
                for i, span in enumerate(spans):
                    if span.kind == "logic" and span.text.strip().startswith("__all__"):
                        retained_all = span
                        break

        for module, spans in self.module_spans:
            # skip every __main__.py except the one we chose
            if module == main_module:
                continue

            for span in spans:
                if span.kind == "import":
                    import_spans.append(span)
                elif span.kind == "main_guard":
                    if include_all_guards or (include_guards and module in include_guards):
                        guard_spans.append(span)
                elif span.kind == "logic" and span.text.strip().startswith("__all__"):
                    continue
                else:
                    other_spans.append(span)

        # 4) Normalize imports once, then assemble final output
        import_spans, import_symbols = normalize_imports(
            package_name=self.package_name,
            import_spans=import_spans )

        simple: list[Span] = [retained_all] if retained_all else []
        simple.extend(other_spans)
        simple.extend(guard_spans)

        blank_line = Span(kind="blank", text="\n")
        body: list[Span] = []
        for span in simple:
            body.extend([span, blank_line])

        output: list[Span] = list(import_spans)
        output.extend(body)

        # 5) Finally, append the __main__.py body
        #    (but strip out any import spans since those have already been
        #     processed by normalize_imports)
        output.extend([s for s in main_spans if s.kind != "import"])

        # 6) Clash‐detection as before
        if not ignore_clashes:
            seen = set(import_symbols)
            for span in output:
                if span.kind in ("function", "class"):
                    header = span.text.lstrip()
                    if header.startswith("def "):
                        name = header[4:].split("(", 1)[0].strip()
                    elif header.startswith("class "):
                        name = header[6:].split("(", 1)[0].strip()
                    else:
                        continue
                    if name in seen:
                        raise Exception(f"Duplicate top-level name detected: {name}")
                    seen.add(name)

        return output


class FlatteningModule:

    __slots__ = ("module", "path")

    def __init__(self, ctx : FlatteningContext, path: Path):
        if not path.is_file():
            raise ValueError(f"FlatteningModule must be created from a file: {path}")

        try:
            relpath = path.relative_to(ctx.package_path)
        except ValueError:
            raise ValueError(f"Path {path} is not inside package root {ctx.package_path}")

        if relpath == Path('.'):
            relpath = Path(ctx.package_path.name)
        if relpath.name == "__init__.py":
            self.module = ctx.package_name
        else:
            mod_suffix = str(relpath.with_suffix('')).replace('/', '.')
            self.module = ctx.package_name + "." + mod_suffix

        self.path = path

def dotted_member_of(dotted: str, module_list: list[str]) -> bool:
    if not module_list:
        return False
    for module in module_list:
        if dotted_of_module(module, dotted):
            return True
    return False

# A simple function to check if a module name matches a dotted name
# (e.g. "foo.bar" matches "foo.bar.baz" and "foo.bar")
def dotted_of_module(module: str, dotted: str) -> bool:
    if dotted == module:
        return True
    if dotted.startswith(module + "."):
        return True
    return False

def normalize_a_module_name(mod: str, package_name: str) -> str:
    if mod.startswith(package_name + ".") or mod == package_name:
        return mod
    else:
        return package_name + "." + mod.lstrip('.')

def normalize_module_names(
    package_name: str,
    module_names: Union[str, list[str]]
) -> list[str]:
    if isinstance(module_names, str):
        module_names = [normalize_a_module_name(module_names, package_name)]
    if not isinstance(module_names, list):
        raise ValueError(f"module_names must be str or list of str, not {type(module_names)}")
    return [normalize_a_module_name(mod, package_name) for mod in module_names]

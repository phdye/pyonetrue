import sys

import importlib.util
from dataclasses import dataclass, field
from typing import List, Union

from .extract_ast import extract_spans, Span
from .normalize_imports import normalize_imports
from .exceptions import (
    DuplicateNameError,
    FlatteningError,
    IncludeExcludeError,
    ModuleInferenceError,
    PathError,
)
try :
    from pathlib import Path
except ImportError:
    from .vendor.pathlib import Path

DEBUG = False

@dataclass
class FlatteningContext:

    package_path       : Union[Path, str]
    package_name       : str                           = ""
    main_py            : tuple[str, List[Span]]        = (None, [])
    module_spans       : List[tuple[str, List[Span]]]  = field(default_factory=list)
    guard_sources      : dict[str, List[Span]]         = field(default_factory=dict)

    # Discovery -- inclusion/exclusion
    module_only             : bool                          = False
    main_from          : List[str]                     = field(default_factory=list)
    exclude            : List[str]                     = field(default_factory=list)
    include            : List[str]                     = field(default_factory=list)

    # Conflict detection
    ignore_clashes     : bool                          = False

    # Output generation
    output             : str                           = "stdout"
    shebang            : str                           = "#!/usr/bin/env python3"
    guards_all         : bool                          = False
    guards_from        : List[str]                     = field(default_factory=list)
    entry_points       : List[str]                     = field(default_factory=list)

    def __post_init__(self):
        if not self.package_path:
            raise PathError("package_path cannot be empty")
        # Resolve package_path to file, dir, or package name
        path = Path(self.package_path)
        if DEBUG: print(f"DEBUG: Resolved path = {path}", file=sys.stderr)
        if path.exists():
            if path.is_dir():
                self.package_name = path.name
            elif path.is_file():
                self.package_name = path.stem
            else:
                raise PathError(f"input path '{self.package_path}' is not a file or directory")
        else:
            if DEBUG: print("DEBUG: package_path not found as file/dir, trying as package name", file=sys.stderr)
            spec = importlib.util.find_spec(self.package_path)
            if spec and spec.submodule_search_locations:
                path = Path(spec.submodule_search_locations[0])
                self.package_name = path.name
            else:
                raise ModuleInferenceError(f"cannot infer package name from '{self.package_path!r}'")

        self.package_path = path

        if DEBUG: print(f"DEBUG: package_path = {self.package_path}", file=sys.stderr)
        if DEBUG: print(f"DEBUG: package_name = {self.package_name}", file=sys.stderr)

        # Normalize excludes/includes lists to fully-qualified names (if provided)
        if self.exclude:
            if isinstance(self.exclude, str):
                self.exclude = self.exclude.split(",")
            self.exclude = normalize_module_names(self.package_name, self.exclude)
            if self.include:
                if isinstance(self.include, str):
                    self.include = self.include.split(",")
                self.include = normalize_module_names(self.package_name, self.include)
            else:
                self.include = []
            if DEBUG: print(f"DEBUG: exclude = {self.exclude}", file=sys.stderr)
            if DEBUG: print(f"DEBUG: include = {self.include}", file=sys.stderr)
        elif self.include:
            raise IncludeExcludeError("`include` flag require `exclude` to be set")

        # Normalize self.guards_from to fully-qualified names
        if self.guards_from:
            if isinstance(self.guards_from, str):
                self.guards_from = self.guards_from.split(",")
            self.guards_from = [ normalize_a_module_name(mod, self.package_name) 
                                 for mod in self.guards_from ]

    def new_module(self, path: Path) -> "FlatteningModule":
        return FlatteningModule(self, path)

    def add_module(self, obj: Union[str, Path, "FlatteningModule"]) -> None:
        if not obj:
            raise PathError("module path cannot be empty")
        if isinstance(obj, FlatteningModule):
            fm = obj
        elif isinstance(obj, (Path, str)):
            fm = FlatteningModule(self, Path(obj))
        else:
            raise PathError(f"Invalid module path: {obj} -- must be str, Path, or FlatteningModule")

        if DEBUG: print(f"\nDEBUG: Adding module {fm.module = } from {fm.path = }", file=sys.stderr)

        try:
            spans = extract_spans(fm.path)
        except Exception as e:
            raise FlatteningError(f"failed to extract spans from {fm.path}") from e
        if DEBUG: print("DEBUG add_module : spans :\n"+"\n".join(span.text for span in spans), file=sys.stderr)
        self.module_spans.append((fm.module, spans))

        for span in spans:
            if span.kind == 'main_guard':
                self.guard_sources.setdefault(fm.module, []).append(span)

        if fm.module.endswith("__main__"):
            self.main_py = (fm.module, spans)
            if DEBUG: print("DEBUG add_module : main spans :\n"+"\n".join(span.text for span in spans), file=sys.stderr)

    def discover_modules(self) -> None:

        if self.package_path.is_file():
            self.add_module(self.package_path)
            return

        path = Path(self.package_path)

        if path.is_file():
            self.add_module(path)
            return

        if DEBUG: print(f"\nDEBUG: Discovering modules in {self.package_path = }", file=sys.stderr)

        # Determine exactly which __main__.py (if any) we are allowed to accept
        if self.module_only:
            allowed_main = None
        elif self.main_from:
            allowed_main = normalize_a_module_name(self.main_from, self.package_name)
            if not allowed_main.endswith(".__main__"):
                allowed_main = allowed_main + ".__main__"
        else:
            allowed_main = self.package_name + ".__main__"

        if DEBUG: print(f"DEBUG: Discover - {allowed_main = }", file=sys.stderr)

        for subpath in sorted(path.rglob('*.py')):
            relpath = subpath.relative_to(path)
            dotted = str(relpath.with_suffix('')).replace('/', '.').replace('\\', '.')
            if dotted.endswith(".__init__"):
                dotted = dotted.rsplit(".", 1)[0]

            full_mod = normalize_a_module_name(dotted, self.package_name)

            if self.exclude and dotted_member_of(full_mod, self.exclude):
                if not (self.include and dotted_member_of(full_mod, self.include)):
                    if DEBUG: print(f"DEBUG: Discover - excluded - skipping module {full_mod = }, from {subpath = }", file=sys.stderr)
                    continue

            if full_mod.endswith(".__main__"):
                if allowed_main is None:
                    if DEBUG: print(f"DEBUG: Discover - no cli - skipping module {full_mod = }, from {subpath = }", file=sys.stderr)
                    continue  # module_only active, skip all __main__.py
                if allowed_main and full_mod != allowed_main:
                    if DEBUG: print(f"DEBUG: Discover - wrong cli - skipping module {full_mod = }, from {subpath = }", file=sys.stderr)
                    continue  # only allow exactly the requested __main__.py
                self.main_py = full_mod

            self.add_module(subpath)

    def gather_root_spans(self):
        docstring = None
        retained_all = None
        retained_imports = []
        retained_logic = []

        for mod, spans in self.module_spans:
            first_logic = True
            for s in spans:
                if docstring is None and first_logic and s.kind == "logic" and (
                    s.text.lstrip().startswith("\"\"\"") or s.text.lstrip().startswith("'''")
                ):
                    docstring = s
                    first_logic = False
                    continue
                first_logic = False

                if mod == self.package_name:
                    if s.kind == "__all__":
                        retained_all = s
                    elif s.kind == "import":
                        retained_imports.append(s)
                    elif s.kind == "main_guard":
                        pass
                    else:
                        retained_logic.append(s)
        return docstring, retained_all, retained_imports, retained_logic

    def gather_module_spans(self):
        non_root_spans = []

        main_mod, _ = self.main_py

        for mod, spans in self.module_spans:
            if mod == self.package_name or mod == main_mod:
                continue
            for s in spans:
                if s.kind != "main_guard":
                    non_root_spans.append(s)

        return non_root_spans

    def gather_main_guard_spans(self):
        result = []
        if self.guards_all:
            for spans in self.guard_sources.values():
                result.extend(spans)
        elif self.guards_from:
            for mod in self.guards_from:
                if mod in self.guard_sources:
                    result.extend(self.guard_sources[mod])
        return result

    def get_main_spans(self):
        main_mod, main_spans = self.main_py
        if not (main_mod and main_spans and not self.module_only):
            return []
        return [s for s in main_spans if s.kind != "import"]

    def normalize_and_assemble(self, imports, all_decl, logic, guards, main, docstring=None):
        future_imports = [s for s in imports if "from __future__" in s.text]
        regular_imports = [s for s in imports if s not in future_imports]

        regular_imports, import_symbols = normalize_imports(
            package_name=self.package_name,
            import_spans=regular_imports,
        )

        ordered = []
        blank_line = Span(kind="blank", text="\n")

        if docstring:
            ordered.append(docstring)
            ordered.append(blank_line)

        ordered.extend(future_imports)
        if future_imports:
            ordered.append(blank_line)

        ordered.extend(regular_imports)
        if regular_imports:
            ordered.append(blank_line)

        if all_decl:
            ordered.append(all_decl)
            ordered.append(blank_line)

        for s in logic + guards:
            ordered.append(s)
            ordered.append(blank_line)

        ordered.extend(main)

        return ordered, import_symbols

    def check_clashes(self, spans, import_symbols):
        if not self.ignore_clashes:
            seen = set(import_symbols)
            for span in spans:
                if span.kind in ("function", "class"):
                    header = span.text.lstrip()
                    if header.startswith("def "):
                        name = header[4:].split("(", 1)[0].strip()
                    elif header.startswith("class "):
                        name = header[6:].split("(", 1)[0].strip()
                    else:
                        continue
                    if name in seen:
                        raise DuplicateNameError(f"Duplicate top-level name: {name}")
                    seen.add(name)


    def get_final_output_spans(self):
        docstring, all_decl, root_imports, root_logic = self.gather_root_spans()
        module_spans = self.gather_module_spans()
        main_guards = self.gather_main_guard_spans()
        main_body = self.get_main_spans()

        imports = root_imports + [s for s in module_spans if s.kind == "import"]
        logic = root_logic + [s for s in module_spans if s.kind not in["import", "main_guard"]]

        spans, import_symbols = self.normalize_and_assemble(
            imports, all_decl, logic, main_guards, main_body, docstring
        )

        self.check_clashes(spans, import_symbols)
        return spans

class FlatteningModule:

    __slots__ = ("module", "path")

    def __init__(self, ctx : FlatteningContext, path: Path):
        if not path.is_file():
            raise PathError(f"FlatteningModule must be created from a file: {path}")

        try:
            relpath = path.relative_to(ctx.package_path)
        except ValueError:
            raise PathError(f"Path {path} is not inside package root {ctx.package_path}")

        if relpath == Path('.'):
            relpath = Path(ctx.package_path.name)
        if relpath.name == "__init__.py":
            self.module = ctx.package_name
        else:
            mod_suffix = str(relpath.with_suffix('')).replace('/', '.')
            self.module = ctx.package_name + "." + mod_suffix

        self.path = path

def dotted_member_of(dotted: str, module_list: List[str]) -> bool:
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

def normalize_a_module_name(module_name: str, package_name: str) -> str:
    if not isinstance(module_name, str):
        raise FlatteningError(f"module_name must be str, not {type(module_name)} : {module_name!r}")
    if module_name.startswith(package_name + ".") or module_name == package_name:
        return module_name
    else:
        return package_name + "." + module_name.lstrip('.')

def normalize_module_names(
    package_name: str,
    module_names: Union[str, List[str]]
) -> list[str]:
    if isinstance(module_names, str):
        module_names = [normalize_a_module_name(module_names, package_name)]
    if not isinstance(module_names, list):
        raise FlatteningError(f"module_names must be str or list of str, not {type(module_names)}")
    return [normalize_a_module_name(mod, package_name) for mod in module_names]

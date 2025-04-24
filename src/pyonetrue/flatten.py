from pathlib import Path
import importlib.util

def flatten_package_to_buffer(package_name):
    spec = importlib.util.find_spec(package_name)
    if spec is None or not spec.submodule_search_locations:
        raise ImportError(f"Cannot locate package: {package_name}")

    package_path = Path(spec.submodule_search_locations[0])
    sources = []

    for pyfile in sorted(package_path.rglob('*.py')):
        if pyfile.name == '__init__.py':
            continue
        rel_path = pyfile.relative_to(package_path)
        sources.append(f"# --- {rel_path} ---\n" + pyfile.read_text())

    return "\n\n".join(sources)

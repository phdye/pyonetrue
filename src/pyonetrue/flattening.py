import os
from cleanedit import analyze_source

class FlatteningContext:
    def __init__(self):
        self.module_spans = []
        self.main_py_imports = []
        self.main_py_body = []
        self.main_guard_block = []

    def add_module(self, path):
        base = os.path.basename(path)
        is_main = base == "__main__.py"
        with open(path, encoding="utf-8") as f:
            source = f.read()
        spans = analyze_source(source)

        print(f"DEBUG: Parsed spans from {path}:")
        for s in spans:
            print(f" - kind={s.kind!r}, text={s.text.strip()[:60]}")

        if is_main:
            self._handle_main_py(spans)
        else:
            self.module_spans.append((path, spans))

    def _handle_main_py(self, spans):
        for span in spans:
            if span.kind == "import":
                self.main_py_imports.append(span)
            else:
                self.main_py_body.append(span)

    def set_main_from(self, path):
        with open(path, encoding="utf-8") as f:
            source = f.read()
        spans = analyze_source(source)
        main_blocks = [
            s for s in spans
            if s.kind == "main_guard" or (s.kind == "if" and "__name__" in s.text and "'__main__'" in s.text)
        ]
        if len(main_blocks) > 1:
            raise ValueError(f"Multiple main guards found in {path}. Only one is allowed.")
        if not main_blocks:
            raise ValueError(f"No main guard found in {path}.")
        self.main_guard_block = main_blocks

    def get_all_imports(self):
        all_imports = []
        for _, spans in self.module_spans:
            all_imports.extend([s for s in spans if s.kind == "import"])
        all_imports.extend(self.main_py_imports)
        return all_imports

    def get_all_other_spans(self):
        ordered = []
        for path, spans in self.module_spans:
            print(f"DEBUG: Processing spans from {path}:")
            for s in spans:
                print(f" - kind={s.kind!r}, text={s.text.strip()[:40]}")
            ordered.extend([s for s in spans if s.kind not in ("import", "main_guard")])
        return ordered

    def get_final_output_spans(self):
        return self.get_all_imports() + self.get_all_other_spans() + self.main_guard_block + self.main_py_body

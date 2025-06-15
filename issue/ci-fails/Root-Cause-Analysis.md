# CI/local ordering mismatch

`pyonetrue` discovers every `.py` file in a package using
`Path.rglob('*.py')`.  The traversal order of `rglob` depends on the
underlying operating system and filesystem.  Continuous integration
and local runs therefore enumerate modules in a different order even
though the set of files is identical.  Because the flattening process
emits modules in the discovered order, the generated `pyonetrue.py`
can be different between CI and a developer's machine while having the
same byte length.

<u>Ludicrous Proposal</u>

One way to guarantee deterministic output, the discovery loop could iterate
over `sorted(path.rglob('*.py'))` so that modules are always processed
in lexical order regardless of platform.  This would ensure identical
flattened files both locally and in CI.

*This would not ensure that symbols are declared before they are used.*


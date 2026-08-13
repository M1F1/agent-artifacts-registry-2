# residual — the kernel

The dependency-free Python package behind the `residual-*` skills: the work
queue, the run directory, sharding, compiling, the gates, prompt rendering and
the HTML reports.

It ships **inside** the `using-residues` skill so that fetching skills gives you
something that runs. Every step skill finds it as `../using-residues/kernel`,
which holds in a git checkout and in an installed skills directory alike.

```sh
bin/residual steps          # nothing installed
bin/residual where          # which kernel and skills are in play
bin/residual-test           # kernel tests + every skill's own
pip install -e .            # optional: puts `residual` on your PATH
```

Python 3.11+ (for `tomllib`). No runtime, dev or test dependencies.

The procedure documentation lives in `../SKILL.md`; the framework's own README
is at the repository root.

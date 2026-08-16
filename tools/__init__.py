"""Shared tooling importable as `tools.<module>` from any pipeline.

This file exists so `from tools import ai_capacity` resolves STATICALLY, not
just at runtime via a sys.path insert. Without it the import works when the
code runs and looks like a phantom dependency to every checker -- including
this repo's own tools/defect_classes.py, whose whole job is catching imports
that will fail in production.
"""

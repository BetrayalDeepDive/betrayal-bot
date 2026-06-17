#!/usr/bin/env python3
"""
stage1_script.py — DISABLED
======================
This script has been REPLACED by master_pipeline.py

All 4 stages now run inside a single pipeline:
  video_pipeline/master_pipeline.py

This file is kept in the repo for reference only.
It will never be called by any workflow.

What replaced this file:
  Stage 1 — Script Generation is now handled inside master_pipeline.py
  as a sequential function within the same process.

Why we switched:
  The 4-stage pipeline passed data through GitHub Actions
  artifacts and inter-job output variables. This caused
  silent failures where stages were skipped without error.
  The single-job master pipeline has zero inter-job
  dependencies and cannot skip any stage.

DO NOT DELETE this file — it serves as documentation.
DO NOT RE-ENABLE this file — it will conflict with master.
"""

import sys

def main():
    print(f"============================================================")
    print(f"  stage1_script.py is DISABLED")
    print(f"  All pipeline stages run inside master_pipeline.py")
    print(f"  This file should never be called directly.")
    print(f"============================================================")
    sys.exit(0)

if __name__ == "__main__":
    main()

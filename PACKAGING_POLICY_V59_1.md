# Packaging policy — V59.1

- Root contains the current V59.1 release and runtime dependencies only.
- Historical release documentation/workbooks are stored under `previous_version/`.
- Python bytecode (`__pycache__`, `*.pyc`) is never distributed or hashed.
- `SHA256SUMS.txt` excludes itself and is generated after all current artifacts are finalized.
- `PACKAGE_MANIFEST.txt` lists distributable files only.

# Project maintenance instructions

## Versioning and changelog

- `VERSION.txt` is the authoritative project version and must contain one
  semantic version in `major.minor.patch` form.
- Every project change must update `CHANGELOG.md` under the resulting version.
- Increment the patch version for backward-compatible fixes and maintenance,
  the minor version for backward-compatible features, and the major version
  for incompatible changes.
- Keep the application version display sourced from `VERSION.txt`; do not
  duplicate a hard-coded version in Python.
- Run the complete test suite after changing either file.

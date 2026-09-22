# Tafel fitter maintenance

These instructions apply to this directory and its descendants.

The user requires a version number and a maintained changelog for every change
to this tool.

- For each task that changes source code, GUI behavior, dependencies, tests,
  documentation or maintained comparison scripts, update `tafel_version.py`
  and `CHANGELOG.md` in the same task. Consolidate related edits into one release
  entry per task rather than bumping for each individual file edit.
- Use MAJOR.MINOR.PATCH: PATCH for compatible fixes and documentation changes,
  MINOR for compatible new functionality, MAJOR for incompatible public behavior
  or data-format changes. Describe scientific/numerical changes explicitly.
- Add the new dated entry at the top of the changelog, describing what changed,
  why it matters and any compatibility or interpretation implications. Preserve
  previous entries; do not claim proposed features are implemented.
- Keep the current version in the README synchronized. The GUI and export code
  must import the central version rather than duplicating a version literal.
- Keep this adaptation's version distinct from upstream MEG-LBNL v1.51, whose
  attribution must remain intact.
- Generating analysis outputs without modifying the tool does not require a new
  release. Do not rewrite historical exports to give them a newer version.
- Run checks appropriate to the change and report the version and validation
  outcome to the user.

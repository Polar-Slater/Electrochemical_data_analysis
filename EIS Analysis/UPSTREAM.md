# Upstream provenance

Base: DearEIS 5.1.3, https://github.com/vyrjana/DearEIS

The complete `deareis` package source and packaged resources were copied from the
locally installed official 5.1.3 wheel. Cache/bytecode files were excluded. This
keeps required GUI license/changelog resources that are generated during upstream
packaging. Original author and license notices are retained. This is a customized
application, not an official DearEIS release.

Adapted upstream files:

- program/data_sets.py: toolbox text importer and native dialog; create project on demand.
- program/project.py: native project-open/save dialogs, remembered save location,
  and protection of the original project identity during Save As.
- gui/fitting.py: editable initial-parameter table, synchronized with circuit edits,
  fit settings, and reuse of fitted parameters; adjacent circuit-diagram tab.
- gui/program.py: application title, quick-open action on Home and File menu.
- gui/data_sets/__init__.py: clearer import button label.
- program/__init__.py: custom window title; omit automatic upstream release checks.
- gui/about.py: custom application version plus upstream attribution.
- arguments.py: custom application identity in command-line help.
- state.py and config/__init__.py: separate local settings and recovery directories.

Numerical APIs and result serialization are unchanged. Dependencies are pinned in
requirements.txt to the direct dependency versions used for this initial build.
Do not overwrite customized files when updating upstream; compare these changes
and rerun import, analysis and GUI checks.

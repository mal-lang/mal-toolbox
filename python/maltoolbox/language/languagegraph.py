"""MAL-Toolbox Language Graph functionality

`LanguageGraph` itself is implemented in Rust and exposed here via the
`maltoolbox._native` extension module - see PYTHON_BINDINGS_IMPLEMENTATION.md
at the repo root for the full rationale. This module only keeps the
pieces that have no native equivalent: `disaggregate_attack_step_full_name`
(a trivial string helper) and `load_language_graph_from_file`'s `.git`
URL branch (`language_graph_from_git_url` needs a live git clone at
runtime - explicitly out of scope for the Rust port, see
`PORTING_NOTES.md` §1).

The pure-Python original's `LanguageGraph.load_from_file` classmethod
*was* `load_language_graph_from_file` (it dispatched `.git`-suffixed
filenames to a clone-then-load path before falling through to the
mal/mar/yaml/json loader). The Rust-native `LanguageGraph.load_from_file`
staticmethod never got that `.git` dispatch ported, so any caller that
does `from maltoolbox._native import LanguageGraph` (directly, or via
`maltoolbox.language`'s re-export) and then calls
`LanguageGraph.load_from_file(git_url)` - e.g. mal-simulator's
`Scenario` loader - got `TypeError: Unknown file extension`. Rather than
require every such caller to route through
`load_language_graph_from_file` instead, we monkeypatch the native
staticmethod itself at import time below: `LanguageGraph.load_from_file`
now checks for a `.git` suffix first and only falls through to the
original native implementation otherwise. This keeps the fix in one
place and makes it transparent to every existing call site.
"""

from __future__ import annotations

import logging

from maltoolbox._native import LanguageGraph
from maltoolbox.file_utils import download_git_repo

logger = logging.getLogger(__name__)

_native_load_from_file = LanguageGraph.load_from_file


def disaggregate_attack_step_full_name(attack_step_full_name: str) -> list[str]:
    """From an attack step full name, get (asset_name, attack_step_name)"""
    return attack_step_full_name.split(':')


def language_graph_from_git_url(git_url: str) -> LanguageGraph:
    """Create a LanguageGraph from a git url pointing to MAL lang.

    The git repository contains a src/main/mal/main.mal
    which is the file to load as the MAL language specification.
    The git repo will be cloned to a local directory named ./.langs.

    Arguments:
    ---------
    git_url     -   the git url pointing to the MAL language specification

    """
    logger.info('Loading language graph from git url %s', git_url)

    dir = download_git_repo(git_url)
    mal_files = list(dir.rglob('*.mal'))

    if not mal_files:
        raise FileNotFoundError(
            'Execution failed: No .mal files found in the cloned repository.'
        )

    if len(mal_files) == 1:
        mal_file = mal_files[0]
    else:
        main_mal_files = [f for f in mal_files if f.name == 'main.mal']
        if main_mal_files:
            mal_file = main_mal_files[0]
        else:
            raise ValueError(
                'Execution failed: .mal files found but no main.mal file in the repository.'
            )

    return LanguageGraph.from_mal_spec(str(mal_file))


def _load_from_file_with_git_support(filename: str) -> LanguageGraph:
    """Create LanguageGraph from mal, mar, yaml, json or git url.

    Patched onto `LanguageGraph.load_from_file` below so every caller
    (direct native import or via this module) gets `.git` dispatch.
    """
    if filename.endswith('.git'):
        return language_graph_from_git_url(filename)
    return _native_load_from_file(filename)


LanguageGraph.load_from_file = staticmethod(_load_from_file_with_git_support)  # type: ignore[method-assign, assignment]


def load_language_graph_from_file(filename: str) -> LanguageGraph:
    """Create LanguageGraph from mal, mar, yaml, json or git url"""
    return LanguageGraph.load_from_file(filename)

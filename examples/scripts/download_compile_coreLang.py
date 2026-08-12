#!/usr/bin/env python3
"""Download coreLang from its git repository into /tmp and compile it into a .mar archive.

Usage:
    uv run script/download_compile_coreLang.py [--git-url URL] [--output PATH]
"""

import argparse
import subprocess
import tempfile
from pathlib import Path

from maltoolbox.language.languagegraph import LanguageGraph

CORELANG_GIT_URL = 'https://github.com/mal-lang/coreLang.git'


def clone_corelang(git_url: str) -> Path:
    """Shallow-clone coreLang into a fresh directory under /tmp."""
    repo_dir = Path(tempfile.mkdtemp(prefix='corelang-', dir='/tmp'))
    subprocess.run(
        ['git', 'clone', '--depth', '1', git_url, str(repo_dir)],
        check=True,
    )
    return repo_dir


def find_main_mal(repo_dir: Path) -> Path:
    """Find the main .mal file to use as the entrypoint of the MAL spec."""
    mal_files = list(repo_dir.rglob('*.mal'))
    if not mal_files:
        raise FileNotFoundError(f'No .mal files found in {repo_dir}')

    main_mal_files = [f for f in mal_files if f.name == 'main.mal']
    if main_mal_files:
        return main_mal_files[0]
    if len(mal_files) == 1:
        return mal_files[0]
    raise FileNotFoundError(
        f'Multiple .mal files found in {repo_dir} but none named main.mal'
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--git-url', default=CORELANG_GIT_URL, help='coreLang git repository URL'
    )
    parser.add_argument(
        '--output',
        default='org.mal-lang.coreLang.mar',
        help='Path to write the compiled .mar archive',
    )
    args = parser.parse_args()

    repo_dir = clone_corelang(args.git_url)
    print(f'Cloned coreLang into {repo_dir}')

    mal_file = find_main_mal(repo_dir)
    print(f'Compiling {mal_file}')

    lang_graph = LanguageGraph.load_from_file(str(mal_file))
    lang_graph.save_to_file(args.output)
    print(f'Wrote compiled language to {args.output}')


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Profile AttackGraph.partially_regenerate_graph with cProfile.

Grows a coreLang model by repeatedly adding/removing Hardware+Application+
Data units, one partially_regenerate_graph call per unit.

Usage:
    uv run scripts/profile_partial_regeneration.py [--hosts N] [--cycles N] [--output PATH]
"""

from __future__ import annotations

import argparse
import cProfile
import pstats
from pathlib import Path

from maltoolbox.attackgraph import AttackGraph
from maltoolbox.language import LanguageGraph
from maltoolbox.model import Model, ModelAsset

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LANG = REPO_ROOT / 'tests' / 'testdata' / 'org.mal-lang.coreLang-1.0.0.mar'
DEFAULT_OUTPUT_DIR = REPO_ROOT / 'prof'

Unit = tuple[ModelAsset, ModelAsset, ModelAsset]


def add_unit(model: Model, network: ModelAsset, index: int) -> tuple[
    set[ModelAsset], set[tuple[ModelAsset, str, ModelAsset]], Unit
]:
    """Create one Hardware+Application+Data unit attached to `network`."""
    app = model.add_asset(asset_type='Application', name=f'App{index}')
    hw = model.add_asset(asset_type='Hardware', name=f'Host{index}')
    data = model.add_asset(asset_type='Data', name=f'Data{index}')

    network.add_associated_assets('applications', {app})
    hw.add_associated_assets('sysExecutedApps', {app})
    app.add_associated_assets('containedData', {data})

    new_assets = {app, hw, data}
    new_associations = {
        (network, 'applications', app),
        (hw, 'sysExecutedApps', app),
        (app, 'containedData', data),
    }
    return new_assets, new_associations, (app, hw, data)


def remove_unit(model: Model, network: ModelAsset, unit: Unit) -> tuple[
    set[ModelAsset], set[tuple[ModelAsset, str, ModelAsset]]
]:
    """Undo `add_unit`, returning the removed assets/associations."""
    app, hw, data = unit
    network.remove_associated_assets('applications', {app})
    hw.remove_associated_assets('sysExecutedApps', {app})
    app.remove_associated_assets('containedData', {data})

    removed_associations = {
        (network, 'applications', app),
        (hw, 'sysExecutedApps', app),
        (app, 'containedData', data),
    }
    removed_assets = {app, hw, data}
    model.remove_asset(app)
    model.remove_asset(hw)
    model.remove_asset(data)
    return removed_assets, removed_associations


def run_cycle(model: Model, network: ModelAsset, ag: AttackGraph, num_units: int) -> None:
    """Incrementally add `num_units` units then tear them all back down,
    driving every change through `partially_regenerate_graph`."""
    units: list[Unit] = []
    for i in range(num_units):
        new_assets, new_associations, unit = add_unit(model, network, i)
        ag.partially_regenerate_graph(
            new_assets=new_assets, new_associations=new_associations
        )
        units.append(unit)

    for unit in reversed(units):
        removed_assets, removed_associations = remove_unit(model, network, unit)
        ag.partially_regenerate_graph(
            removed_assets=removed_assets, removed_associations=removed_associations
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--hosts', type=int, default=200,
        help='Number of Hardware/Application/Data units to add then remove '
             'per cycle (default: 200)',
    )
    parser.add_argument(
        '--cycles', type=int, default=1,
        help='Number of add/remove cycles to run inside the profiled region '
             '(default: 1)',
    )
    parser.add_argument(
        '--lang', type=Path, default=DEFAULT_LANG,
        help='Path to a .mal or .mar language spec (default: coreLang test fixture)',
    )
    parser.add_argument(
        '--output', type=Path, default=None,
        help='Path to write the .prof file '
             '(default: prof/partial_regeneration_<hosts>x<cycles>.prof)',
    )
    parser.add_argument(
        '--top', type=int, default=20,
        help='Number of rows to print from the cumulative-time summary '
             '(default: 20, 0 to disable)',
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    output = args.output or (
        DEFAULT_OUTPUT_DIR / f'partial_regeneration_{args.hosts}x{args.cycles}.prof'
    )
    output.parent.mkdir(parents=True, exist_ok=True)

    print(f'Loading language graph from {args.lang}')
    lang_graph = LanguageGraph.load_from_file(str(args.lang))

    model = Model('Profiling Model', lang_graph)
    network = model.add_asset(asset_type='Network', name='CorpNet')
    ag = AttackGraph(lang_graph=lang_graph, model=model)

    profiler = cProfile.Profile()
    profiler.enable()
    for _ in range(args.cycles):
        run_cycle(model, network, ag, args.hosts)
    profiler.disable()

    profiler.dump_stats(str(output))
    print(f'Wrote profile to {output}')

    if args.top > 0:
        stats = pstats.Stats(profiler)
        stats.sort_stats('cumulative')
        stats.print_stats(args.top)


if __name__ == '__main__':
    main()

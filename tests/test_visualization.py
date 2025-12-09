from pathlib import Path
from maltoolbox.model import Model
from maltoolbox.attackgraph import AttackGraph
from maltoolbox.visualization import render_attack_graph, render_model


# -------------------------------------------------------------------
# 1. Tests when PATH is a directory
# -------------------------------------------------------------------

def test_render_model_to_dir(example_model: Model, tmp_path: Path):
    """Ensure the model renders to directory with .gv and .gv.pdf."""
    outdir = tmp_path

    render_model(example_model, path=outdir, view=False)

    expected_pdf = outdir / f"{example_model.name}.gv.pdf"
    expected_gv = outdir / f"{example_model.name}.gv"

    assert expected_pdf.exists()
    assert expected_gv.exists()


def test_render_attack_graph_to_dir(example_attackgraph: AttackGraph, tmp_path: Path):
    """Ensure the attack graph renders to directory with .gv and .gv.pdf."""
    outdir = tmp_path
    assert example_attackgraph.model, "Need model"
    name = example_attackgraph.model.name + "-attack_graph"

    render_attack_graph(example_attackgraph, path=outdir, view=False)

    expected_pdf = outdir / f"{name}.gv.pdf"
    expected_gv = outdir / f"{name}.gv"

    assert expected_pdf.exists()
    assert expected_gv.exists()


# -------------------------------------------------------------------
# 2. Tests when PATH is a specific file path
# -------------------------------------------------------------------

def test_render_model_to_exact_file(example_model: Model, tmp_path: Path):
    """Ensure rendering works when given an explicit file path."""
    out_file = tmp_path / "custom_output.gv"  # user-specified file name

    render_model(example_model, path=out_file, view=False)

    expected_pdf = tmp_path / "custom_output.gv.pdf"
    expected_gv = tmp_path / "custom_output.gv"

    assert expected_pdf.exists()
    assert expected_gv.exists()


def test_render_attack_graph_to_exact_file(example_attackgraph: AttackGraph, tmp_path: Path):
    """Ensure attack graph renders to an exact file path."""
    out_file = tmp_path / "attack_output.gv"

    render_attack_graph(example_attackgraph, path=out_file, view=False)

    expected_pdf = tmp_path / "attack_output.gv.pdf"
    expected_gv = tmp_path / "attack_output.gv"

    assert expected_pdf.exists()
    assert expected_gv.exists()


# -------------------------------------------------------------------
# 3. Tests when PATH is None (default behavior)
# -------------------------------------------------------------------

def test_render_model_no_path(example_model: Model, tmp_path: Path, monkeypatch):
    """
    Ensure rendering works with path=None.
    We monkeypatch cwd so files go into tmp_path.
    """
    monkeypatch.chdir(tmp_path)

    render_model(example_model, path=None, view=False)

    expected_pdf = tmp_path / f"{example_model.name}.gv.pdf"
    expected_gv = tmp_path / f"{example_model.name}.gv"

    assert expected_pdf.exists()
    assert expected_gv.exists()


def test_render_attack_graph_no_path(example_attackgraph: AttackGraph, tmp_path: Path, monkeypatch):
    """
    Ensure rendering attack graph works with no path.
    Files should appear in the working directory.
    """
    monkeypatch.chdir(tmp_path)
    assert example_attackgraph.model, "Need model"
    name = example_attackgraph.model.name + "-attack_graph"

    render_attack_graph(example_attackgraph, path=None, view=False)

    expected_pdf = tmp_path / f"{name}.gv.pdf"
    expected_gv = tmp_path / f"{name}.gv"

    assert expected_pdf.exists()
    assert expected_gv.exists()

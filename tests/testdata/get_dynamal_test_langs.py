"""Fetch the DynaMAL test language specifications into tests/testdata.

Clones https://gitlab.com/kth-ssas/dynamal-group/dynamaltestlangs and copies
every ``*.dmal`` file it contains into this directory (flattened by
filename), so they can be committed as test fixtures.

Usage:
    python tests/testdata/get_dynamal_test_langs.py
"""
import re
import shutil
from pathlib import Path

from maltoolbox.file_utils import download_git_repo

DYNAMAL_TEST_LANGS_URL = (
    "https://gitlab.com/kth-ssas/dynamal-group/dynamaltestlangs.git"
)
TESTDATA_DIR = Path(__file__).resolve().parent
test_lang_dir = TESTDATA_DIR / "dynamal_test_langs"
test_lang_dir.mkdir(exist_ok=True)

version_pattern = re.compile(r"#version:\s*")
id_pattern = re.compile(r"#id:\s*")
def fix_version_id(lang_path: Path):
    lang_text = lang_path.read_text()
    prepend_text = ""
    id_match = bool(id_pattern.search(lang_text))
    version_match = bool(version_pattern.search(lang_text))
    if not id_match:
        prepend_text += "#id: \"" + lang_path.stem + "\"\n"

    if not version_match:
        prepend_text += "#version: \"0.1.0\"\n"

    if len(prepend_text) > 0:
        if id_match and version_match:
            prepend_text += "\n"
        lang_path.write_text(prepend_text + lang_text)


def add_credit_disclaimer(lang_path: Path) -> None:
    lang_text = lang_path.read_text()
    disclaimer = (
        "/**\n"
        f"  * Created by Viktor Engström\n"
        f"  * Repo: {DYNAMAL_TEST_LANGS_URL}\n"
        f"  * Converted by Sandor Berglund\n"
        "  */\n\n"
    )
    lang_path.write_text(disclaimer + lang_text)


def fix_category(lang_path: Path):
    lang_text = lang_path.read_text()
    has_category = "category" in lang_text
    if not has_category:
        lines = lang_text.splitlines(keepends=True)

        insert_idx = 0
        while insert_idx < len(lines) and lines[insert_idx].startswith("#"):
            insert_idx += 1
        lines.insert(insert_idx, f"category {lang_path.stem} {{\n")

        assoc_idx = next(
            (i for i, line in enumerate(lines)
             if line.lstrip().startswith("associations")),
            None,
        )
        body_end = assoc_idx if assoc_idx is not None else len(lines)
        for i in range(insert_idx + 1, body_end):
            if lines[i].strip():
                lines[i] = "\t" + lines[i]

        if assoc_idx is not None:
            lines.insert(assoc_idx, "}\n\n")
        else:
            lines.append("}\n")

        lang_path.write_text("".join(lines))

step_start_pattern = re.compile(r"^\s*(\||&|#|!E(?![A-Za-z0-9_])|E(?![A-Za-z0-9_]))")
stray_step_arrow_pattern = re.compile(
    r"^(\s*[|&#]\s*[A-Za-z_][A-Za-z0-9_]*)\s*>(\s*(//.*)?)$"
)
def fix_stray_step_arrow(lang_path: Path):
    """Drop the bare trailing `>` some step declarations have (e.g.
    `| plantTree >`) — it isn't part of the current attack_step grammar
    and causes a syntax error."""
    lines = lang_path.read_text().splitlines(keepends=True)

    fixed_lines = []
    for line in lines:
        eol = "\n" if line.endswith("\n") else ""
        content = line[:-1] if eol else line
        match = stray_step_arrow_pattern.match(content)
        if match:
            line = f"{match.group(1)}{match.group(2)}{eol}"
        fixed_lines.append(line)

    lang_path.write_text("".join(fixed_lines))


star_traversal_pattern = re.compile(r"(?:\*[A-Za-z_][A-Za-z0-9_]*)+[,.(\s*/)]")
star_field_pattern = re.compile(r"\*([A-Za-z_][A-Za-z0-9_]*)")
def fix_star_traversal_suffix(lang_path: Path):
    """Convert the old dmal prefix transitive marker `*field` into the
    postfix `field*` form the current grammar expects wherever it directly
    precedes a `,` or `.` (e.g. `*sub*super.` -> `sub*.super*.`)."""
    lang_text = lang_path.read_text()

    def replace(match: re.Match) -> str:
        chain, delim = match.group(0)[:-1], match.group(0)[-1]
        fields = star_field_pattern.findall(chain)
        return ".".join(f"{field}*" for field in fields) + delim

    lang_path.write_text(star_traversal_pattern.sub(replace, lang_text))


reaches_pattern = re.compile(r"^(\s*)->\s*(.*)$")
def fix_double_reaching(lang_path: Path):
    """Merge repeated `-> target` lines within a single attack step into
    one comma-separated clause, keeping only the first `->` and dropping
    any exact-duplicate targets."""
    lines = lang_path.read_text().splitlines(keepends=True)

    seen_targets: set[str] = set()
    last_line_idx: int | None = None
    kept_lines: list[str] = []
    for line in lines:
        if step_start_pattern.match(line):
            seen_targets = set()
            last_line_idx = None

        eol = "\n" if line.endswith("\n") else ""
        content = line[:-1] if eol else line
        match = reaches_pattern.match(content)
        if match:
            indent, rest = match.groups()
            target = re.sub(r"//.*", "", rest).strip().rstrip(",")
            if target in seen_targets:
                continue
            seen_targets.add(target)

            if last_line_idx is None:
                kept_lines.append(line)
            else:
                prev_content = kept_lines[last_line_idx].rstrip("\n")
                if not prev_content.endswith(","):
                    prev_content += ","
                kept_lines[last_line_idx] = prev_content + "\n"
                kept_lines.append(f"{indent}{rest}{eol}")
            last_line_idx = len(kept_lines) - 1
            continue

        kept_lines.append(line)

    lang_path.write_text("".join(kept_lines))


dynamic_op_pattern = re.compile(r"^(\s*)(\+?[AR]>)\s*(.*)$")
def fix_double_dynamic_operations(lang_path: Path):
    """Merge repeated `A>`/`R>`/`+A>`/`+R>` clauses within a single attack
    step into one comma-separated clause, keeping only the first operator."""
    lines = lang_path.read_text().splitlines(keepends=True)

    last_line_idx: dict[str, int] = {}
    kept_lines: list[str] = []
    for line in lines:
        if step_start_pattern.match(line):
            last_line_idx = {}

        eol = "\n" if line.endswith("\n") else ""
        content = line[:-1] if eol else line
        match = dynamic_op_pattern.match(content)
        if match:
            indent, op, rest = match.groups()
            if op in last_line_idx:
                prev_idx = last_line_idx[op]
                prev_content = kept_lines[prev_idx].rstrip("\n")
                if not prev_content.endswith(","):
                    prev_content += ","
                kept_lines[prev_idx] = prev_content + "\n"
                kept_lines.append(f"{indent}{rest}{eol}")
            else:
                kept_lines.append(line)
                last_line_idx[op] = len(kept_lines) - 1
            continue

        kept_lines.append(line)

    lang_path.write_text("".join(kept_lines))

def fix_intDynamicTestLang13(lang_path: Path):
    """Fix the `intDynamicTestLang13` test language, which has a syntax error
    in its `category` declaration (missing `{`)."""
    lang_text = lang_path.read_text()
    new_lang_text = lang_text.replace("""// {top} -> {middle, bottom} -> reached
	| moveTopThenBottom
		-> super*sub.files.reached""", "", 1)
    new_lang_text = new_lang_text.replace("""// {middle, top}
	| addBottomToTopRight
		A> self / *super.files""", "", 1)
    new_lang_text = new_lang_text.replace("*sub*super*sub.reached", "*sub.*super.*sub.files.reached")
    lang_path.write_text(new_lang_text)
    

def copy_test_langs(dir_name: str, repo_dir: Path) -> None:
    sub_dir = test_lang_dir / dir_name
    sub_dir.mkdir(exist_ok=True)
    for copy_path in (repo_dir / dir_name).rglob("*.dmal"):
        lang_path = (sub_dir / copy_path.name).with_suffix(".mal")
        shutil.copy(copy_path, lang_path)
        if copy_path.name == "intDynamicTestLang13.dmal":
            fix_intDynamicTestLang13(lang_path)
        fix_version_id(lang_path)
        fix_category(lang_path)
        fix_double_reaching(lang_path)
        fix_double_dynamic_operations(lang_path)
        fix_stray_step_arrow(lang_path)
        fix_star_traversal_suffix(lang_path)
        add_credit_disclaimer(lang_path)

def main() -> None:
    repo_dir = download_git_repo(DYNAMAL_TEST_LANGS_URL)

    copy_test_langs("basic", repo_dir)
    copy_test_langs("intermediate", repo_dir)
    copy_test_langs("advanced", repo_dir)


if __name__ == "__main__":
    main()

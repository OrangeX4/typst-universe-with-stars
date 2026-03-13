#!/usr/bin/env python3
"""
Build and force-push the readmes-in-typst-universe repository content.

After fetch_packages.py has run, this script:
  1. Collects the latest-version typst.toml for every package into metadata/
  2. Collects the latest-version README.md for every package into readmes/
  3. Generates a README.md that summarises all packages sorted by star count,
     with AI-wiki guidance badges and instructions.
  4. Force-pushes the result to https://github.com/OrangeX4/readmes-in-typst-universe
     (main branch) so that the repository always reflects the current state
     without accumulating history.

Required environment variable:
  READMES_PAT – GitHub Personal Access Token (classic) with ``repo`` scope,
                or a fine-grained token with "Contents: Read and write" access
                on the OrangeX4/readmes-in-typst-universe repository.

Optional environment variable:
  GITHUB_ACTOR – used as the git commit author name (defaults to "github-actions").
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

CLONE_DIR = "/tmp/typst-packages"
REPO_ROOT = Path(__file__).parent.parent
TARGET_REPO = "https://github.com/OrangeX4/readmes-in-typst-universe"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

STAR_TIERS = [
    (1000, None,  "1000+ ★"),
    (500,  1000,  "500 – 1000 ★"),
    (400,  500,   "400 – 500 ★"),
    (300,  400,   "300 – 400 ★"),
    (200,  300,   "200 – 300 ★"),
    (100,  200,   "100 – 200 ★"),
    (50,   100,   "50 – 100 ★"),
    (0,    50,    "0 – 50 ★"),
]

ZREAD_BADGE = (
    "https://img.shields.io/badge/Ask_Zread-_.svg"
    "?style=flat&color=00b0aa&labelColor=000000"
    "&logo=data%3Aimage%2Fsvg%2Bxml%3Bbase64%2CPHN2ZyB3aWR0aD0iMTYiIGhlaWdodD0iMTYiIHZpZXdCb3g9IjAgMCAxNiAxNiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTQuOTYxNTYgMS42MDAxSDIuMjQxNTZDMS44ODgxIDEuNjAwMSAxLjYwMTU2IDEuODg2NjQgMS42MDE1NiAyLjI0MDFWNC45NjAxQzEuNjAxNTYgNS4zMTM1NiAxLjg4ODEgNS42MDAxIDIuMjQxNTYgNS42MDAxSDQuOTYxNTZDNS4zMTUwMiA1LjYwMDEgNS42MDE1NiA1LjMxMzU2IDUuNjAxNTYgNC45NjAxVjIuMjQwMUM1LjYwMTU2IDEuODg2NjQgNS4zMTUwMiAxLjYwMDEgNC45NjE1NiAxLjYwMDFaIiBmaWxsPSIjZmZmIi8%2BCjxwYXRoIGQ9Ik00Ljk2MTU2IDEwLjM5OTlIMi4yNDE1NkMxLjg4ODEgMTAuMzk5OSAxLjYwMTU2IDEwLjY4NjQgMS42MDE1NiAxMS4wMzk5VjEzLjc1OTlDMS42MDE1NiAxNC4xMTM0IDEuODg4MSAxNC4zOTk5IDIuMjQxNTYgMTQuMzk5OUg0Ljk2MTU2QzUuMzE1MDIgMTQuMzk5OSA1LjYwMTU2IDE0LjExMzQgNS42MDE1NiAxMy43NTk5VjExLjAzOTlDNS42MDE1NiAxMC42ODY0IDUuMzE1MDIgMTAuMzk5OSA0Ljk2MTU2IDEwLjM5OTlaIiBmaWxsPSIjZmZmIi8%2BCjxwYXRoIGQ9Ik0xMy43NTg0IDEuNjAwMUgxMS4wMzg0QzEwLjY4NSAxLjYwMDEgMTAuMzk4NCAxLjg4NjY0IDEwLjM5ODQgMi4yNDAxVjQuOTYwMUMxMC4zOTg0IDUuMzEzNTYgMTAuNjg1IDUuNjAwMSAxMS4wMzg0IDUuNjAwMUgxMy43NTg0QzE0LjExMTkgNS42MDAxIDE0LjM5ODQgNS4zMTM1NiAxNC4zOTg0IDQuOTYwMVYyLjI0MDFDMTQuMzk4NCAxLjg4NjY0IDE0LjExMTkgMS42MDAxIDEzLjc1ODQgMS42MDAxWiIgZmlsbD0iI2ZmZiIvPgo8cGF0aCBkPSJNNCAxMkwxMiA0TDQgMTJaIiBmaWxsPSIjZmZmIi8%2BCjxwYXRoIGQ9Ik00IDEyTDEyIDQiIHN0cm9rZT0iI2ZmZiIgc3Ryb2tlLXdpZHRoPSIxLjUiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIvPgo8L3N2Zz4K"
    "&logoColor=ffffff"
)


def _fmt_date(iso: str | None) -> str:
    """Return a compact date string (YYYY-MM-DD) or 'N/A'."""
    if not iso:
        return "N/A"
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        return iso[:10] if len(iso) >= 10 else iso


def _stars_str(stars: int | None) -> str:
    return f"{stars:,}" if stars is not None else "N/A"


def _pkg_row(pkg: dict) -> str:
    """Format one package as a Markdown table row."""
    kind = "template" if pkg.get("is_template") else "package"
    repo = pkg.get("repository") or pkg.get("homepage") or "N/A"
    cats = ", ".join(pkg.get("categories") or []) or "N/A"
    kws = ", ".join(pkg.get("keywords") or []) or "N/A"
    return (
        f"| {pkg['name']} "
        f"| {pkg.get('description', '') or ''} "
        f"| {pkg.get('version', '')} "
        f"| {_stars_str(pkg.get('stars'))} "
        f"| {_fmt_date(pkg.get('last_update'))} "
        f"| {kind} "
        f"| {repo} "
        f"| {cats} "
        f"| {kws} |"
    )


TABLE_HEADER = (
    "| Name | Description | Version | Stars | Last Update"
    " | Type | Repository | Categories | Keywords |\n"
    "|------|-------------|---------|-------|------------|"
    "------|------------|------------|----------|\n"
)


def _tier_label(stars: int | None) -> str:
    """Return the tier label for a package based on its star count."""
    s = stars if stars is not None else 0
    for lo, hi, label in STAR_TIERS:
        if hi is None:
            if s >= lo:
                return label
        else:
            if lo <= s < hi:
                return label
    return "0 – 50 ★"


def generate_readme(packages: list[dict], updated_at: str) -> str:
    """Build the README.md content for readmes-in-typst-universe."""

    # Sort all packages by stars descending (None treated as 0).
    def _sort_key(p: dict) -> int:
        return p.get("stars") or 0

    sorted_pkgs = sorted(packages, key=_sort_key, reverse=True)
    templates = [p for p in sorted_pkgs if p.get("is_template")]
    plain_pkgs = [p for p in sorted_pkgs if not p.get("is_template")]

    # Badge section
    deepwiki_url = f"https://deepwiki.com/OrangeX4/readmes-in-typst-universe"
    zread_url = f"https://zread.ai/OrangeX4/readmes-in-typst-universe"
    badges = (
        f'<a href="{deepwiki_url}"><img src="https://deepwiki.com/badge.svg"></a>\n'
        f'<a href="{zread_url}"><img src="{ZREAD_BADGE}"></a>\n'
    )

    lines: list[str] = []
    lines.append(badges)
    lines.append("")
    lines.append("# Typst Universe — Packages & Templates READMEs")
    lines.append("")
    lines.append(
        f"> Auto-generated on {_fmt_date(updated_at)}. "
        "Source: [typst/packages](https://github.com/typst/packages) · "
        "Website: [typst-universe-with-stars](https://orangex4.github.io/typst-universe-with-stars/)"
    )
    lines.append("")

    # AI guidance section
    lines.append("## How to Use This Repository (AI / Wiki Guide)")
    lines.append("")
    lines.append(
        "This repository aggregates the **READMEs** and **metadata** of every "
        "package and template published in the "
        "[Typst Universe](https://typst.app/universe) package registry.\n"
        "\n"
        "### Repository layout\n"
        "\n"
        "| Path | Contents |\n"
        "|------|----------|\n"
        "| `readmes/<name>.md` | Full README of the latest version of each package/template |\n"
        "| `metadata/<name>.toml` | Raw `typst.toml` (package manifest) of the latest version |\n"
        "| `README.md` (this file) | Summary table of all packages sorted by GitHub stars |\n"
        "\n"
        "### Guidance for AI assistants (DeepWiki, Zread, etc.)\n"
        "\n"
        "When a user asks about a Typst package or template:\n"
        "\n"
        "1. **Skim this README** first — every package appears in the table below "
        "with its `name`, `description`, `version`, `stars`, `last update`, "
        "`type` (package or template), `repository`, `categories`, and `keywords`. "
        "Use the table to quickly identify candidate packages that match the query.\n"
        "2. **Open `readmes/<name>.md`** for each promising candidate to read the "
        "full documentation, usage examples, and API reference before forming your answer.\n"
        "3. **Open `metadata/<name>.toml`** if you need the raw package manifest "
        "(e.g., declared dependencies, entry point, template parameters).\n"
        "4. Return a well-informed answer that cites specific package names and "
        "version numbers so the user can install them with `typst add <name>`."
    )
    lines.append("")

    # Package tables by tier
    lines.append("## All Packages & Templates (sorted by ★)")
    lines.append("")

    for lo, hi, label in STAR_TIERS:
        def _in_tier(p: dict) -> bool:
            s = p.get("stars") or 0
            if hi is None:
                return s >= lo
            return lo <= s < hi

        tier_templates = [p for p in templates if _in_tier(p)]
        tier_pkgs = [p for p in plain_pkgs if _in_tier(p)]

        if not tier_templates and not tier_pkgs:
            continue

        lines.append(f"### {label}")
        lines.append("")

        if tier_pkgs:
            lines.append("#### Packages")
            lines.append("")
            lines.append(TABLE_HEADER.rstrip("\n"))
            for pkg in tier_pkgs:
                lines.append(_pkg_row(pkg))
            lines.append("")

        if tier_templates:
            lines.append("#### Templates")
            lines.append("")
            lines.append(TABLE_HEADER.rstrip("\n"))
            for pkg in tier_templates:
                lines.append(_pkg_row(pkg))
            lines.append("")

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# File collection
# ---------------------------------------------------------------------------


def collect_files(packages: list[dict], work_dir: Path) -> None:
    """Populate metadata/ and readmes/ inside *work_dir*."""
    preview_dir = Path(CLONE_DIR) / "packages" / "preview"
    metadata_dir = work_dir / "metadata"
    readmes_dir = work_dir / "readmes"
    metadata_dir.mkdir(parents=True, exist_ok=True)
    readmes_dir.mkdir(parents=True, exist_ok=True)

    for pkg in packages:
        name = pkg["name"]
        version = pkg["version"]
        pkg_ver_dir = preview_dir / name / version

        # typst.toml
        toml_src = pkg_ver_dir / "typst.toml"
        if toml_src.exists():
            shutil.copy2(toml_src, metadata_dir / f"{name}.toml")

        # README (any casing)
        for readme_name in ("README.md", "readme.md", "Readme.md"):
            candidate = pkg_ver_dir / readme_name
            if candidate.exists():
                shutil.copy2(candidate, readmes_dir / f"{name}.md")
                break


# ---------------------------------------------------------------------------
# Git push
# ---------------------------------------------------------------------------


def push_to_remote(work_dir: Path, pat: str, actor: str, updated_at: str) -> None:
    """Initialise a git repo in *work_dir* and force-push to TARGET_REPO."""
    remote_url = TARGET_REPO.replace(
        "https://", f"https://{actor}:{pat}@"
    )

    def _git(*args: str) -> None:
        subprocess.run(["git", "-C", str(work_dir), *args], check=True)

    _git("init", "-b", "main")
    _git("config", "user.email", f"{actor}@users.noreply.github.com")
    _git("config", "user.name", actor)
    _git("add", ".")
    _git("commit", "-m", f"chore: update readmes-in-typst-universe [{updated_at}]")
    _git("remote", "add", "origin", remote_url)
    _git("push", "--force", "origin", "main")
    print(f"Force-pushed to {TARGET_REPO}", flush=True)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    pat = os.environ.get("READMES_PAT", "")
    if not pat:
        print("READMES_PAT is not set – skipping push.", file=sys.stderr)
        sys.exit(1)

    actor = os.environ.get("GITHUB_ACTOR", "github-actions")

    # Load packages.json (generated by fetch_packages.py).
    packages_json = REPO_ROOT / "packages.json"
    if not packages_json.exists():
        print(f"packages.json not found at {packages_json}", file=sys.stderr)
        sys.exit(1)

    with open(packages_json, encoding="utf-8") as fh:
        data = json.load(fh)

    packages: list[dict] = data["packages"]
    updated_at: str = data.get("updated_at", "")

    with tempfile.TemporaryDirectory() as tmp:
        work_dir = Path(tmp)

        print("Collecting typst.toml files…", flush=True)
        collect_files(packages, work_dir)

        print("Generating README.md…", flush=True)
        readme_content = generate_readme(packages, updated_at)
        (work_dir / "README.md").write_text(readme_content, encoding="utf-8")

        print("Pushing to remote…", flush=True)
        push_to_remote(work_dir, pat, actor, updated_at)

    print("Done.", flush=True)


if __name__ == "__main__":
    main()

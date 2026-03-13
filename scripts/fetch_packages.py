#!/usr/bin/env python3
"""
Fetch package metadata from typst/packages and generate packages.json.

For each package the script:
  - Identifies the latest semver version
  - Parses typst.toml (description, repository, homepage, keywords,
    categories, template info)
  - Determines whether the package is a template (has [template] key)
  - Fetches star count and last-push date from GitHub API when the
    repository / homepage URL points to GitHub (excluding the typst/packages
    repo itself)
  - Records when the latest version was first added to typst/packages via
    git history
  - Builds a thumbnail URL for template packages

Output: packages.json at the repository root.
"""

import json
import os
import re
import subprocess
import sys
import time
import tomllib
from datetime import datetime, timezone
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
HEADERS: dict[str, str] = {"Accept": "application/vnd.github.v3+json"}
if GITHUB_TOKEN:
    HEADERS["Authorization"] = f"Bearer {GITHUB_TOKEN}"

TYPST_PACKAGES_URL = "https://github.com/typst/packages"
CLONE_DIR = "/tmp/typst-packages"

# ---------------------------------------------------------------------------
# Repository helpers
# ---------------------------------------------------------------------------


def setup_repo() -> None:
    """Clone (or update) the typst/packages repository.

    A blobless clone is used so that full commit history is available for
    ``git log`` queries while file-content blobs are fetched lazily.
    """
    if os.path.exists(CLONE_DIR):
        print("Updating existing clone…", flush=True)
        subprocess.run(
            ["git", "-C", CLONE_DIR, "fetch", "origin", "main"],
            check=True,
        )
        subprocess.run(
            ["git", "-C", CLONE_DIR, "reset", "--hard", "origin/main"],
            check=True,
        )
    else:
        print("Cloning typst/packages (blobless)…", flush=True)
        subprocess.run(
            [
                "git",
                "clone",
                "--filter=blob:none",
                TYPST_PACKAGES_URL,
                CLONE_DIR,
            ],
            check=True,
        )


# ---------------------------------------------------------------------------
# Version helpers
# ---------------------------------------------------------------------------


def _semver_key(version: str) -> tuple[int, int, int]:
    parts = version.lstrip("v").split(".")
    try:
        return (int(parts[0]), int(parts[1]), int(parts[2]))
    except (IndexError, ValueError):
        return (0, 0, 0)


def get_latest_version(versions: list[str]) -> str:
    return max(versions, key=_semver_key)


# ---------------------------------------------------------------------------
# URL / GitHub helpers
# ---------------------------------------------------------------------------

_GITHUB_RE = re.compile(
    r"https?://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/?#\s]+)"
)


def is_github_url(url: str | None) -> bool:
    """Return True if *url* is a GitHub repo URL (not the typst/packages repo)."""
    if not url:
        return False
    norm = url.rstrip("/")
    if norm in (
        "https://github.com/typst/packages",
        "http://github.com/typst/packages",
    ):
        return False
    return bool(_GITHUB_RE.match(norm))


def extract_owner_repo(url: str) -> str | None:
    """Extract ``owner/repo`` from a GitHub URL, stripping ``.git`` suffix."""
    m = _GITHUB_RE.match(url)
    if not m:
        return None
    repo = m.group("repo")
    if repo.endswith(".git"):
        repo = repo[:-4]
    return f"{m.group('owner')}/{repo}"


# In-process cache so that multiple packages sharing the same upstream repo
# only trigger one API call.
_github_cache: dict[str, dict] = {}


def get_repo_info(owner_repo: str) -> dict:
    """Fetch stars count and last-push date for a GitHub repository."""
    if owner_repo in _github_cache:
        return _github_cache[owner_repo]

    url = f"https://api.github.com/repos/{owner_repo}"
    result: dict = {"stars": None, "pushed_at": None}
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            result = {
                "stars": data.get("stargazers_count"),
                "pushed_at": data.get("pushed_at"),
            }
        else:
            print(
                f"  GitHub API {resp.status_code} for {owner_repo}",
                file=sys.stderr,
            )
    except requests.RequestException as exc:
        print(f"  Network error fetching {owner_repo}: {exc}", file=sys.stderr)

    _github_cache[owner_repo] = result
    # Polite delay to stay well within GitHub's rate-limit.
    time.sleep(0.05)
    return result


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------


def get_publish_date(pkg_name: str, version: str) -> str | None:
    """Return the ISO timestamp of when *version* was first added to
    typst/packages, or ``None`` if it cannot be determined.
    """
    path = f"packages/preview/{pkg_name}/{version}/typst.toml"
    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                CLONE_DIR,
                "log",
                "--diff-filter=A",
                "--format=%cI",
                "--",
                path,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        lines = [ln.strip() for ln in result.stdout.splitlines() if ln.strip()]
        # git log shows newest first; the last line is the original addition.
        return lines[-1] if lines else None
    except subprocess.TimeoutExpired:
        print(f"  git log timed out for {pkg_name} {version}", file=sys.stderr)
        return None
    except OSError as exc:
        print(f"  git log failed for {pkg_name} {version}: {exc}", file=sys.stderr)
        return None


# ---------------------------------------------------------------------------
# Main processing
# ---------------------------------------------------------------------------


def process_packages() -> list[dict]:
    preview_dir = Path(CLONE_DIR) / "packages" / "preview"
    packages: list[dict] = []

    pkg_dirs = sorted(d for d in preview_dir.iterdir() if d.is_dir())
    total = len(pkg_dirs)

    for idx, pkg_dir in enumerate(pkg_dirs, 1):
        pkg_name = pkg_dir.name
        versions = [v.name for v in pkg_dir.iterdir() if v.is_dir()]
        if not versions:
            continue

        latest_ver = get_latest_version(versions)
        toml_path = pkg_dir / latest_ver / "typst.toml"
        if not toml_path.exists():
            continue

        try:
            with open(toml_path, "rb") as fh:
                data = tomllib.load(fh)
        except tomllib.TOMLDecodeError as exc:
            print(f"  Malformed TOML {toml_path}: {exc}", file=sys.stderr)
            continue

        pkg_meta = data.get("package", {})
        tmpl_meta = data.get("template", None)
        is_template = tmpl_meta is not None

        repository: str | None = pkg_meta.get("repository")
        homepage: str | None = pkg_meta.get("homepage")

        # Prefer repository URL for star lookup; fall back to homepage.
        github_url: str | None = None
        for url in (repository, homepage):
            if url and is_github_url(url):
                github_url = url
                break

        stars: int | None = None
        last_update: str | None = None
        if github_url:
            owner_repo = extract_owner_repo(github_url)
            if owner_repo:
                info = get_repo_info(owner_repo)
                stars = info.get("stars")
                last_update = info.get("pushed_at")

        # Build thumbnail URL for templates.
        thumbnail: str | None = None
        if is_template and tmpl_meta:
            thumb = tmpl_meta.get("thumbnail")
            if thumb:
                thumbnail = (
                    "https://raw.githubusercontent.com/typst/packages/main"
                    f"/packages/preview/{pkg_name}/{latest_ver}/{thumb}"
                )

        last_publish = get_publish_date(pkg_name, latest_ver)

        entry = {
            "name": pkg_name,
            "version": latest_ver,
            "description": pkg_meta.get("description", ""),
            "repository": repository,
            "homepage": homepage,
            "keywords": pkg_meta.get("keywords", []),
            "categories": pkg_meta.get("categories", []),
            "is_template": is_template,
            "thumbnail": thumbnail,
            "stars": stars,
            "last_update": last_update,
            "last_publish": last_publish,
        }
        packages.append(entry)

        stars_str = f"★{stars:,}" if stars is not None else "no stars"
        print(f"[{idx}/{total}] {pkg_name} {latest_ver} — {stars_str}", flush=True)

    return packages


def main() -> None:
    setup_repo()
    packages = process_packages()

    output = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "packages": packages,
    }

    out_path = Path(__file__).parent.parent / "packages.json"
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(output, fh, indent=2, ensure_ascii=False)

    print(f"\nWrote {len(packages)} packages → {out_path}", flush=True)


if __name__ == "__main__":
    main()

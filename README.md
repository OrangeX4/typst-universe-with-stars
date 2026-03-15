# Typst Universe with Stars (unofficial)

> **This is an unofficial site**, not affiliated with or endorsed by the [official Typst Universe](https://typst.app/universe/).

🌐 **Live site:** <https://orangex4.github.io/typst-universe-with-stars/>

<a href="https://deepwiki.com/OrangeX4/readmes-in-typst-universe"><img src="https://deepwiki.com/badge.svg"></a> <a href="https://zread.ai/OrangeX4/readmes-in-typst-universe"><img src="https://img.shields.io/badge/Ask_Zread-_.svg?style=flat&color=00b0aa&labelColor=000000&logo=data%3Aimage%2Fsvg%2Bxml%3Bbase64%2CPHN2ZyB3aWR0aD0iMTYiIGhlaWdodD0iMTYiIHZpZXdCb3g9IjAgMCAxNiAxNiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTQuOTYxNTYgMS42MDAxSDIuMjQxNTZDMS44ODgxIDEuNjAwMSAxLjYwMTU2IDEuODg2NjQgMS42MDE1NiAyLjI0MDFWNC45NjAxQzEuNjAxNTYgNS4zMTM1NiAxLjg4ODEgNS42MDAxIDIuMjQxNTYgNS42MDAxSDQuOTYxNTZDNS4zMTUwMiA1LjYwMDEgNS42MDE1NiA1LjMxMzU2IDUuNjAxNTYgNC45NjAxVjIuMjQwMUM1LjYwMTU2IDEuODg2NjQgNS4zMTUwMiAxLjYwMDEgNC45NjE1NiAxLjYwMDFaIiBmaWxsPSIjZmZmIi8%2BCjxwYXRoIGQ9Ik00Ljk2MTU2IDEwLjM5OTlIMi4yNDE1NkMxLjg4ODEgMTAuMzk5OSAxLjYwMTU2IDEwLjY4NjQgMS42MDE1NiAxMS4wMzk5VjEzLjc1OTlDMS42MDE1NiAxNC4xMTM0IDEuODg4MSAxNC4zOTk5IDIuMjQxNTYgMTQuMzk5OUg0Ljk2MTU2QzUuMzE1MDIgMTQuMzk5OSA1LjYwMTU2IDE0LjExMzQgNS42MDE1NiAxMy43NTk5VjExLjAzOTlDNS42MDE1NiAxMC42ODY0IDUuMzE1MDIgMTAuMzk5OSA0Ljk2MTU2IDEwLjM5OTlaIiBmaWxsPSIjZmZmIi8%2BCjxwYXRoIGQ9Ik0xMy43NTg0IDEuNjAwMUgxMS4wMzg0QzEwLjY4NSAxLjYwMDEgMTAuMzk4NCAxLjg4NjY0IDEwLjM5ODQgMi4yNDAxVjQuOTYwMUMxMC4zOTg0IDUuMzEzNTYgMTAuNjg1IDUuNjAwMSAxMS4wMzg0IDUuNjAwMUgxMy43NTg0QzE0LjExMTkgNS42MDAxIDE0LjM5ODQgNS4zMTM1NiAxNC4zOTg0IDQuOTYwMVYyLjI0MDFDMTQuMzk4NCAxLjg4NjY0IDE0LjExMTkgMS42MDAxIDEzLjc1ODQgMS42MDAxWiIgZmlsbD0iI2ZmZiIvPgo8cGF0aCBkPSJNNCAxMkwxMiA0TDQgMTJaIiBmaWxsPSIjZmZmIi8%2BCjxwYXRoIGQ9Ik00IDEyTDEyIDQiIHN0cm9rZT0iI2ZmZiIgc3Ryb2tlLXdpZHRoPSIxLjUiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIvPgo8L3N2Zz4K&logoColor=ffffff"></a>

The AI-friendly package index is hosted at [OrangeX4/readmes-in-typst-universe](https://github.com/OrangeX4/readmes-in-typst-universe), which contains all READMEs and metadata for every Typst Universe package.

A GitHub Pages site that browses every package in [typst/packages](https://github.com/typst/packages) and ranks them by GitHub stars.

## Features

- **Sort** by ★ Stars, Last Update (upstream repo push), or Last Publish (version added to typst/packages)
- **Filter** by Kind (All / Package / Template) and by Category
- **Search** across name, description, keywords, and categories
- **Template thumbnails** shown inline for template packages
- Cards link directly to `https://typst.app/universe/package/<name>`

## How it works

A scheduled GitHub Actions workflow (`.github/workflows/fetch-packages.yml`) runs at
**00:00 UTC** and **12:00 UTC** every day:

1. Clones `typst/packages` (blobless, full history for publish-date queries).
2. Finds the latest semver version for every package under `packages/preview/`.
3. Parses each `typst.toml`: description, repository, homepage, keywords, categories,
   template info.
4. For packages whose `repository` or `homepage` points to GitHub (excluding
   `https://github.com/typst/packages` itself), fetches star count and last-push
   date via the GitHub API using `GITHUB_TOKEN`.
5. Uses `git log --diff-filter=A` to determine when each version was first published
   to typst/packages.
6. Assembles a `build/` directory with all static assets and `packages.json`, then
   deploys it directly to GitHub Pages — no commits are pushed to `main`.

## GitHub Pages setup

1. Go to **Settings → Pages**.
2. Set *Source* to **GitHub Actions** (not "Deploy from a branch").
3. The site will be available at `https://<user>.github.io/typst-universe-with-stars/`.

## PR Previews

Pull requests automatically get a preview deployment at
`https://<user>.github.io/typst-universe-with-stars/pr-preview/pr-<number>/`
via the `rossjrw/pr-preview-action`.

## Local development

```bash
# Serve the static site locally (Python)
python -m http.server 8080
# Then open http://localhost:8080

# Run the data-fetch script (requires Python 3.11+ and `pip install requests`)
GITHUB_TOKEN=<your_token> python scripts/fetch_packages.py
```
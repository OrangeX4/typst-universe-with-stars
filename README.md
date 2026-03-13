# Typst Universe with Stars (unofficial)

> **This is an unofficial site**, not affiliated with or endorsed by the [official Typst Universe](https://typst.app/universe/).

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
# GitHub Copilot Instructions for joetheismansleg.github.io

## Project Overview

This is a minimal static site generator for GitHub Pages. The architecture is deliberately simple:

- **Core concept**: A Python script (`generate_site.py`) generates `index.html` → GitHub Actions builds and deploys to GitHub Pages
- **Deployment**: Automated CI/CD via `.github/workflows/deploy.yml` triggers on any branch push
- **Purpose**: Demonstrates Python-based site generation with GitHub Pages integration

## Key Files & Responsibilities

| File | Purpose |
|------|---------|
| `generate_site.py` | Generates `index.html` with hardcoded HTML structure |
| `.github/workflows/deploy.yml` | CI/CD pipeline: checks out → runs Python → uploads → deploys |
| `README.md` | Project description |

## Critical Patterns

### Build Process
1. **Python 3.11** must be available (set in deploy.yml)
2. `generate_site.py` writes to `index.html` in the repo root
3. Artifact upload path is `.` (entire repo root) - ensures `index.html` is included
4. No build caching or dependencies; purely sequential execution

### Site Generation Pattern
- Currently hardcoded HTML in `generate_site.py` using triple-quoted strings
- Uses standard Python `open()` with UTF-8 encoding (best practice)
- Output always goes to `index.html` in repo root
- `print()` statements for debugging in GitHub Actions logs

### Deployment Behavior
- Workflow triggers on **any branch** (`branches: ["**"]`)
- Permissions: `contents: read`, `pages: write`, `id-token: write` (standard Pages setup)
- Deploys to the environment named `github-pages` (configured in repo Settings)
- Deploy step outputs `page_url` - used to link from workflow summary

## When Modifying This Project

- **Changing site content**: Edit the `html` string in `generate_site.py`
- **Adding Python dependencies**: Update setup step in workflow; ensure they're standard library or minimal
- **Changing build output location**: Update both `generate_site.py` write path AND workflow artifact `path:`
- **Testing locally**: Run `python generate_site.py` then open `index.html` in a browser
- **Debugging deployments**: Check workflow run logs in Actions tab for Python execution and artifact upload status

## Conventions & Constraints

- Single HTML file output only (GitHub Pages default behavior)
- No external build tools (Jekyll, Hugo, etc.) - pure Python
- Minimal .gitignore - only excludes Jekyll/Bundler artifacts (legacy, can be cleaned up)
- Branch-agnostic builds are intentional: any branch push should preview on Pages

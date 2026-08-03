# Office AI Weekly GitHub Pages Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a minimal homepage for the latest Office AI Weekly issue and test whether the current private repository can publish it with GitHub Pages at no additional cost.

**Architecture:** Keep the archived issue and assets unchanged. Add a root homepage, a small verification script, and a GitHub Actions workflow that packages only `index.html` and `issues/` into the Pages artifact. If GitHub rejects Pages for the current private-repository plan, stop without changing visibility or billing.

**Tech Stack:** Static HTML/CSS, Python standard library, GitHub Actions, GitHub Pages, GitHub CLI

---

## File Structure

- Create `index.html`: public homepage with the latest-issue entry.
- Create `scripts/verify_site.py`: verify the homepage link, local issue assets, and exact publication scope.
- Create `.github/workflows/deploy-pages.yml`: package and deploy only approved public files.
- Do not modify `issues/M8W1/M8W1穗彩AI办公小报.html` or anything under `issues/M8W1/assets/`.

### Task 1: Add a site verification check

**Files:**
- Create: `scripts/verify_site.py`

- [ ] **Step 1: Create the verifier**

The script accepts a site directory, requires a root `index.html`, confirms that it links to the M8W1 HTML, rejects absolute local image paths, confirms every non-`data:` image exists, and rejects any publication artifact containing files outside `index.html` and `issues/`.

```python
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote
import sys

LATEST = "issues/M8W1/M8W1穗彩AI办公小报.html"


class References(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs = []
        self.srcs = []

    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key == "href" and value:
                self.hrefs.append(value)
            if key == "src" and value:
                self.srcs.append(value)


root = Path(sys.argv[1]).resolve()
index = root / "index.html"
issue = root / LATEST
assert index.is_file(), "missing index.html"
assert issue.is_file(), f"missing {LATEST}"

home = References()
home.feed(index.read_text(encoding="utf-8"))
expected_href = "issues/M8W1/M8W1%E7%A9%97%E5%BD%A9AI%E5%8A%9E%E5%85%AC%E5%B0%8F%E6%8A%A5.html"
assert expected_href in home.hrefs, "homepage does not link to latest issue"

newsletter = References()
newsletter.feed(issue.read_text(encoding="utf-8"))
for src in newsletter.srcs:
    if src.startswith(("data:", "http://", "https://")):
        continue
    assert not src.startswith("/"), f"absolute local path: {src}"
    assert (issue.parent / unquote(src)).is_file(), f"missing image: {src}"

files = {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()}
unexpected = {path for path in files if path != "index.html" and not path.startswith("issues/")}
assert not unexpected, f"unexpected published files: {sorted(unexpected)}"
print(f"site verified: {len(files)} files")
```

- [ ] **Step 2: Verify that the check initially fails**

Run the verifier against a temporary directory containing only the current `issues` directory and no homepage.

Expected: failure containing `missing index.html`.

### Task 2: Create the homepage

**Files:**
- Create: `index.html`

- [ ] **Step 1: Add the minimal homepage**

Create a responsive static page with:

- Title: `办公 AI 小报`
- Description: `每周整理 AI 在办公场景中的使用情况与实践发现`
- Latest label: `最新一期`
- Issue title: `M8W1 穗彩 AI 办公小报`
- Button text: `查看最新一期`
- Button target: `issues/M8W1/M8W1%E7%A9%97%E5%BD%A9AI%E5%8A%9E%E5%85%AC%E5%B0%8F%E6%8A%A5.html`

Keep all CSS inside this file and do not add external dependencies.

- [ ] **Step 2: Build an isolated publication artifact**

```bash
site_dir=$(mktemp -d)
cp index.html "$site_dir/"
cp -R issues "$site_dir/"
python3 scripts/verify_site.py "$site_dir"
```

Expected: `site verified: 17 files`.

- [ ] **Step 3: Test with a local web server**

Serve the temporary artifact, request `/index.html` and the encoded latest-issue URL, and confirm both return HTTP 200.

- [ ] **Step 4: Commit the homepage and verifier**

```bash
git add index.html scripts/verify_site.py
git commit -m "Add Office AI Weekly homepage"
```

### Task 3: Add narrowly scoped Pages deployment

**Files:**
- Create: `.github/workflows/deploy-pages.yml`

- [ ] **Step 1: Add the Pages workflow**

Use a workflow triggered by pushes to `main` and manual dispatch. Give it only `contents: read`, `pages: write`, and `id-token: write`. Its build job must copy only `index.html` and `issues/` into `_site`, run `python3 scripts/verify_site.py _site`, configure Pages, and upload `_site`. Its deploy job uses `actions/deploy-pages` and the `github-pages` environment.

- [ ] **Step 2: Validate the workflow file and publication scope locally**

Rebuild the temporary artifact and rerun the verifier. Confirm no README, documentation, scripts, workflow files, or Git metadata appear in the artifact.

- [ ] **Step 3: Commit and push**

```bash
git add .github/workflows/deploy-pages.yml
git commit -m "Add scoped GitHub Pages deployment"
git push
```

### Task 4: Test free GitHub Pages availability

**Files:**
- No repository file changes expected.

- [ ] **Step 1: Check current Pages status**

```bash
gh api repos/staveful/office-ai-weekly/pages
```

Expected before setup: HTTP 404 if no Pages site exists.

- [ ] **Step 2: Request workflow-based Pages setup**

```bash
gh api --method POST repos/staveful/office-ai-weekly/pages -f build_type=workflow
```

If GitHub returns a plan or private-repository restriction, stop immediately and report the exact response. Do not change repository visibility, billing, or other Pages settings.

- [ ] **Step 3: Trigger and watch deployment when setup succeeds**

```bash
gh workflow run deploy-pages.yml
gh run watch --exit-status
```

Expected: workflow completes successfully and reports a Pages URL.

- [ ] **Step 4: Verify the hosted site**

Confirm these return HTTP 200:

- `https://staveful.github.io/office-ai-weekly/`
- `https://staveful.github.io/office-ai-weekly/issues/M8W1/M8W1%E7%A9%97%E5%BD%A9AI%E5%8A%9E%E5%85%AC%E5%B0%8F%E6%8A%A5.html`

Extract every non-`data:` image reference from the hosted issue, request each resolved URL, and confirm HTTP 200. Open the hosted issue in a browser and confirm there are no broken images.

- [ ] **Step 5: Final repository verification**

Confirm the local and remote `main` commit hashes match, the worktree is clean, repository visibility is still `PRIVATE`, and the archived issue/assets have not changed.

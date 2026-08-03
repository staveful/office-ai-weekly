# Office AI Weekly GitHub Pages Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a minimal homepage for the latest Office AI Weekly issue and test whether the current private repository can publish it with GitHub Pages at no additional cost.

**Architecture:** Keep the archived issue and assets unchanged. Add a root homepage, a verifier that derives an exact publication manifest from the issue's image references, and a manual-only GitHub Actions workflow that packages only approved files. Enable automatic publishing only after Pages setup and the first deployment succeed.

**Tech Stack:** Static HTML/CSS, Python standard library, GitHub Actions, GitHub Pages, GitHub CLI

---

## File Structure

- Create `index.html`: public homepage with the latest-issue entry.
- Create `scripts/verify_site.py`: verify the homepage link, exact asset manifest, local files, and hosted responses.
- Create `.github/workflows/deploy-pages.yml`: package and deploy only approved public files.
- Do not modify `issues/M8W1/M8W1穗彩AI办公小报.html` or anything under `issues/M8W1/assets/`.

### Task 1: Record archive baseline and add the verifier

**Files:**
- Create: `scripts/verify_site.py`

- [ ] **Step 1: Record the immutable archive baseline**

The first archive commit is `fc70197`. Before and after every implementation commit, run:

```bash
test "$(git rev-parse HEAD:issues/M8W1)" = "$(git rev-parse fc70197:issues/M8W1)"
```

Expected: exit 0. This proves the archived HTML and assets still have the original Git tree hash.

- [ ] **Step 2: Create the verifier**

Create `scripts/verify_site.py` with two modes: a local artifact directory or `--url` for a hosted site. Local verification must allow exactly `index.html`, the M8W1 HTML, and the local images actually referenced by that HTML. It must reject extra files anywhere, symlinks, disallowed extensions, queries, fragments, absolute decoded paths, and traversal.

```python
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urljoin, urlsplit
from urllib.request import urlopen
import sys

LATEST = "issues/M8W1/M8W1穗彩AI办公小报.html"
LATEST_ENCODED = "issues/M8W1/M8W1%E7%A9%97%E5%BD%A9AI%E5%8A%9E%E5%85%AC%E5%B0%8F%E6%8A%A5.html"
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}


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


def parse(text):
    references = References()
    references.feed(text)
    return references


def safe_local_path(raw):
    parts = urlsplit(raw)
    assert not parts.scheme and not parts.netloc, f"external local reference: {raw}"
    assert not parts.query and not parts.fragment, f"query or fragment not allowed: {raw}"
    decoded = unquote(parts.path)
    path = PurePosixPath(decoded)
    assert not path.is_absolute(), f"absolute path: {raw}"
    assert ".." not in path.parts, f"path traversal: {raw}"
    assert path.suffix.lower() in IMAGE_EXTENSIONS, f"disallowed asset: {raw}"
    return path


def expected_files(issue_text):
    expected = {"index.html", LATEST}
    for src in parse(issue_text).srcs:
        if src.startswith("data:"):
            continue
        path = safe_local_path(src)
        expected.add((PurePosixPath(LATEST).parent / path).as_posix())
    return expected


def verify_directory(root_value):
    root = Path(root_value).resolve()
    index = root / "index.html"
    issue = root / LATEST
    assert index.is_file(), "missing index.html"
    assert issue.is_file(), f"missing {LATEST}"
    assert LATEST_ENCODED in parse(index.read_text(encoding="utf-8")).hrefs, "latest link missing"
    expected = expected_files(issue.read_text(encoding="utf-8"))
    for path in root.rglob("*"):
        assert not path.is_symlink(), f"symlink not allowed: {path}"
    actual = {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()}
    assert actual == expected, f"publication mismatch: extra={sorted(actual-expected)} missing={sorted(expected-actual)}"
    print(f"site verified: {len(actual)} files")


def get_bytes(url):
    with urlopen(url, timeout=20) as response:
        assert response.status == 200, f"HTTP {response.status}: {url}"
        return response.read()


def get_text(url):
    return get_bytes(url).decode("utf-8")


def verify_url(base):
    base = base.rstrip("/") + "/"
    home = get_text(base)
    assert LATEST_ENCODED in parse(home).hrefs, "hosted latest link missing"
    issue_url = urljoin(base, LATEST_ENCODED)
    issue = get_text(issue_url)
    for src in parse(issue).srcs:
        if src.startswith("data:"):
            continue
        safe_local_path(src)
        get_bytes(urljoin(issue_url, src))
    print("hosted site verified")


if sys.argv[1] == "--url":
    verify_url(sys.argv[2])
else:
    verify_directory(sys.argv[1])
```

- [ ] **Step 3: Confirm initial and negative failures**

Verify that a temporary artifact without `index.html` fails with `missing index.html`. After Task 2 creates the homepage, also prove that adding either `secret.txt` at the artifact root or `issues/extra.txt` makes the verifier fail with `publication mismatch`; remove each test file after the expected failure.

### Task 2: Create and verify the homepage

**Files:**
- Create: `index.html`

- [ ] **Step 1: Add the minimal homepage**

Create a responsive, dependency-free page containing:

- `办公 AI 小报`
- `每周整理 AI 在办公场景中的使用情况与实践发现`
- `最新一期`
- `M8W1 穗彩 AI 办公小报`
- A `查看最新一期` button linking to `issues/M8W1/M8W1%E7%A9%97%E5%BD%A9AI%E5%8A%9E%E5%85%AC%E5%B0%8F%E6%8A%A5.html`

Keep all CSS inside `index.html` and add no external dependencies.

- [ ] **Step 2: Build and verify the exact artifact**

```bash
pages_artifact=$(mktemp -d)
cp index.html "$pages_artifact/"
cp -R issues "$pages_artifact/"
python3 scripts/verify_site.py "$pages_artifact"
```

Expected: `site verified: 17 files`.

- [ ] **Step 3: Run reproducible local HTTP checks**

Start a local server rooted at the artifact, then run:

```bash
server_log=$(mktemp)
python3 -m http.server 8000 --directory "$pages_artifact" >"$server_log" 2>&1 &
server_pid=$!
trap 'kill "$server_pid" 2>/dev/null || true' EXIT
python3 scripts/verify_site.py --url http://127.0.0.1:8000/
kill "$server_pid"
trap - EXIT
```

Expected: `hosted site verified`.

- [ ] **Step 4: Preserve archive, commit, and recheck**

```bash
test "$(git rev-parse HEAD:issues/M8W1)" = "$(git rev-parse fc70197:issues/M8W1)"
git add index.html scripts/verify_site.py
git commit -m "Add Office AI Weekly homepage"
test "$(git rev-parse HEAD:issues/M8W1)" = "$(git rev-parse fc70197:issues/M8W1)"
```

### Task 3: Add a manual-only Pages workflow

**Files:**
- Create: `.github/workflows/deploy-pages.yml`

- [ ] **Step 1: Add the complete workflow**

```yaml
name: Deploy GitHub Pages

on:
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: pages
  cancel-in-progress: false

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4
      - name: Build approved artifact
        run: |
          mkdir _site
          cp index.html _site/
          cp -R issues _site/
          python3 scripts/verify_site.py _site
      - name: Configure Pages
        uses: actions/configure-pages@v5
      - name: Upload Pages artifact
        uses: actions/upload-pages-artifact@v4
        with:
          path: _site

  deploy:
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    runs-on: ubuntu-latest
    needs: build
    steps:
      - name: Deploy Pages
        id: deployment
        uses: actions/deploy-pages@v4
```

- [ ] **Step 2: Validate the workflow**

Install `actionlint` if it is not already available, then run `actionlint .github/workflows/deploy-pages.yml`. Expected: exit 0 with no output.

- [ ] **Step 3: Preserve archive, commit, and push the manual workflow**

```bash
test "$(git rev-parse HEAD:issues/M8W1)" = "$(git rev-parse fc70197:issues/M8W1)"
git add .github/workflows/deploy-pages.yml
git commit -m "Add manual GitHub Pages deployment"
test "$(git rev-parse HEAD:issues/M8W1)" = "$(git rev-parse fc70197:issues/M8W1)"
git push
```

### Task 4: Probe Pages availability without changing visibility

**Files:**
- No repository file changes.

- [ ] **Step 1: GET the current Pages configuration and preserve the exact response**

Use the GitHub API with the authenticated CLI token, writing the response body to a temporary file and capturing the HTTP status without printing the token:

```bash
pages_body=$(mktemp)
github_token=$(gh auth token)
pages_status=$(curl -sS -o "$pages_body" -w '%{http_code}' \
  -H 'Accept: application/vnd.github+json' \
  -H "Authorization: Bearer $github_token" \
  -H 'X-GitHub-Api-Version: 2022-11-28' \
  'https://api.github.com/repos/staveful/office-ai-weekly/pages')
case "$pages_status" in
  200)
    build_type=$(jq -r '.build_type // ""' "$pages_body")
    if [ "$build_type" != workflow ]; then
      printf 'Existing Pages configuration (HTTP %s):\n' "$pages_status"
      jq . "$pages_body"
      exit 20
    fi
    ;;
  404) ;;
  401|403)
    printf 'Pages authentication/permission error (HTTP %s):\n' "$pages_status"
    jq . "$pages_body"
    exit 21
    ;;
  *)
    printf 'Unexpected Pages response (HTTP %s):\n' "$pages_status"
    jq . "$pages_body"
    exit 22
    ;;
esac
```

- HTTP 200 with `build_type: workflow`: continue without POST.
- HTTP 200 with another build type: stop and report the existing configuration rather than overwrite it.
- HTTP 404: continue to the create request.
- HTTP 401 or 403: stop and report an authentication or permission problem, including the response body.
- Any other status: stop and report the exact status and body.

- [ ] **Step 2: Create workflow-based Pages only after a 404**

Send `POST /repos/staveful/office-ai-weekly/pages` with `{"build_type":"workflow"}`.

Only when the GET status was 404, run:

```bash
create_body=$(mktemp)
create_status=$(curl -sS -o "$create_body" -w '%{http_code}' -X POST \
  -H 'Accept: application/vnd.github+json' \
  -H "Authorization: Bearer $github_token" \
  -H 'X-GitHub-Api-Version: 2022-11-28' \
  -H 'Content-Type: application/json' \
  'https://api.github.com/repos/staveful/office-ai-weekly/pages' \
  --data '{"build_type":"workflow"}')
case "$create_status" in
  201) ;;
  401|403)
    printf 'Pages authentication/permission error (HTTP %s):\n' "$create_status"
    jq . "$create_body"
    exit 23
    ;;
  409|422)
    printf 'Pages setup rejected (HTTP %s):\n' "$create_status"
    jq . "$create_body"
    exit 24
    ;;
  *)
    printf 'Unexpected Pages setup response (HTTP %s):\n' "$create_status"
    jq . "$create_body"
    exit 25
    ;;
esac
```

- HTTP 201: continue.
- HTTP 409 or 422: stop and report the exact response. Do not assume it is a plan restriction unless the response says so.
- HTTP 401 or 403: stop and report the authentication or permission error.
- Any other status: stop and report the exact response.

At every stop, leave repository visibility, billing, and workflow triggers unchanged.

### Task 5: Deploy once, verify, then enable automatic publishing

**Files:**
- Modify after successful deployment only: `.github/workflows/deploy-pages.yml`

- [ ] **Step 1: Dispatch the exact workflow and capture its run ID**

```bash
head_sha=$(git rev-parse HEAD)
prior_runs=$(mktemp)
gh api "repos/staveful/office-ai-weekly/actions/workflows/deploy-pages.yml/runs?event=workflow_dispatch&head_sha=$head_sha&per_page=100" \
  --jq '.workflow_runs[].id' > "$prior_runs"
gh workflow run deploy-pages.yml --ref main
run_id=''
for attempt in $(seq 1 30); do
  current_runs=$(mktemp)
  gh api "repos/staveful/office-ai-weekly/actions/workflows/deploy-pages.yml/runs?event=workflow_dispatch&head_sha=$head_sha&per_page=100" \
    --jq '.workflow_runs[].id' > "$current_runs"
  while IFS= read -r candidate; do
    if ! grep -qx "$candidate" "$prior_runs"; then
      run_id=$candidate
      break
    fi
  done < "$current_runs"
  [ -n "$run_id" ] && break
  sleep 2
done
test -n "$run_id"
gh run watch "$run_id" --exit-status
```

- [ ] **Step 2: Read and verify the actual Pages URL**

```bash
pages_url=$(gh api repos/staveful/office-ai-weekly/pages --jq .html_url)
python3 scripts/verify_site.py --url "$pages_url"
```

Expected: `hosted site verified`. Also open the hosted issue in a browser and confirm no broken images.

- [ ] **Step 3: Enable automatic publishing only after the successful test**

Change the workflow trigger to:

```yaml
on:
  push:
    branches: [main]
  workflow_dispatch:
```

Run `actionlint`, preserve the archive tree, and commit with `Enable automatic Pages publishing`. Before pushing, record existing push-event runs for the new `head_sha` using the same `prior_runs` method above; push, then poll the workflow-runs API with `event=push&head_sha=$head_sha` for at most 60 seconds, select an ID absent from `prior_runs`, and pass that exact ID to `gh run watch "$run_id" --exit-status`.

- [ ] **Step 4: Final repository and remote verification**

```bash
git fetch origin main
test "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)"
test "$(git rev-parse HEAD:issues/M8W1)" = "$(git rev-parse fc70197:issues/M8W1)"
test "$(git rev-parse origin/main:issues/M8W1)" = "$(git rev-parse fc70197:issues/M8W1)"
test -z "$(git status --porcelain)"
test "$(gh repo view staveful/office-ai-weekly --json visibility --jq .visibility)" = "PRIVATE"
python3 scripts/verify_site.py --url "$(gh api repos/staveful/office-ai-weekly/pages --jq .html_url)"
```

Expected: every command exits 0, the repository remains private, the archive tree matches the original commit, and the hosted site responds successfully.

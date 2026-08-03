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


if len(sys.argv) < 2:
    raise SystemExit("usage: verify_site.py SITE_DIR | --url BASE_URL")
if sys.argv[1] == "--url":
    verify_url(sys.argv[2])
else:
    verify_directory(sys.argv[1])

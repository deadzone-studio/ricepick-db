"""Turns one filled-in issue form into one entry in rices.json.

Everything a stranger typed is data. It is read from the environment, never
pasted into a command, and the file is written with json.dump so no field can
break out of its own quotes.
"""

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import date, datetime
from pathlib import Path

from ricepick.constants import DISTROS, IMAGE_HOSTS
from ricepick.validate import InvalidRice, validate

CATALOG = Path("rices.json")
API = "https://api.github.com"
TIMEOUT = 20
REPO_PREFIX = "https://github.com/"
ALLOWED_IN_PATH = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-")


class Refused(Exception):
    """Something in the form is wrong. The message goes back to the person."""


def parse_form(body: str) -> dict[str, str]:
    """GitHub renders a form as '### Label' followed by what was typed."""
    sections: dict[str, str] = {}
    label, lines = None, []

    for line in body.replace("\r\n", "\n").split("\n"):
        if line.startswith("### "):
            if label is not None:
                sections[label] = "\n".join(lines).strip()
            label, lines = line[4:].strip().lower(), []
        elif label is not None:
            lines.append(line)

    if label is not None:
        sections[label] = "\n".join(lines).strip()

    return {key: "" if value == "_No response_" else value
            for key, value in sections.items()}


def ticked(block: str) -> list[str]:
    chosen = []
    for line in block.split("\n"):
        line = line.strip()
        if line[:5].lower() == "- [x]":
            chosen.append(line[5:].strip().lower())
    return chosen


def api(path: str) -> dict:
    request = urllib.request.Request(
        API + path,
        headers={"Accept": "application/vnd.github+json",
                 "User-Agent": "ricepick-db"},
    )
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        request.add_header("Authorization", f"Bearer {token}")

    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            raise Refused("GitHub says that repository does not exist, "
                          "or it is private.") from None
        raise Refused(f"GitHub answered {error.code} when asked about it.") from None
    except (urllib.error.URLError, OSError) as error:
        raise Refused(f"could not reach GitHub: {error}") from None


def split_repo(url: str) -> tuple[str, str]:
    if not url.startswith(REPO_PREFIX):
        raise Refused(f"the repository has to start with {REPO_PREFIX} "
                      "- GitLab rices are added by hand for now.")

    path = url[len(REPO_PREFIX):].strip("/")
    if path.endswith(".git"):
        path = path[:-4]

    parts = path.split("/")
    if len(parts) != 2 or not all(parts):
        raise Refused("that is not an address of a repository, "
                      "it should look like https://github.com/someone/their-rice")
    if not all(set(part) <= ALLOWED_IN_PATH for part in parts):
        raise Refused("the repository address has characters that cannot be in one")

    return parts[0], parts[1]


def build_entry(form: dict[str, str]) -> dict:
    name = form.get("name", "").strip()
    repo_url = form.get("repository", "").strip()
    screenshot = form.get("screenshot", "").strip()
    description = " ".join(form.get("description", "").split())

    if not screenshot.startswith(IMAGE_HOSTS):
        allowed = "\n".join(f"- `{host}`" for host in IMAGE_HOSTS)
        raise Refused("the screenshot has to be hosted on one of these:\n" + allowed)

    owner, repo_name = split_repo(repo_url)
    meta = api(f"/repos/{owner}/{repo_name}")
    head = api(f"/repos/{owner}/{repo_name}/commits/{meta['default_branch']}")

    distros = [d for d in ticked(form.get(
        "distributions it is known to work on", "")) if d in DISTROS]

    return {
        "name": name,
        "author": meta["owner"]["login"],
        "repo": f"{REPO_PREFIX}{meta['full_name']}",
        "commit": head["sha"],
        "screenshots": [screenshot],
        "description": description,
        "distros": distros or ["arch"],
        "verified": False,
        "archived": bool(meta.get("archived")),
        "last_update": (meta.get("pushed_at") or "")[:10] or date.today().isoformat(),
        "stars": int(meta.get("stargazers_count") or 0),
        "added": date.today().isoformat(),
    }


def already_here(entries: list[dict], entry: dict) -> str | None:
    for old in entries:
        if old.get("repo", "").rstrip("/").lower() == entry["repo"].rstrip("/").lower():
            return f"that repository is already on the list as **{old.get('name')}**"
        if old.get("name", "").lower() == entry["name"].lower():
            return f"**{old.get('name')}** is already on the list under that name"
    return None


def main() -> int:
    body = os.environ.get("ISSUE_BODY", "")
    if not body.strip():
        print("the form came through empty")
        return 1

    entries = json.loads(CATALOG.read_text(encoding="utf-8"))

    try:
        entry = build_entry(parse_form(body))
        clash = already_here(entries, entry)
        if clash:
            raise Refused(clash)
        validate(entry)
    except Refused as error:
        print(str(error))
        return 1
    except InvalidRice as error:
        print(f"{error}\n\nFix that in the form and open it again.")
        return 1

    entries.append(entry)
    entries.sort(key=lambda item: str(item.get("name", "")).lower())
    CATALOG.write_text(json.dumps(entries, indent=2, ensure_ascii=False) + "\n",
                       encoding="utf-8")

    state = "archived by its author" if entry["archived"] else "active"
    since = (datetime.now().date()
             - date.fromisoformat(entry["last_update"])).days
    print(
        f"Added **{entry['name']}** by {entry['author']}.\n\n"
        f"- pinned to `{entry['commit'][:7]}`\n"
        f"- {entry['stars']} stars, {state}, last pushed {since} days ago\n"
        f"- marked unverified until someone checks it\n\n"
        "It shows up in ricepick within six hours."
    )
    print(f"::notice::added {entry['name']}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

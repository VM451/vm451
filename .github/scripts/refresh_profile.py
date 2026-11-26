import json
import os
import re
from base64 import b64encode
from datetime import date, datetime, timedelta
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen

from profile_cards import render_cards

USER = "VM451"
PROFILE = f"https://github.com/{USER}"
API = f"https://api.github.com/users/{USER}"
LANDMARK_COUNT = 4
EXCLUDED_REPOSITORIES = {USER.lower(), f"{USER.lower()}.github.io"}
BEGIN = "<!-- profile:begin -->"
END = "<!-- profile:end -->"


def fetch(url):
    headers = {"User-Agent": "VM451-profile-refresh"}
    if urlsplit(url).netloc == "api.github.com":
        headers["Accept"] = "application/vnd.github+json"
        token = os.environ.get("GITHUB_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"
    request = Request(url, headers=headers)
    with urlopen(request, timeout=15) as response:
        return response.read().decode("utf-8")


def avatar_uri(url):
    host = "avatars.githubusercontent.com"
    parts = urlsplit(url)
    if parts.scheme != "https" or parts.netloc != host:
        raise ValueError("Unexpected GitHub avatar URL")
    thumbnail = urlunsplit(("https", host, parts.path, "s=128", ""))
    with urlopen(thumbnail, timeout=15) as response:
        if urlsplit(response.url).netloc != host:
            raise ValueError("Unexpected GitHub avatar redirect")
        data = response.read(128 * 1024 + 1)
    if data.startswith(b"\xff\xd8\xff"):
        mime = "image/jpeg"
    elif data.startswith(b"\x89PNG\r\n\x1a\n"):
        mime = "image/png"
    else:
        raise ValueError("Unsupported GitHub avatar format")
    if len(data) > 128 * 1024:
        raise ValueError("GitHub avatar is too large")
    return f"data:{mime};base64,{b64encode(data).decode('ascii')}"


class Calendar(HTMLParser):
    def __init__(self):
        super().__init__()
        self.cells = {}
        self.counts = {}
        self.tip = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "td" and "ContributionCalendar-day" in attrs.get("class", "").split():
            day = date.fromisoformat(attrs["data-date"])
            level = int(attrs["data-level"])
            if attrs["id"] in self.cells or not 0 <= level <= 4:
                raise ValueError("Unexpected GitHub calendar cell")
            self.cells[attrs["id"]] = (day, level)
        elif tag == "tool-tip" and attrs.get("for", "").startswith("contribution-day-component-"):
            self.tip = attrs["for"]

    def handle_endtag(self, tag):
        if tag == "tool-tip":
            self.tip = None

    def handle_data(self, text):
        if self.tip is None or not text.strip():
            return
        match = re.fullmatch(r"(No|\d[\d,]*) contributions? on .+", text.strip())
        if not match or self.tip in self.counts:
            raise ValueError("Unexpected GitHub calendar tooltip")
        count = match[1]
        self.counts[self.tip] = 0 if count == "No" else int(count.replace(",", ""))

    def days(self):
        if self.cells.keys() != self.counts.keys() or not 364 <= len(self.cells) <= 371:
            raise ValueError("Incomplete GitHub contribution calendar")
        days = sorted((day, self.counts[key], level) for key, (day, level) in self.cells.items())
        if any((b[0] - a[0]).days != 1 for a, b in zip(days, days[1:])):
            raise ValueError("GitHub contribution calendar has gaps or duplicate dates")
        return days


def pushed_at(repo):
    return datetime.fromisoformat(repo["pushed_at"].replace("Z", "+00:00"))


def landmark_repos(repos):
    candidates = [
        repo for repo in repos
        if repo["name"].lower() not in EXCLUDED_REPOSITORIES
        and not repo["fork"]
        and not repo["archived"]
        and repo["pushed_at"]
    ]
    candidates.sort(key=lambda repo: repo["name"].lower())
    candidates.sort(key=pushed_at, reverse=True)
    return candidates[:LANDMARK_COUNT]


def profile_data(days, account, repos):
    counts = [count for _, count, _ in days]
    first = days[0][0]
    sunday = first - timedelta(days=(first.weekday() + 1) % 7)
    projects = []
    for repo in landmark_repos(repos):
        name = repo["name"]
        mix = json.loads(fetch(f"https://api.github.com/repos/{USER}/{name}/languages"))
        if not isinstance(mix, dict) or any(type(size) is not int or size <= 0 for size in mix.values()):
            raise ValueError(f"Unexpected GitHub languages for {name}")
        projects.append({
            "name": name,
            "description": repo["description"] or "No description provided.",
            "language": repo["language"],
            "stars": repo["stargazers_count"],
            "updated": pushed_at(repo).date(),
            "mix": sorted(mix.items(), key=lambda item: (-item[1], item[0])),
        })
    return {
        "login": account["login"],
        "bio": account["bio"] or "",
        "avatar": avatar_uri(account["avatar_url"]),
        "first": first,
        "last": days[-1][0],
        "days": [(*(divmod((day - sunday).days, 7)), count, level) for day, count, level in days],
        "total": sum(counts),
        "active": sum(count > 0 for count in counts),
        "peak": max(counts),
        "repos": len(repos),
        "followers": account["followers"],
        "stars": sum(repo["stargazers_count"] for repo in repos),
        "projects": projects,
    }


def render_readme(data):
    total, active, peak = data["total"], data["active"], data["peak"]
    projects = data["projects"]
    lines = [
        f"[![VM451, Software Engineer in Apple Plateform](./profile/header.svg)]({PROFILE})",
        "",
        "## The city I built this year",
        "",
        f"[![Contribution City: {total:,} contributions, {active:,} active days, busiest day {peak:,}.](./profile/city.svg)]({PROFILE}#contributions)",
        "",
        '<p align="center">Every tile is a day; taller buildings mean more contributions.</p>',
        "",
        f'<p align="center"><sub>{data["first"]} to {data["last"]} · <a href="{PROFILE}#contributions">GitHub contribution calendar</a></sub></p>',
        "",
        "## Population",
        "",
        f"![Profile Signal: {data['stars']:,} stars, {total:,} contributions, {data['repos']:,} public repos, {data['followers']:,} followers.](./profile/population.svg)",
        "",
        "## Landmarks",
        "",
        "![Project cards with languages, stars, and update dates](./profile/landmarks.svg)",
        "",
        " · ".join(f"[**{p['name']}**]({PROFILE}/{p['name']})" for p in projects),
        "",
        "## Visit",
        "",
        f"[![GitHub: @vm451](./profile/visit.svg)]({PROFILE})",
        "",
        f'<p align="center"><a href="{PROFILE}">GitHub</a> · <a href="{PROFILE}?tab=repositories">Repositories</a></p>',
    ]
    return "\n".join(lines)


def update(path):
    original = path.read_text(encoding="utf-8")
    if original.count(BEGIN) != 1 or original.count(END) != 1 or original.index(BEGIN) > original.index(END):
        raise ValueError("README must have exactly one ordered pair of profile markers")

    calendar = Calendar()
    calendar.feed(fetch(f"https://github.com/users/{USER}/contributions"))
    calendar.close()
    days = calendar.days()

    account = json.loads(fetch(API))
    repos = []
    page = 1
    while True:
        batch = json.loads(fetch(f"{API}/repos?type=owner&per_page=100&page={page}"))
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    if (
        account["login"] != USER
        or len({repo["id"] for repo in repos}) != len(repos)
        or any(repo["private"] or repo["owner"]["login"] != USER for repo in repos)
    ):
        raise ValueError("Incomplete or unexpected GitHub repository list")

    data = profile_data(days, account, repos)
    cards = render_cards(data)
    before, remainder = original.split(BEGIN)
    _, after = remainder.split(END)
    refreshed = f"{before}{BEGIN}\n\n{render_readme(data)}\n\n{END}{after}"
    directory = path.parent / "profile"
    directory.mkdir(exist_ok=True)
    for name, svg in cards.items():
        target = directory / name
        if not target.exists() or target.read_text(encoding="utf-8") != svg:
            target.write_text(svg, encoding="utf-8")
    if refreshed != original:
        path.write_text(refreshed, encoding="utf-8")


if __name__ == "__main__":
    update(Path(__file__).resolve().parents[2] / "README.md")

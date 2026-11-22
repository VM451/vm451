import json
import re
from datetime import date, timedelta
from html import escape
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen

USER = "VM451"
PROFILE = f"https://github.com/{USER}"
API = f"https://api.github.com/users/{USER}"
PROJECTS = ("AnyTypKit", "TypstUniverseKit", "BrightCraft-Legal", "LedgerAgent")
BEGIN = "<!-- profile:begin -->"
END = "<!-- profile:end -->"


def fetch(url):
    request = Request(url, headers={"User-Agent": "VM451-profile-refresh"})
    with urlopen(request, timeout=15) as response:
        return response.read().decode("utf-8")


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


def markdown(text):
    plain = escape(" ".join(text.split()))
    return re.sub(r"([\\`*_{}\[\]()!|~])", r"\\\1", plain)


def render(days, account, repos):
    counts = [count for _, count, _ in days]
    total, active, peak = sum(counts), sum(count > 0 for count in counts), max(counts)
    last = days[-1][0]
    sunday = last - timedelta(days=(last.weekday() + 1) % 7)
    levels = {day: ".:-=+"[level] for day, _, level in days}
    graph = []
    for offset, label in enumerate(("Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat")):
        row = (levels.get(sunday + timedelta(weeks=w, days=offset), " ") for w in range(-15, 1))
        graph.append(f"{label}  " + " ".join(row).rstrip())
    stars = sum(repo["stargazers_count"] for repo in repos)
    by_name = {repo["name"]: repo for repo in repos}
    lines = [
        "## The city I built this year",
        "",
        f"**{total:,} contributions** · {active:,} active days · Busiest day: {peak:,}",
        "",
        "Last 16 weeks, oldest to newest. Each character is one day.",
        "",
        "```text",
        *graph,
        "```",
        "",
        "` . : - = + ` — none to highest activity.",
        "",
        f"[Open GitHub's contribution calendar]({PROFILE}#contributions) · {days[0][0]} to {last}",
        "",
        "## Population",
        "",
        "| Stars across public repos | Contributions | Public repos | Followers |",
        "| ---: | ---: | ---: | ---: |",
        f"| {stars:,} | {total:,} | {account['public_repos']:,} | {account['followers']:,} |",
        "",
        "## Landmarks",
        "",
        "| Project | Description | Language | Stars | Updated (UTC) |",
        "| --- | --- | --- | ---: | --- |",
    ]
    for name in PROJECTS:
        repo = by_name.get(name)
        if repo is None:
            continue
        description = markdown(repo["description"] or "No description provided.")
        language = markdown(repo["language"] or "—")
        updated = date.fromisoformat(repo["updated_at"][:10])
        lines.append(f"| [{name}]({PROFILE}/{name}) | {description} | {language} | {repo['stargazers_count']:,} | {updated} |")
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
    for page in range(1, account["public_repos"] // 100 + 2):
        batch = json.loads(fetch(f"{API}/repos?type=owner&per_page=100&page={page}"))
        repos.extend(batch)
        if len(batch) < 100:
            break
    if (
        account["login"] != USER
        or len({repo["id"] for repo in repos}) != len(repos)
        or len(repos) != account["public_repos"]
        or any(repo["private"] or repo["owner"]["login"] != USER for repo in repos)
    ):
        raise ValueError("Incomplete or unexpected GitHub repository list")

    before, remainder = original.split(BEGIN)
    _, after = remainder.split(END)
    refreshed = f"{before}{BEGIN}\n\n{render(days, account, repos)}\n\n{END}{after}"
    if refreshed != original:
        path.write_text(refreshed, encoding="utf-8")


if __name__ == "__main__":
    update(Path(__file__).resolve().parents[2] / "README.md")

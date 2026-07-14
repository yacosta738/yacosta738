"""
Daily metrics pipeline: queries GitHub's GraphQL API for live stats and overwrites
the dynamic <tspan> elements (by id) in assets/profile-card-{dark,light}.svg.

Does NOT touch the ASCII art or static personal info — those are fixed content
created once by scripts/image_to_ascii_svg.py and hand-edited into the templates.

Required env vars (only read when main() runs, not at import time):
    METRICS_TOKEN   fine-grained PAT with read:Followers, read:Starring,
                    read:Contents, read:Commit statuses, read:Metadata,
                    read:Pull Requests scopes
    USER_NAME       GitHub username, e.g. "yacosta738"
"""
import csv
import datetime
import hashlib
import os
from dateutil import relativedelta
from lxml import etree
import requests

GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"
UPTIME_START = datetime.date(2012, 9, 3)  # start of university, not birthday
CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "cache")


def format_plural(unit: int) -> str:
    """Returns 's' for plural counts, '' for exactly one."""
    return "" if unit == 1 else "s"


def uptime_string(start: datetime.date, today: datetime.date) -> str:
    """Formats the time elapsed since `start` as 'X years, Y months, Z days'."""
    diff = relativedelta.relativedelta(today, start)
    return "{} year{}, {} month{}, {} day{}".format(
        diff.years, format_plural(diff.years),
        diff.months, format_plural(diff.months),
        diff.days, format_plural(diff.days),
    )


def get_headers() -> dict:
    return {"authorization": f"token {os.environ['METRICS_TOKEN']}"}


def get_user_name() -> str:
    return os.environ["USER_NAME"]


def graphql_request(query: str, variables: dict) -> dict:
    response = requests.post(
        GITHUB_GRAPHQL_URL, json={"query": query, "variables": variables},
        headers=get_headers(), timeout=30,
    )
    if response.status_code != 200:
        raise RuntimeError(f"GraphQL request failed ({response.status_code}): {response.text}")
    return response.json()


def fetch_followers(user_name: str) -> int:
    query = """
    query($login: String!) {
        user(login: $login) { followers { totalCount } }
    }"""
    data = graphql_request(query, {"login": user_name})
    return data["data"]["user"]["followers"]["totalCount"]


def fetch_commit_count(user_name: str, years_back: int = 15) -> int:
    start = (datetime.datetime.utcnow() - datetime.timedelta(days=365 * years_back)).isoformat() + "Z"
    end = datetime.datetime.utcnow().isoformat() + "Z"
    query = """
    query($login: String!, $start: DateTime!, $end: DateTime!) {
        user(login: $login) {
            contributionsCollection(from: $start, to: $end) {
                contributionCalendar { totalContributions }
            }
        }
    }"""
    data = graphql_request(query, {"login": user_name, "start": start, "end": end})
    return data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["totalContributions"]


def fetch_repos_and_stars(user_name: str, affiliations: list[str]) -> tuple[int, int]:
    """Returns (repo_count, star_count) for the given ownership affiliations."""
    query = """
    query($login: String!, $affiliations: [RepositoryAffiliation], $cursor: String) {
        user(login: $login) {
            repositories(first: 100, after: $cursor, ownerAffiliations: $affiliations) {
                totalCount
                edges { node { stargazers { totalCount } } }
                pageInfo { endCursor hasNextPage }
            }
        }
    }"""
    total_repos = 0
    total_stars = 0
    cursor = None
    while True:
        data = graphql_request(query, {
            "login": user_name, "affiliations": affiliations, "cursor": cursor,
        })
        repos = data["data"]["user"]["repositories"]
        total_repos = repos["totalCount"]
        total_stars += sum(edge["node"]["stargazers"]["totalCount"] for edge in repos["edges"])
        if not repos["pageInfo"]["hasNextPage"]:
            break
        cursor = repos["pageInfo"]["endCursor"]
    return total_repos, total_stars


def repo_cache_path(owner: str, name: str) -> str:
    key = hashlib.sha256(f"{owner}/{name}".encode()).hexdigest()
    return os.path.join(CACHE_DIR, f"{key}.csv")


def load_repo_cache(owner: str, name: str) -> tuple[str | None, int, int]:
    """Returns (last_commit_sha, cached_additions, cached_deletions), or (None, 0, 0)."""
    path = repo_cache_path(owner, name)
    if not os.path.exists(path):
        return None, 0, 0
    with open(path, newline="", encoding="utf-8") as f:
        row = next(csv.reader(f), None)
    if not row:
        return None, 0, 0
    return row[0], int(row[1]), int(row[2])


def save_repo_cache(owner: str, name: str, last_sha: str, additions: int, deletions: int) -> None:
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(repo_cache_path(owner, name), "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([last_sha, additions, deletions])


def fetch_repo_names(user_name: str, affiliations: list[str]) -> list[tuple[str, str]]:
    """Returns [(owner, name), ...] for repos matching the given affiliations."""
    query = """
    query($login: String!, $affiliations: [RepositoryAffiliation], $cursor: String) {
        user(login: $login) {
            repositories(first: 100, after: $cursor, ownerAffiliations: $affiliations) {
                edges { node { name owner { login } } }
                pageInfo { endCursor hasNextPage }
            }
        }
    }"""
    names = []
    cursor = None
    while True:
        data = graphql_request(query, {
            "login": user_name, "affiliations": affiliations, "cursor": cursor,
        })
        repos = data["data"]["user"]["repositories"]
        names.extend((edge["node"]["owner"]["login"], edge["node"]["name"]) for edge in repos["edges"])
        if not repos["pageInfo"]["hasNextPage"]:
            break
        cursor = repos["pageInfo"]["endCursor"]
    return names


def fetch_commit_diff(owner: str, name: str, user_name: str, since_sha: str | None) -> tuple[str | None, int, int]:
    """
    Walks commit history authored by user_name on the default branch, stopping at
    since_sha if given. Returns (newest_sha_seen, additions_delta, deletions_delta).
    """
    query = """
    query($owner: String!, $name: String!, $cursor: String) {
        repository(owner: $owner, name: $name) {
            defaultBranchRef {
                target {
                    ... on Commit {
                        history(first: 100, after: $cursor) {
                            edges {
                                node {
                                    oid
                                    additions
                                    deletions
                                    author { user { login } }
                                }
                            }
                            pageInfo { endCursor hasNextPage }
                        }
                    }
                }
            }
        }
    }"""
    newest_sha = None
    additions = 0
    deletions = 0
    cursor = None
    while True:
        data = graphql_request(query, {"owner": owner, "name": name, "cursor": cursor})
        ref = data["data"]["repository"]["defaultBranchRef"]
        if ref is None:
            return newest_sha, additions, deletions
        history = ref["target"]["history"]
        for edge in history["edges"]:
            node = edge["node"]
            if newest_sha is None:
                newest_sha = node["oid"]
            if node["oid"] == since_sha:
                return newest_sha, additions, deletions
            author = node["author"]["user"]
            if author and author["login"] == user_name:
                additions += node["additions"]
                deletions += node["deletions"]
        if not history["pageInfo"]["hasNextPage"]:
            return newest_sha, additions, deletions
        cursor = history["pageInfo"]["endCursor"]


def compute_total_loc(user_name: str, affiliations: list[str]) -> tuple[int, int, int]:
    """Returns (total_additions, total_deletions, total_net_loc) across all repos, using cache."""
    total_additions = 0
    total_deletions = 0
    for owner, name in fetch_repo_names(user_name, affiliations):
        last_sha, cached_add, cached_del = load_repo_cache(owner, name)
        newest_sha, new_add, new_del = fetch_commit_diff(owner, name, user_name, last_sha)
        additions = cached_add + new_add
        deletions = cached_del + new_del
        if newest_sha:
            save_repo_cache(owner, name, newest_sha, additions, deletions)
        total_additions += additions
        total_deletions += deletions
    return total_additions, total_deletions, total_additions - total_deletions


def set_tspan_by_id(tree: etree._ElementTree, element_id: str, value: str) -> None:
    matches = tree.xpath(f'//*[@id="{element_id}"]')
    if not matches:
        raise ValueError(f"No element with id={element_id!r} found in SVG")
    matches[0].text = value


def update_svg(path: str, values: dict[str, str]) -> None:
    parser = etree.XMLParser(remove_blank_text=False)
    tree = etree.parse(path, parser)
    for element_id, value in values.items():
        set_tspan_by_id(tree, element_id, value)
    tree.write(path, pretty_print=False, xml_declaration=False, encoding="utf-8")


def main() -> None:
    user_name = get_user_name()
    today = datetime.date.today()
    uptime = uptime_string(UPTIME_START, today)

    followers = fetch_followers(user_name)
    commits = fetch_commit_count(user_name)
    owned_repos, stars = fetch_repos_and_stars(user_name, ["OWNER"])
    contributed_repos, _ = fetch_repos_and_stars(user_name, ["OWNER", "COLLABORATOR", "ORGANIZATION_MEMBER"])
    additions, deletions, net_loc = compute_total_loc(user_name, ["OWNER", "COLLABORATOR", "ORGANIZATION_MEMBER"])

    values = {
        "uptime_data": uptime,
        "repo_data": f"{owned_repos:,}",
        "contrib_data": f"{contributed_repos:,}",
        "star_data": f"{stars:,}",
        "commit_data": f"{commits:,}",
        "follower_data": f"{followers:,}",
        "loc_total": f"{net_loc:,}",
        "loc_add": f"{additions:,}",
        "loc_del": f"{deletions:,}",
    }

    assets_dir = os.path.join(os.path.dirname(__file__), "..", "assets")
    update_svg(os.path.join(assets_dir, "profile-card-dark.svg"), values)
    update_svg(os.path.join(assets_dir, "profile-card-light.svg"), values)
    print("Updated profile card SVGs:", values)


if __name__ == "__main__":
    main()

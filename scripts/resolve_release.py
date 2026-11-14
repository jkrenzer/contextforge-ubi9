"""Resolve only published, stable upstream semver releases. No third-party deps."""
import json
import os
import re
import urllib.parse
import urllib.request

TAG = re.compile(r"v[0-9]+\.[0-9]+\.[0-9]+")


def validate_release(release):
    tag = release.get("tag_name", "")
    if release.get("draft") or release.get("prerelease") or not TAG.fullmatch(tag):
        raise ValueError("Expected a published stable vMAJOR.MINOR.PATCH release")
    return tag


def main():
    requested = os.environ.get("REQUESTED_RELEASE", "").strip()
    if requested and not TAG.fullmatch(requested):
        raise ValueError("Release input must be vMAJOR.MINOR.PATCH")
    suffix = "tags/" + urllib.parse.quote(requested, safe="") if requested else "latest"
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "contextforge-ubi9"}
    if os.environ.get("GH_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["GH_TOKEN"]
    request = urllib.request.Request(
        "https://api.github.com/repos/IBM/mcp-context-forge/releases/" + suffix,
        headers=headers,
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        tag = validate_release(json.load(response))
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
        output.write(f"tag={tag}\n")
    print(f"Selected upstream stable release: {tag}")


if __name__ == "__main__":
    main()

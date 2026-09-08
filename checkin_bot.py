# INF601 - Advanced Programming in Python
# Samuel Hart
# Scheduled Check-In Bot

"""
Skeleton for the Scheduled Check-In Bot.

Run by GitHub Actions (see .github/workflows/checkin.yml) on a cron schedule.
This first version proves the plumbing works end to end: it authenticates to
the Practice Hub with the PRACTICE_API_TOKEN environment variable and lists
every post written by the instructor. Collecting attachments and replying to
check-ins get added on top of this in later steps.
"""

import os
import sys

import requests

# All three settings come from the environment so nothing secret lives in
# code. The workflow injects them from GitHub secrets/variables; the defaults
# just make local testing easier (the URL is public info, the token is not).
API_URL = os.environ.get("PRACTICE_API_URL", "https://practice.fhsucyber.com").rstrip("/")
INSTRUCTOR_ID = int(os.environ.get("INSTRUCTOR_ID", "7"))

# The API serves at most 100 posts per request, so we ask for full pages.
PAGE_SIZE = 100


def whoami(headers):
    # GET /api/v1/me — returns the account that owns the token. One cheap
    # call to prove auth works before we try anything else.
    resp = requests.get(f"{API_URL}/api/v1/me", headers=headers)
    resp.raise_for_status()  # raise HTTPError on 4xx/5xx instead of continuing with an error response
    return resp.json()


def list_instructor_posts(headers):
    # GET /api/v1/posts?author=... — returns the instructor's posts as a
    # JSON list, newest first. The endpoint only serves one page at a time,
    # so we walk it with offset until a page comes back short.
    posts = []
    offset = 0
    while True:
        resp = requests.get(
            f"{API_URL}/api/v1/posts",
            headers=headers,
            params={"author": INSTRUCTOR_ID, "limit": PAGE_SIZE, "offset": offset},
        )
        resp.raise_for_status()  # raise HTTPError on 4xx/5xx instead of continuing with an error response
        page = resp.json()
        posts.extend(page)
        # A page smaller than the page size means the API ran out of posts.
        if len(page) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    return posts


def main():
    token = os.environ.get("PRACTICE_API_TOKEN")
    if not token:
        # Missing token is a setup error, not a normal failure — exit
        # non-zero so the Actions run shows red instead of silently
        # doing nothing.
        print("PRACTICE_API_TOKEN is not set — cannot authenticate.")
        sys.exit(1)

    # Every request this bot makes carries the token in this header.
    headers = {"Authorization": f"Bearer {token}"}

    me = whoami(headers)
    print(f"Authenticated as {me['name']} (user id {me['id']})")

    posts = list_instructor_posts(headers)
    print(f"Found {len(posts)} post(s) by instructor {INSTRUCTOR_ID}:")
    for post in posts:
        print(f"  [{post['id']}] {post['title']}")


if __name__ == "__main__":
    main()
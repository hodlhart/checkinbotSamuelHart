# INF601 - Advanced Programming in Python
# Samuel Hart
# Scheduled Check-In Bot

"""
Scheduled Check-In Bot — run by GitHub Actions (.github/workflows/checkin.yml)
on a cron schedule. Two jobs:

  Task 1: archive every instructor post into artifact/ (collected.json with
          the full title/body/tags/timestamps, plus every attachment
          downloaded into artifact/files/).
  Task 2: reply to each check-in post inside its open window (next step).

This version does Task 1 end to end.
"""

import json
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

# Where the graded artifact lives: artifact/collected.json (all posts) and
# artifact/files/ (one copy of every attachment). The workflow commits this
# folder back to the repo after each run.
ARTIFACT_DIR = "artifact"
FILES_DIR = os.path.join(ARTIFACT_DIR, "files")


def whoami(headers):
    # GET /api/v1/me — returns the account that owns the token. One cheap
    # call to prove auth works before we try anything else.
    # Every call in this file passes timeout=30 — without it a hung API
    # would stall the run until the job's own timeout kills it.
    resp = requests.get(f"{API_URL}/api/v1/me", headers=headers, timeout=30)
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
            timeout=30,
        )
        resp.raise_for_status()  # raise HTTPError on 4xx/5xx instead of continuing with an error response
        page = resp.json()
        posts.extend(page)
        # A page smaller than the page size means the API ran out of posts.
        if len(page) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    return posts


def get_post(headers, post_id):
    # GET /api/v1/posts/{id} — returns that one post in full. The list
    # endpoint is the one that could hand back truncated bodies, so every
    # post we archive gets re-fetched on its own to guarantee the complete
    # body made it into the artifact.
    resp = requests.get(f"{API_URL}/api/v1/posts/{post_id}", headers=headers, timeout=30)
    resp.raise_for_status()  # raise HTTPError on 4xx/5xx instead of continuing with an error response
    return resp.json()


def attachment_url(att):
    # Attachment entries carry a download_url relative to the site; glue it
    # onto the API base. An absolute URL (if the server ever sends one)
    # passes through untouched.
    url = att["download_url"]
    return url if url.startswith("http") else f"{API_URL}{url}"


def download_attachments(headers, post):
    # GET each attachment's download_url — returns the raw file bytes with
    # its content type, not JSON. Writing in binary mode because the bytes
    # could be anything (image, PDF, zip...). Each file is saved as
    # {post_id}_{filename}: the post-id prefix keeps same-named attachments
    # on different posts from overwriting each other, and basename() strips
    # any directory components the server might put in the name.
    for att in post.get("attachments", []):
        resp = requests.get(attachment_url(att), headers=headers, timeout=30)
        resp.raise_for_status()  # raise HTTPError on 4xx/5xx instead of continuing with an error response
        safe_name = f"{post['id']}_{os.path.basename(att['filename'])}"
        with open(os.path.join(FILES_DIR, safe_name), "wb") as fh:
            fh.write(resp.content)


def save_collected_json(posts):
    # Write the archived posts as indented JSON so the artifact is readable
    # by the grader's script and by a human clicking around the repo.
    # json.dump needs ensure_ascii=False to keep non-ASCII characters (an
    # em dash in a body, say) readable instead of \u-escaped.
    path = os.path.join(ARTIFACT_DIR, "collected.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(posts, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


def collect(headers):
    # Task 1: archive everything the instructor has posted. The paginated
    # list gives us the ids; each post is then re-fetched in full and its
    # attachments pulled down. Returns the list of full post dicts that
    # end up in collected.json.
    os.makedirs(FILES_DIR, exist_ok=True)  # both json and downloaded files land under here
    collected = []
    for post in list_instructor_posts(headers):
        # If a post is deleted between listing it and fetching it, skip it
        # with a warning instead of failing the whole run — a fresh copy
        # of the archive is still worth committing.
        try:
            full = get_post(headers, post["id"])
        except requests.HTTPError as err:
            print(f"  warning: post {post['id']} disappeared ({err.response.status_code}), skipping")
            continue
        download_attachments(headers, full)
        collected.append(full)
        print(f"  [{full['id']}] {full['title']} — {len(full['attachments'])} attachment(s)")
    save_collected_json(collected)
    return collected


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

    print(f"Collecting posts by instructor {INSTRUCTOR_ID}...")
    collected = collect(headers)
    print(
        f"Archived {len(collected)} post(s) to {ARTIFACT_DIR}/collected.json "
        f"and {len(os.listdir(FILES_DIR))} file(s) to {FILES_DIR}/"
    )


if __name__ == "__main__":
    main()
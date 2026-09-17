### INF601 - Advanced Programming in Python
### Samuel Hart
### Scheduled Check-In Bot


# Scheduled Check-In Bot

A Python program that GitHub Actions runs on a schedule. It talks to the INF601 Practice Hub REST API and does two jobs automatically, with no one at the keyboard: it archives every post the instructor makes, and it replies to each daily check-in while the check-in's reply window is open.

## Description

The bot runs on GitHub's servers via a cron schedule (see `.github/workflows/checkin.yml`): every three hours, eight passes a day. Each run does two things:

**Task 1: collect everything the instructor posts.** The bot pages through all posts authored by the instructor (user id 7), re-fetches each one in full so no body text is ever truncated, and saves the complete post data (titles, bodies, tags, timestamps) to `artifact/collected.json`. Every attached file on every post is downloaded byte-for-byte into `artifact/files/`, saved as `{post_id}_{filename}` so same-named attachments on different posts can't overwrite each other. The workflow then commits the `artifact/` folder back to this repository, so the archive is always reviewable here.

**Task 2: reply to each check-in, on time.** Some instructor posts are "check-ins", recognizable because the title contains the word "check-in" (matched as a whole word, singular or plural, case-insensitive, so ordinary posts can't be mistaken for one). Check-ins only accept replies during a limited time window enforced by the server; reply too early or too late and the API returns `423 Locked` and nothing is saved. The bot replies to each check-in it hasn't already answered (it checks existing comments first, so re-runs never double-post), treats a closed window as routine (it just waits for the next scheduled run) and replies with a short message identifying both the student and the bot.

Robustness details worth knowing: every API call has a 30-second timeout so a hung server can't stall the run, a concurrency guard keeps overlapping runs from racing on the same git push (a queued run waits rather than cancelling the one in flight, so no run's chance at a reply window is thrown away), the commit-back step rebases on the remote before pushing so a moved branch can't cause a rejected push, and a run where nothing changed completes as a green no-op instead of a failure. Each run also wipes `artifact/files/` and regenerates it from scratch, so the artifact always mirrors the instructor's currently visible posts exactly, and an attachment whose post was deleted doesn't linger.

## Getting Started

### Dependencies

* Python 3.13
* Packages listed in `requirements.txt` (one dependency: `requests`):

```
pip install -r requirements.txt
```

### Installing

* Clone the repository:

```
git clone https://github.com/hodlhart/checkinbotSamuelHart.git
cd checkinbotSamuelHart
```

* Create/activate a virtual environment and install requirements (shown with [uv](https://docs.astral.sh/uv/); `python -m venv` + `pip` works too):

```
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

* Configuration: the bot reads three settings from the environment. In GitHub Actions they live under **Settings → Secrets and variables → Actions**:

| Name | Kind | Value |
|---|---|---|
| `PRACTICE_API_TOKEN` | Secret | your Practice Hub API token |
| `PRACTICE_API_URL` | Secret | `https://practice.fhsucyber.com` |
| `INSTRUCTOR_ID` | Variable | `7` |

The token is a secret and is never committed to this repository. GitHub also masks secret values in the run logs, so an accidental print shows up as `***`.

### Executing program

* Locally (token must be exported first):

```
export PRACTICE_API_TOKEN="your-token-here"
python checkin_bot.py
```

* On GitHub: the workflow runs automatically at minute 17 of every third hour UTC (0, 3, 6, 9, 12, 15, 18, 21). That spacing deliberately skips 04:00 to 06:00 UTC, which is 11 PM to 1 AM Central: the assignment asks for no runs there, since a late one could slip past midnight and miss a day's window. Minute 17 rather than 0 avoids GitHub's crowded on-the-hour slots. The eight daily passes are margin, since GitHub drops a share of requested runs. To run it by hand, go to the **Actions** tab → **Scheduled Check-In Bot** → **Run workflow**, or from the terminal with the GitHub CLI:

```
gh workflow run checkin.yml
gh run watch (or gh run watch <run-id> to skip the picker)
```

* Expected output (each run prints its progress):

```
Authenticated as Samuel Hart (user id 8)
Collecting posts by instructor 7...
Archived 0 post(s) to artifact/collected.json and 0 file(s) to artifact/files/
Found 0 check-in post(s) among them
Replied to 0 check-in(s) this run
```

## Help

* `PRACTICE_API_TOKEN is not set; cannot authenticate.` The token environment variable is missing, so export it locally or add it as a repository secret.
* `window closed (423), will retry next run` means the check-in's reply window is shut right now. That is normal, and the next scheduled run retries.
* `already replied, skipping` means the bot found its own earlier comment on that check-in, so it does not double-post.
* `! [rejected] main -> main (fetch first)` during a manual re-run of an old run is fixed by the rebase-before-push in the commit-back step. If you see it, the workflow file predates that fix.
* `No artifact changes to commit` in a run log is not a failure. It means the instructor posted nothing new since the last run.

## Authors

Samuel Hart, [@hodlhart](https://github.com/hodlhart)

## Version History

* 0.4
    * Schedule set to every three hours, which skips the 04:00 to 06:00 UTC block the assignment asks us to avoid while keeping eight passes a day as margin for dropped runs
* 0.3
    * Schedule reliability: added an hourly cron line alongside the two-hourly one, because GitHub delayed or dropped about 57% of the requested runs, and stopped cancelling an in-flight run when the next tick arrives
* 0.2
    * Task 2: check-in detection, in-window replies, duplicate and 423 handling
    * Review fixes: request timeouts, concurrency guard, unique attachment names, job timeout, word-boundary matching, plural check-in titles, per-reply error isolation, rebase-before-push
* 0.1
    * Initial release: skeleton, Task 1 collection, scheduled workflow with artifact commit-back

## License

This project is coursework for INF601 and is not licensed for reuse.

## Acknowledgments

* [Practice Hub API reference](https://practice.fhsucyber.com/docs-guide)
* README structure adapted from [awesome-readme](https://github.com/matiassingers/awesome-readme) and [PurpleBooth](https://gist.github.com/PurpleBooth/109311bb0361f32d87a2)

## AI Usage

* **Claude Code** wrote the bot skeleton, the Task 1 collection logic, the Task 2 reply logic, and the GitHub Actions workflow, working from written prompts that specified each requirement. Three review rounds produced most of the hardening: request timeouts, a run-concurrency guard, unique attachment filenames and a job timeout; then word-boundary check-in matching, per-reply error isolation and the race-window note; and finally the rebase-before-push fix for the rejected push. Claude Code also flagged on its own that its word-boundary pattern would miss plural titles like "weekly check-ins", which became the `s?` plural-match fix.

* **I (Sam Hart)** set up the repository and authentication, configured the three Actions secrets and variables, wrote the prompts each piece was built from, and ran and verified every workflow run. I also decided the shape of the artifact: it wipes `artifact/files/` and rebuilds it each run, so the folder mirrors the instructor's currently visible posts instead of accumulating files whose posts were deleted.

* **Changes I made to AI-generated code.** The schedule is mine. I read the Actions history instead of trusting the cron line, found that roughly half of all requested runs never started (GitHub delays and drops scheduled runs under load), and changed the workflow twice because of it: first adding an hourly line alongside the two-hourly one, then reducing the whole thing to `17 */3 * * *`. The second change was to comply with the assignment's instruction not to schedule between 04:00 and 06:00 UTC, and three-hour spacing skips that block on its own. I also changed `cancel-in-progress` from true to false, because with more frequent runs a cancelled run is a lost chance to catch a reply window. Separately, I stress-tested the workflow by re-running completed runs, which surfaced a rejected push that the bot had never hit in normal operation; the rebase-before-push block came out of that. I cut one line from an earlier draft of this section, a claim that I could explain every function and every line of the YAML, because it claimed competence instead of describing work.
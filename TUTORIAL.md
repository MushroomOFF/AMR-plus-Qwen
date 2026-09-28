# Tutorial — Set Up AMR on Your Own Machine & GitHub Actions with Your Personal Artists List

This tutorial walks you through running the whole project **for yourself**:
a fresh database, **your** artists list, new releases found automatically from
Apple Music — first locally, then fully automated in **your own GitHub
Actions**, optionally publishing a GitHub Pages site and posting to your own
Telegram channel.

> Difficulty: beginner-friendly. Commands are shown for macOS/Linux;
> on Windows use `py -3` instead of `python3` and `\`-style paths.
> Parts 1–2 (local run) need **no accounts and no tokens at all**.

---

## Part 0 — What you need

- Python 3.12+ (`python3 --version`)
- Git
- Internet access (the public iTunes Search API is used — **no Apple account needed**)
- A GitHub account (only for Part 3 — cloud automation)
- *(Optional)* Telegram bot token + channel/chat IDs, Yandex.Music and Zvuk
  tokens — only if you want notifications and those streaming services.
  **Everything else works without them.**

---

## Part 1 — Local setup

### Step 1.1 — Clone the repository (or your fork)

```bash
git clone <repo-url> amr
cd amr
```

### Step 1.2 — Virtual environment and dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r "Python Scripts/requirements.txt"
```

Dependencies: `requests`, `pandas`, `python-dotenv`, `yandex-music`.

### Step 1.3 — Paths: mostly automatic ✅

Most scripts compute the repo root themselves:

```python
ROOT_FOLDER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
```

and load `.env` from the repo root. You do **not** need to edit them.

One exception: `Python Scripts/server.py` (the optional local web server) has
the author's path hard-coded near the top of the file:

```python
# BEFORE (author's machine):
ROOT_FOLDER = '/Users/mushroomoff/Yandex.Disk.localized/GitHub/mushroomoff.github.io/'

# AFTER (your machine), or just copy-paste this portable line:
ROOT_FOLDER = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/'
```

Only do this if you plan to run `server.py` (Step 1.9). All other scripts work
as-is.

### Step 1.4 — Create `.env` (optional but recommended)

Create a `.env` file in the repository root (it is git-ignored). Even if you
skip Telegram/YM/Zvuk, create it with empty values so nothing crashes:

```dotenv
# Telegram — create a bot via @BotFather; chat/channel IDs via @userinfobot
tg_token=
tg_channel_id=
tg_logger_id=
# Streaming services (browser cookies after login) — optional
ym_token=
zv_token=
# Local web server admin — optional
admin_token=
```

With empty Telegram values, `amr_functions.send_message()` simply skips
sending (you will see *"Message not sent! No TOKEN or CHAT_ID"* in
`status.log`) and everything keeps working locally.

### Step 1.5 — Start with a clean database

The repo ships with the author's `Databases/music_releases.db`. For a personal
run, delete it — the schema is recreated automatically on first script run:

```bash
rm Databases/music_releases.db
```

> Keep `Databases/Backups/*.json` only if you want the author's data as a
> starting point — otherwise delete them too; they are just JSON exports.

### Step 1.6 — Build YOUR personal artists list

Artists live in the `artists` table. The quickest way to fill it is SQL:

```bash
sqlite3 Databases/music_releases.db <<'SQL'
CREATE TABLE IF NOT EXISTS artists (
    row_id INTEGER,
    artist TEXT,
    artist_id INTEGER,
    artist_genre TEXT,
    update_type INTEGER,
    update_date TEXT DEFAULT NULL,
    PRIMARY KEY(row_id AUTOINCREMENT)
);
INSERT INTO artists (artist, artist_id, artist_genre, update_type, update_date) VALUES
    ('Power Paladin', 1540478964, 'Power Metal',  2, NULL),
    ('Mob Rules',     286753887,  'Heavy Metal',  2, NULL),
    ('My New Band',   123456789,  'Rock',         1, NULL);
SQL
```

Field meanings:

| Field | Meaning |
|---|---|
| `artist` | Display name of the artist |
| `artist_id` | Apple Music **artist ID** (see below); must be `> 0` |
| `artist_genre` | Free-text label |
| `update_type` | Priority tier: `2` = checked weekly in CI & interactive filters, `1` = regular, `0` = only when you choose "ALL" |
| `update_date` | `NULL` = needs checking; a timestamp = last processed date |

**Finding an artist ID** — open the artist's page on Apple Music and copy the
number from the URL:

```
https://music.apple.com/us/artist/power-paladin/1540478964
                                            ^^^^^^^^^^ artist_id
```

Or search via the public API:

```bash
curl -s "https://itunes.apple.com/search?term=power+paladin&entity=musicArtist&limit=3" \
  | python3 -c "import json,sys; [print(r['artistName'], r['artistId']) for r in json.load(sys.stdin)['results']]"
```

**Alternative: keep the list in JSON.** Edit `Databases/Backups/artists.json`
(same fields — see the shipped example) and import it into SQLite:

```bash
cd "Python Scripts"
python AMR_DB_Sync.py --db ../Databases/music_releases.db --json-dir ../Databases/Backups
# a dry-run diff is shown first — answer y to apply
```

### Step 1.7 — First scan: find new releases

```bash
cd "Python Scripts"
python AMR_LookApp.py
```

It asks interactively:

```
Choose countries to check: [us, ru, jp] / 2:[us, ru] / jp:[jp]
Choose artists to check:   Enter:[2,1] / 2 / 1 / 0:! ALL [2,1,0]
```

Pick your countries and artist tiers. The script walks through every artist
with `update_date IS NULL`, queries iTunes for their albums, skips releases
already in `my_releases`, inserts genuinely new ones, prints progress and logs
to `status.log` in the repo root. Typical per-artist statuses: `N new records`,
`EMPTY` (no albums in that country store), `ERROR (50x)` (API hiccup — retry
later with `AMR_LookApp_Errors.py`).

### Step 1.8 — Verify and back up

```bash
sqlite3 ../Databases/music_releases.db \
  "SELECT main_artist, album, release_date FROM my_releases ORDER BY release_date DESC LIMIT 10;"

python AMR_DB_Backup.py    # dumps DB tables → Databases/Backups/*.json
```

### Step 1.9 — Website & local server (optional)

```bash
python server.py           # after editing ROOT_FOLDER in Step 1.3
# open http://localhost:8000/index.html
```

For a purely static preview, any static server works:

```bash
python3 -m http.server 8000 -d Website
```

### Step 1.10 — Make it a habit

- Re-run `AMR_LookApp.py` whenever you like (weekly matches the CI cadence).
  To force a full re-scan, reset progress:
  ```sql
  UPDATE artists SET update_date = NULL WHERE update_type IN (1, 2);
  ```
- Add new favorite artists anytime (Step 1.6) — the next run picks them up.

✅ At this point the project is fully yours and runs 100 % locally.
Continue to Part 2 for cloud automation, Part 3 for GitHub Pages, Part 4 for
Telegram. You can stop here — nothing in the cloud runs until you enable it.

---

## Part 2 — Run it in YOUR GitHub Actions

The repo already contains four workflows in `.github/workflows/`:

| Workflow | Trigger | What it does |
|---|---|---|
| `amr-weekly-update.yml` | Fri 04:00 UTC | `AMR_LookApp.py` + `AMR_NewReleases.py`, commits & pushes results |
| `amr-zvym.yml` | daily 06:09 UTC | `AMR_ZVYM.py` (Yandex.Music / Zvuk lookup) |
| `amr_manual-run.yml` | manual button | runs the pipeline once, no commit/push |
| `amr-deploy.yml` | push to `Website/**` | deploys `Website/` to GitHub Pages |

### Step 2.1 — Push your personal data

Commit the files that define *your* setup:

```bash
git add Databases/music_releases.db Databases/Backups "Python Scripts" README.md TUTORIAL.md
git commit -m "Personal setup: my artists list"
git push origin main
```

(If you manage the list only in `artists.json`, commit that; the DB will be
rebuilt by the scripts and auto-committed by the workflow.)

### Step 2.2 — Enable scheduled workflows

On a **fork**, GitHub disables scheduled workflows by default. Go to
**Actions** → open *AMR Weekly Update* → **Enable workflow**.

### Step 2.3 — Secrets (optional features)

The workflows map GitHub **secrets** to the env vars the scripts read
(`Settings → Secrets and variables → Actions → New repository secret`):

| Secret | Env var in workflow | Needed for |
|---|---|---|
| `TG_TOKEN` | `tg_token` | Telegram posts/logging |
| `TG_CHANNEL_ID` | `tg_channel_id` | Your releases channel |
| `TG_LOGGER_ID` | `tg_logger_id` | Bot error-log chat |
| `YM_TOKEN` | `ym_token` | Yandex.Music lookup |
| `ZV_TOKEN` | `zv_token` | Zvuk lookup |

**You can skip all of them.** On GitHub the scripts detect
`GITHUB_ACTIONS=true`, set `ROOT_FOLDER=''` and use repo-relative paths; with
empty tokens Telegram sends are skipped and `AMR_ZVYM.py` finds nothing — the
weekly LookApp pipeline still works and commits new releases for your artists.

### Step 2.4 — Fix the commit identity (one-minute edit)

Each data-committing workflow contains the author's git identity:

```yaml
git config --local user.email "mushroomoff@mail.ru"
git config --local user.name "MushroomOFF"
```

Change these two lines in `amr-weekly-update.yml` and `amr-zvym.yml` to your
name/email (any valid address works; use
`<your-id>+<username>@users.noreply.github.com` to keep yours private).

### Step 2.5 — Test the pipeline manually

**Actions → Manual run → Run workflow.** Watch the log: it checks out your
repo, installs requirements, runs the scripts and pushes a commit like
*"AMR autoupdate…"* with updated DB/JSON files. From now on it repeats every
Friday automatically.

> Note: the scheduled/manual workflows run against the committed database in
> your repo. If you also develop locally, run `AMR_DB_Backup.py` and push your
> JSON/DB before the Friday job, so both sides stay in sync.

---

## Part 3 — Publish the website with YOUR data (GitHub Pages)

1. **Settings → Pages → Source:** select **GitHub Actions** (the
   `amr-deploy.yml` workflow uses `actions/deploy-pages`).
2. That workflow deploys the `Website/` folder whenever its files change —
   which happens automatically when the weekly job commits refreshed
   `new_releases.json` / `soon_releases.json`. Or trigger it manually once.
3. Your site appears at `https://<your-username>.github.io/<repo-name>/`.
4. Optional: edit `Website/index.html` / icons / `manifest.webmanifest` to
   rename the site for yourself.

---

## Part 4 — Telegram notifications (optional)

1. Create a bot with **@BotFather** → copy the token → repo secret `TG_TOKEN`
   (and `.env` locally).
2. Create your channel (or topic group), add the bot as admin with
   *post messages* permission → get the numeric ID (via @userinfobot or
   `https://api.telegram.org/bot<TOKEN>/getUpdates`) → secret `TG_CHANNEL_ID`.
3. Optionally make a private chat with the bot for run/error logs →
   `TG_LOGGER_ID`.
4. `AMR_NewReleases.py` will now post formatted new-release messages to your
   channel after each run.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `FileNotFoundError` on `Databases/...` locally | Wrong `ROOT_FOLDER` (only relevant for `server.py`) — redo Step 1.3; path must end with `/` |
| `KeyError: 'tg_token'` | Missing `.env` (Step 1.4) |
| `Bad ID` in log | `artist_id` ≤ 0 or wrong — fix in the `artists` table |
| Many `ERROR (502/503)` | Apple API throttling — wait, then run `AMR_LookApp_Errors.py` |
| Nothing found for an artist | No albums in that country store (`EMPTY`) or all releases already known |
| Scheduled workflow never runs | Not enabled after forking (Step 2.2) or cron timezone confusion (all crons are UTC) |
| Push from workflow fails (`Permission denied`) | Fork Settings → Actions → General → Workflow permissions → **Read and write** |
| Pages shows old data | Check Settings → Pages source is *GitHub Actions*; run `amr-deploy` manually |

Happy listening! 🤘

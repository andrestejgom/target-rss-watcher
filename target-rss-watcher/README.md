# target-rss-watcher

An unofficial, synthetic RSS feed for the ECB's **TARGET Professional Use**
documentation pages (Common components, T2, T2S, TIPS, ECMS, Pontes).

The ECB does not publish an RSS feed for these pages. This tool checks them
every hour, detects new, revised, silently-replaced, or removed documents,
and publishes those changes as a standard RSS feed you can subscribe to in
Feedly, Thunderbird, Outlook, or any RSS reader.

**This tool does not copy or mirror ECB content.** It only records titles,
dates, links, and a SHA-256 fingerprint of each linked file, so it can tell
when something changed. Every feed entry links back to the original ECB
page or file. The ECB remains the sole authoritative source.

## Why a headless browser is needed

The "Documents and links" section on these ECB pages is rendered
client-side (with JavaScript) — a plain HTTP fetch only returns an empty
heading. This project uses [Playwright](https://playwright.dev/) (headless
Chromium) to render the page first, then parses the resulting HTML.

## How it works

```
scraper.py   -> renders each page with Playwright, extracts every link to a
                document file (.pdf, .zip, .xsd, .xlsx, ...) in the main
                content area, along with its title, nearby date, and any
                "with revisions" / "updated" style annotation
hasher.py    -> downloads each linked file (streamed, capped at 25 MB) and
                computes a SHA-256 fingerprint
diff.py      -> compares this run's findings against data/inventory.json
                (saved from the previous run) and produces a list of
                Change events: new_document, content_replaced,
                revision_marked, metadata_changed, document_removed
feed.py      -> prepends new Change events to docs/feed.xml (RSS 2.0),
                keeping the most recent 300 items
inventory.py -> loads/saves data/inventory.json, the state file that lets
                each run know what the previous run already saw
main.py      -> orchestrates all of the above for every page in
                src/config.py's WATCHED_PAGES list
```

## One-time setup

### 1. Create the repository

Create a **new, independent GitHub repository** (public or private — public
is required for free GitHub Pages on a free personal account) and push this
project to it:

```bash
cd target-rss-watcher
git init
git add .
git commit -m "Initial commit: TARGET Professional Use RSS watcher"
git branch -M main
git remote add origin https://github.com/<your-username>/<repo-name>.git
git push -u origin main
```

### 2. Enable GitHub Pages

In the repository on GitHub: **Settings → Pages**.

- Source: **Deploy from a branch**
- Branch: **main**, folder: **/docs**
- Save.

After a minute or two, your feed will be live at:

```
https://<your-username>.github.io/<repo-name>/feed.xml
```

### 3. Point the feed's metadata at that URL

Edit `src/config.py` and replace the placeholder:

```python
FEED_SELF_URL = "https://<your-username>.github.io/<repo-name>/feed.xml"
```

with your real URL, then commit and push:

```bash
git add src/config.py
git commit -m "Set real feed URL"
git push
```

(This is cosmetic — it only affects the `<atom:link rel="self">` tag some
readers use for auto-discovery. The feed works without it too.)

### 4. Check GitHub Actions permissions

**Settings → Actions → General → Workflow permissions**: make sure
**"Read and write permissions"** is selected. The hourly job needs this to
commit `docs/feed.xml` and `data/inventory.json` back to the repository.

### 5. Run it once manually

**Actions tab → "Check TARGET Professional Use pages" → Run workflow.**

Watch the run. The first run will populate `data/inventory.json` for the
first time — since there's no *previous* run to compare against, it should
report each currently-listed document as a `new_document` (this is
expected and correct: it establishes the baseline). From the second run
onward, the feed will only show real changes.

After that, it just runs hourly on the schedule in
`.github/workflows/check.yml` (`cron: "7 * * * *"`).

### 6. Subscribe

Add `https://<your-username>.github.io/<repo-name>/feed.xml` to your RSS
reader. Done — updates will arrive as if the ECB offered the feed directly.

## Running locally (optional, for testing/debugging)

```bash
pip install -r requirements.txt
python -m playwright install --with-deps chromium
python -m src.main
```

This scrapes all six pages once, updates `docs/feed.xml`, and updates
`data/inventory.json` — exactly what the hourly job does.

### Inspecting a single page

If extraction ever finds zero documents on a page (ECB changed the
markup), dump the fully-rendered HTML to look at it directly:

```bash
python -m src.scraper "https://www.ecb.europa.eu/paym/target/target-professional-use-documents-links/ecms/html/index.en.html" --dump ecms_dump.html
```

Then open `ecms_dump.html` and check how the document list is structured
now. `extract_document_links()` in `src/scraper.py` is intentionally
generic (it scans for any `<a href>` pointing at a document file inside
`#main-content`), so it should keep working through most markup tweaks —
but a full redesign of the "Documents and links" widget may require
adjusting the selector logic there.

### Running the offline tests

No network or browser needed — these test the parsing/diff/feed logic
against local HTML fixtures:

```bash
python tests/test_pipeline.py
```

## Adding or removing a watched page

Edit `WATCHED_PAGES` in `src/config.py`:

```python
WatchedPage(
    key="pontes",
    label="Pontes",
    url="https://www.ecb.europa.eu/paym/target/target-professional-use-documents-links/pontes-documents-links/html/index.en.html",
),
```

`key` becomes the top-level field name in `data/inventory.json` and the
RSS `<category>` tag — keep it short, lowercase, no spaces.

## Tuning

All of these live in `src/config.py`:

| Setting | Purpose |
|---|---|
| `DOCUMENT_EXTENSIONS` | Which file types count as "documents" |
| `MAX_HASH_BYTES` | Skip hashing files larger than this (metadata is still tracked) |
| `DELAY_BETWEEN_REQUESTS_SECONDS` | Politeness delay between file downloads |
| `MAX_FEED_ITEMS` | How many recent items feed.xml keeps |

## Limitations

- The watcher reports changes **after** the ECB publishes or modifies
  something — it cannot predict a document that doesn't exist yet.
- An hourly run can occasionally be delayed by a few minutes (GitHub
  Actions' scheduler is best-effort, not real-time) — fine for release
  documentation, not for anything requiring second-level precision.
- Every feed entry links to the official ECB file or page. The feed is a
  notification layer; the ECB is always the source of truth.
- If ECB's frontend changes significantly, extraction may need updating —
  see "Inspecting a single page" above.

## License / disclaimer

This is an independent personal tool with no affiliation to, endorsement
by, or connection to the European Central Bank. All linked documents and
pages belong to the ECB; this project only stores metadata (titles, dates,
links, hashes) needed to detect changes, never document content itself.

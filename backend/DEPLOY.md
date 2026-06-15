# Backend deploy - the ONE manual step (about 3 minutes)

This is the only thing that has to be done by hand. Do it once, before the talk.

The pages are static (GitHub Pages), so they need a tiny external endpoint to
save and read answers. We use a Google Apps Script Web App that appends each
answer to a Google Sheet (the exact pattern Event 1 used) - plus a `doGet` that
hands answers back as JSON (and JSONP) so the live results page and the takeaway
image can read them.

**ONE deploy serves everything.** The single script powers BOTH polls and BOTH
live pages. On first write it auto-creates two tabs in the one spreadsheet:

| Tab | Columns | What it holds |
|---|---|---|
| `Poll1` | Timestamp, Name, Token, Answer, Event | the one-word poll |
| `Poll2` | Timestamp, Name, Token, Changed, Answer, Event | the yes/no + their one word now |

You do **not** create the tabs by hand - the script makes them (with a bold,
frozen header row) the first time each poll gets a response.

**`Token` is a silent per-device id** (a random value stored on each phone, no
email, no login). Because `/poll` and `/changed` are the same site, a phone uses
the **same** Token on both - so the same person's start answer (Poll1) and end
answer (Poll2) share a Token and can be joined later. The live "before vs after"
view doesn't even need the join (it compares totals), but the Token is there if
you want per-person movement afterwards.

## Steps

1. Go to **https://sheets.google.com** and create a **new blank spreadsheet**.
   Name it: `AI Club Event 03 - Poll`.

2. In that sheet's menu: **Extensions > Apps Script**.

3. Delete whatever code is in the editor, then **paste the entire contents of
   `apps-script.gs`** (the file next to this one).

4. **Save** (Cmd+S). Name the project `Event 3 Poll` if it asks.

5. Click **Deploy > New deployment**.
   - Click the gear next to "Select type" and choose **Web app**.
   - **Execute as:** Me
   - **Who has access:** **Anyone**  (this matters - phones submit anonymously)
   - Click **Deploy**.

6. Google shows a permissions prompt the first time. Click **Authorize access**,
   pick your Google account, click **Advanced > Go to Event 3 Poll (unsafe)**,
   then **Allow**. (It says "unsafe" because it's your own unverified script -
   that's normal.)

7. Copy the **Web app URL** it gives you. It looks like (THIS IS JUST AN EXAMPLE
   URL - use the one Google actually gives you):

   ```
   https://script.google.com/macros/s/AKfycbEXAMPLEonlyEXAMPLEonly12345/exec
   ```

8. Sanity check: paste that URL into a browser. You should see
   `{"status":"ok","service":"event-three poll","type":"poll1","count":0,"responses":[]}`.
   (Add `?type=poll2` to the URL to check the other poll the same way.)

## Wire it into EVERY page - paste the URL ONCE

There is now a single shared config file, `config.js`, at the repo root. Every
page (poll, results, changed) reads the endpoint from it - so you paste the URL
**once**, not three times.

9. Open `config.js` (repo root) and replace the placeholder:

   ```js
   window.AI_CLUB_ENDPOINT = "__PASTE_APPS_SCRIPT_WEB_APP_URL__";
   ```

   with the URL from step 7:

   ```js
   window.AI_CLUB_ENDPOINT = "https://script.google.com/macros/s/AKfyc...../exec";
   ```

   Then commit and push:

   ```bash
   cd /path/to/event-three
   git add config.js
   git commit -m "Wire AI Club endpoint into config.js"
   git push
   ```

   GitHub Pages redeploys in ~30-60s. That's the poll, the live results board,
   and the yes/no page all wired in one go.

## The takeaway image (end of talk)

The takeaway generator can take the URL at run time (no editing needed):

```bash
python3 "~/Desktop/Code with Claude Debriefed/poll_takeaway.py" --endpoint "<your /exec URL>"
```

- default = themed leaderboard PNG from Poll1
- `--ai` = let Claude tidy the "Other" bucket (needs `ANTHROPIC_API_KEY`; falls
  back to printing a paste-ready prompt if there's no key)
- `--changed` = the yes/no result card from Poll2

## 60-second smoke test (do this once the endpoint is pasted + pushed)

This proves the silent device-token matching end to end on a real phone:

1. On **phone A**, open `.../event-three/poll`, enter a name + one word, submit.
2. On the **same phone A**, open `.../event-three/changed`, pick Yes/No and type a
   word, submit.
3. Open the Google Sheet:
   - `Poll1` has one new row, `Poll2` has one new row.
   - **The `Token` value is identical in both rows.** That is the same-device
     match working (no email needed).
4. Open `.../event-three/results/?view=beforeafter` - you should see your two
   answers reflected in the start/now counts and the Yes/No headline.

If the two Token values match, you're done. (Different tokens would mean the two
pages aren't same-origin - they are, so they will match.)

That's it. No secrets live in this repo - the data lives only in your Google Sheet.

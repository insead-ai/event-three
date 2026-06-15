# Backend deploy - the ONE manual step (about 3 minutes)

This is the only thing that has to be done by hand. Do it once, before the talk.

The poll page is static (GitHub Pages), so it needs a tiny external endpoint to
save answers. We use a Google Apps Script Web App that appends each answer to a
Google Sheet (the exact pattern Event 1 used) - plus a `doGet` that hands the
answers back as JSON so the takeaway image can be generated with one command.

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

7. Copy the **Web app URL** it gives you. It looks like:
   `https://script.google.com/macros/s/AKfyc.....iks/exec`

8. Sanity check: paste that URL into a browser. You should see
   `{"status":"ok","service":"event-three poll","count":0,"responses":[]}`.

## Wire it into the live poll page

9. In the deployed poll repo, open `poll/index.html`, find this line near the
   bottom:

   ```js
   const ENDPOINT = "__PASTE_APPS_SCRIPT_WEB_APP_URL__";
   ```

   Replace the placeholder with the URL from step 7, commit and push:

   ```bash
   cd /path/to/event-three
   git add poll/index.html
   git commit -m "Wire poll endpoint"
   git push
   ```

   GitHub Pages redeploys in ~30-60s.

## Wire it into the takeaway generator

10. Either edit the default in `~/.claude/scripts/event-three-poll/poll_takeaway.py`
    (the `DEFAULT_ENDPOINT` constant near the top), or just pass it at run time:

    ```bash
    python3 ~/.claude/scripts/event-three-poll/poll_takeaway.py --endpoint "PASTE_THE_/exec_URL_HERE"
    ```

That's it. No secrets live in this repo - the data lives only in your Google Sheet.

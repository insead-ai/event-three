# INSEAD AI Club - Event 3: Code with Claude, Debriefed

Live audience poll for Event 3 (Mon 15 June 2026). One question, answered on
phones, with a deck-styled takeaway image generated at the end of the talk.

**Live poll:** https://insead-ai.github.io/event-three/poll

## The question

> In one word: the most important skill for being good at AI?

Attendees enter their **name** and their **one-word answer**, then submit. They
get a friendly confirmation screen.

## How it fits together

```
 Phone (poll/index.html on GitHub Pages)
        |  fetch POST {name, answer, timestamp, event}  (mode: no-cors)
        v
 Google Apps Script Web App  (backend/apps-script.gs)
        |  appends a row
        v
 Google Sheet  "AI Club Event 03 - Poll"   <- the only place response data lives
        ^
        |  GET -> { responses: [...] }  (doGet returns rows as JSON)
        |
 poll_takeaway.py  (~/.claude/scripts/event-three-poll/)  -> 1280x720 PNG for the deck
```

This reuses the proven Event 1 / `insead-ai/poll` collection pattern (Apps Script
`doPost` appending to a Sheet, front-end `fetch` with `mode: 'no-cors'`). The one
addition is a richer `doGet` that returns every response as JSON, so the end-of-talk
takeaway is a single command instead of a manual CSV export.

## Contents

| Path | What it is |
|---|---|
| `poll/index.html` | The live poll page. Deck-styled (cream/coral, Lora + Inter). Mobile-first. |
| `backend/apps-script.gs` | Google Apps Script: `doPost` saves an answer, `doGet` returns all answers as JSON. |
| `backend/DEPLOY.md` | The one-time, idiot-proof deploy guide (the single manual step). |

## Setup

1. Deploy the backend - follow `backend/DEPLOY.md` (about 3 minutes, one time).
2. Paste the Web App URL into `poll/index.html` (`const ENDPOINT = ...`) and push.
3. At the end of the talk, run the takeaway generator (see below).

## End-of-talk takeaway image

```bash
python3 ~/.claude/scripts/event-three-poll/poll_takeaway.py --endpoint "<your /exec URL>"
```

It fetches the responses, renders a deck-styled word cloud / ranked-words card
(1280x720 PNG) into the deck bundle folder, and reveals it in Finder. Run
`--help` for options. With no endpoint set it renders against clearly-labelled
sample data so you can preview the design.

## Privacy

This repo is public. It contains **no response data and no secrets**. All answers
live only in the private Google Sheet behind the Apps Script endpoint.

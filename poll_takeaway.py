#!/usr/bin/env python3
"""
Event 3 poll - end-of-talk takeaway image generator (v2, themed).

Fetches the live poll responses from the Google Apps Script endpoint and renders
a deck-styled 1280x720 PNG. The DEFAULT view is a themed leaderboard: every
one-word answer is bucketed into a theme (via the shared themes.json, the same
file the live /results dashboard uses, so they never drift), then drawn as a
ranked set of coral bars, biggest first.

Modes:
    (default)     themed leaderboard of poll 1 (the one-word answers)
    --ai          hybrid polish: ask Claude to sort the "Other" words into the
                  best existing theme, merge, re-render. No key/offline -> prints
                  the Other words + a paste-ready prompt instead. Never crashes.
    --changed     render a yes/no result card from poll 2

Reuses the deck's exact palette and Lora/Inter look (Georgia + Helvetica Neue
stand in locally for Lora + Inter). Pure Pillow + requests - no heavy deps.

Usage:
    python3 poll_takeaway.py                       # themed leaderboard (live, or sample)
    python3 poll_takeaway.py --endpoint "<URL>"    # the Apps Script /exec URL
    python3 poll_takeaway.py --ai                  # + Claude sorts the Other bucket
    python3 poll_takeaway.py --changed             # yes/no result card (poll 2)
    python3 poll_takeaway.py --sample              # force sample data (preview design)
    python3 poll_takeaway.py --out /some/file.png  # override output path
    python3 poll_takeaway.py --no-open             # don't reveal in Finder

The end-of-talk command Freddie runs:
    python3 "~/Desktop/Code with Claude Debriefed/poll_takeaway.py" --endpoint "<your /exec URL>"
"""

import argparse
import json
import os
import subprocess
import sys
from collections import Counter

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    sys.exit("Pillow is required:  pip3 install --user pillow")

# ----------------------------------------------------------------------------
# Config
# ----------------------------------------------------------------------------

# Paste the Apps Script Web App /exec URL here to make a bare run work with no flags.
DEFAULT_ENDPOINT = "__PASTE_APPS_SCRIPT_WEB_APP_URL__"

DEFAULT_OUT = os.path.expanduser(
    "~/Desktop/Code with Claude Debriefed/event3_poll_takeaway.png"
)

W, H = 1280, 720

# Deck design tokens (match deck_master.html exactly)
PAPER    = (250, 249, 245)   # #FAF9F5
CARD     = (244, 242, 236)   # #F4F2EC
INK      = (20, 20, 19)      # #141413
INK_SOFT = (138, 135, 128)   # #8A8780
INK_MID  = (92, 90, 83)      # #5C5A53
ACCENT   = (217, 119, 87)    # #D97757
LINE     = (226, 223, 214)   # #E2DFD6
MINT     = (207, 230, 224)   # #cfe6e0
ACCENT_SOFT = (224, 163, 142)  # muted coral for non-leading bars
NEUTRAL  = (201, 197, 185)   # the "No" segment

# Theme order = precedence (must match results/index.html THEME_ORDER).
THEME_ORDER = [
    "Communication", "Judgement & Taste", "Curiosity & Adaptability",
    "Technical / Coding", "Prompting", "Creativity", "Critical thinking",
    "Business & Domain", "Other",
]

# Embedded fallback if themes.json cannot be read (kept in sync with the file).
FALLBACK_THEMES = {
    "Communication": ["communication", "communicate", "communicating", "clarity", "clear", "articulat", "listening", "listen", "writing", "write", "explain", "language", "expression", "storytelling", "narrative", "persuasion", "persuade", "empathy", "empathetic", "speaking", "presentation", "presenting", "influence"],
    "Judgement & Taste": ["judgement", "judgment", "judging", "taste", "discernment", "discern", "decision", "decisive", "wisdom", "intuition", "common sense", "evaluation", "evaluate", "discretion", "selectivity", "humility", "humble", "patience", "patient", "discipline", "integrity", "maturity", "pragmatism", "pragmatic"],
    "Curiosity & Adaptability": ["curiosity", "curious", "adaptability", "adaptable", "adapt", "learning", "willingness to learn", "openness", "open-minded", "open mind", "agility", "agile", "flexibility", "flexible", "experimentation", "experiment", "exploration", "exploring", "explore", "growth", "grit", "resilience", "perseverance", "persistence", "persistent", "tenacity"],
    "Technical / Coding": ["coding", "to code", "python", "technical", "engineering", "engineer", "programming", "programmer", "program", "developer", "software", "datasets", "data science", "maths", "mathematics", "statistics", "algorithm", "machine learning", "modelling", "modeling"],
    "Prompting": ["prompting", "prompts", "prompt", "instructing", "instruction", "questioning", "asking good questions", "context-setting"],
    "Creativity": ["creativity", "creative", "imagination", "imaginative", "vision", "visionary", "originality", "original", "ideation", "inventive", "invention", "innovation", "innovative", "artistry"],
    "Critical thinking": ["critical", "reasoning", "logic", "logical", "analysis", "analytical", "analyse", "analyze", "thinking", "first principles", "scepticism", "skepticism", "sceptical", "skeptical", "verification", "verify", "rigour", "rigor", "rigorous", "problem-solving", "problem solving", "problemsolving"],
    "Business & Domain": ["business", "domain", "industry", "strategy", "strategic", "commercial", "commerciality", "market", "value creation", "product sense", "customer", "execution", "delivery", "outcomes", "leadership", "management", "focus", "prioritisation", "prioritization", "ownership", "delegation"],
    "Other": [],
}

# Candidate fonts: serif stands in for Lora, sans for Inter. First that exists wins.
SERIF_CANDIDATES = [
    "/Library/Fonts/Lora-Medium.ttf",
    os.path.expanduser("~/Library/Fonts/Lora-Medium.ttf"),
    "/System/Library/Fonts/Supplemental/Georgia.ttf",
    "/System/Library/Fonts/Supplemental/Times New Roman.ttf",
]
SANS_CANDIDATES = [
    "/Library/Fonts/Inter-Regular.ttf",
    os.path.expanduser("~/Library/Fonts/Inter-Regular.ttf"),
    "/System/Library/Fonts/HelveticaNeue.ttc",
    "/System/Library/Fonts/Helvetica.ttc",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
]

SAMPLE = [
    "curiosity", "Curiosity", "judgement", "taste", "patience", "curiosity",
    "context", "judgement", "communication", "curiosity", "iteration",
    "taste", "humility", "judgement", "curiosity", "clarity", "context",
    "patience", "taste", "writing", "communication", "judgement", "delegation",
    "context", "taste", "curiosity", "asking", "verification", "judgement",
    "curiosity", "imagination", "coding", "persistence", "prompting",
    "listening", "reasoning", "strategy", "adaptability", "prompts",
]

SAMPLE_CHANGED = (
    ["yes"] * 27 + ["no"] * 13
)


def _load_font(candidates, size):
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _text_size(draw, text, font):
    box = draw.textbbox((0, 0), text, font=font)
    return box[2] - box[0], box[3] - box[1]


# ----------------------------------------------------------------------------
# Themes
# ----------------------------------------------------------------------------

def load_themes():
    """Load the shared themes.json sitting next to this script's repo copy.

    Looks next to the script first (repo layout), then the Desktop bundle, then
    falls back to the embedded copy. Returns a dict theme -> [keywords]."""
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(here, "themes.json"),                       # repo: themes.json beside the script
        os.path.join(here, "..", "themes.json"),
        os.path.expanduser("~/Desktop/Code with Claude Debriefed/themes.json"),
    ]
    for path in candidates:
        try:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                data.pop("_comment", None)
                if data:
                    return data
        except Exception:
            continue
    return dict(FALLBACK_THEMES)


def theme_for(answer, themes):
    a = (answer or "").lower().strip()
    if not a:
        return "Other"
    for theme in THEME_ORDER:
        if theme == "Other":
            continue
        for kw in themes.get(theme, []):
            if kw in a:
                return theme
    return "Other"


def bucket(answers, themes):
    """Return (ranked list of (theme, count), total, other_words)."""
    counts = Counter()
    other_words = []
    for a in answers:
        t = theme_for(a, themes)
        counts[t] += 1
        if t == "Other":
            other_words.append(a.strip())
    ordered = [(t, counts[t]) for t in THEME_ORDER if counts[t] > 0]
    ordered.sort(key=lambda kv: -kv[1])
    return ordered, len(answers), other_words


# ----------------------------------------------------------------------------
# Data
# ----------------------------------------------------------------------------

def fetch_responses(endpoint, kind="answer", poll_type="poll1"):
    """Return a list of strings (answers or changed values) from the endpoint."""
    import requests
    sep = "&" if "?" in endpoint else "?"
    url = endpoint + sep + "type=" + poll_type
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    data = r.json()
    rows = data.get("responses", [])
    out = []
    for row in rows:
        val = (row.get(kind) or "").strip()
        if val:
            out.append(val)
    return out


# ----------------------------------------------------------------------------
# AI hybrid polish (optional)
# ----------------------------------------------------------------------------

def ai_resort_other(other_words):
    """Ask Claude to map each Other word to the best existing theme.

    Returns a dict {word_lower: theme} for words it could place. On any failure
    (no key, network, parse) returns None so the caller falls back to keyword-only.
    """
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key or not other_words:
        return None
    try:
        import urllib.request

        themes_for_prompt = [t for t in THEME_ORDER if t != "Other"]
        prompt = (
            "You are sorting one-word survey answers into themes.\n"
            "Themes (use these EXACT strings, nothing else): "
            + ", ".join(themes_for_prompt) + ".\n"
            "For each word below, choose the single best-fitting theme. If a word "
            "genuinely fits none, use \"Other\".\n"
            "Return ONLY a JSON object mapping each lowercase word to its theme. "
            "No prose.\n\n"
            "Words: " + json.dumps(sorted(set(w.lower() for w in other_words)))
        )
        body = json.dumps({
            "model": "claude-opus-4-8",
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": prompt}],
        }).encode("utf-8")
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=body,
            headers={
                "x-api-key": key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=40) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        text = "".join(
            b.get("text", "") for b in payload.get("content", []) if b.get("type") == "text"
        ).strip()
        # Strip code fences if present
        if text.startswith("```"):
            text = text.strip("`")
            if text.lower().startswith("json"):
                text = text[4:]
        mapping = json.loads(text)
        valid = set(THEME_ORDER)
        clean = {}
        for w, t in mapping.items():
            if t in valid:
                clean[w.lower()] = t
        return clean or None
    except Exception as e:
        print(f"AI step failed ({e}). Falling back to keyword-only.")
        return None


def ai_prompt_for_manual(other_words):
    themes_for_prompt = [t for t in THEME_ORDER if t != "Other"]
    words = json.dumps(sorted(set(w.lower() for w in other_words)))
    return (
        "Sort these one-word survey answers into themes. Use ONLY these exact "
        "theme strings: " + ", ".join(themes_for_prompt) + ", Other.\n"
        "Return a JSON object mapping each word to its theme.\n\n"
        "Words: " + words
    )


# ----------------------------------------------------------------------------
# Render: themed leaderboard (default)
# ----------------------------------------------------------------------------

def render_leaderboard(ranked, total, out_path, is_sample, ai_used=False):
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)

    f_eyebrow = _load_font(SANS_CANDIDATES, 17)
    f_title   = _load_font(SERIF_CANDIDATES, 40)
    f_total   = _load_font(SERIF_CANDIDATES, 22)
    f_theme   = _load_font(SANS_CANDIDATES, 26)
    f_count   = _load_font(SERIF_CANDIDATES, 26)
    f_foot    = _load_font(SANS_CANDIDATES, 14)

    PAD_X = 84
    top = 52

    eyebrow = "BEFORE WE STARTED, WE ASKED THE ROOM"
    if is_sample:
        eyebrow = "SAMPLE DATA - DESIGN PREVIEW"
    elif ai_used:
        eyebrow = "WHAT THE ROOM SAID  (THEMES, AI-TIDIED)"
    d.text((PAD_X, top), eyebrow, font=f_eyebrow, fill=ACCENT if is_sample else INK_SOFT)

    title = "The most important skill for being good at AI"
    d.text((PAD_X, top + 28), title, font=f_title, fill=INK)

    count_line = f"{total} answers" if total else "No answers yet"
    d.text((PAD_X, top + 84), count_line, font=f_total, fill=INK_MID)

    rule_y = top + 124
    d.line([(PAD_X, rule_y), (W - PAD_X, rule_y)], fill=LINE, width=1)

    if not ranked:
        msg = "Run again once answers come in."
        fw, fh = _text_size(d, msg, f_total)
        d.text(((W - fw) / 2, H / 2 - fh), msg, font=f_total, fill=INK_SOFT)
    else:
        _draw_bars(d, ranked, total, (PAD_X, rule_y + 30, W - PAD_X, H - 70),
                   f_theme, f_count)

    foot_y = H - 44
    d.text((PAD_X, foot_y), "Code with Claude, debriefed", font=f_foot, fill=INK_MID)
    wm = "INSEAD AI Club"
    ww, _ = _text_size(d, wm, f_foot)
    d.text((W - PAD_X - ww, foot_y), wm, font=f_foot, fill=INK)

    img.save(out_path, "PNG")
    return out_path


def _draw_bars(d, ranked, total, box, f_theme, f_count):
    x0, y0, x1, y1 = box
    rows = ranked[:8]
    n = len(rows)
    max_n = rows[0][1]
    bar_w_max = (x1 - x0)

    # Each row = a label/count line on top, then a bar below it, then a gap.
    # Size the parts to the available height so 1-8 rows all fit cleanly.
    label_h = 34          # space the theme label + count occupy
    bar_h = 20            # the bar thickness
    label_to_bar = 8      # gap between label baseline and the bar
    block_h = label_h + label_to_bar + bar_h
    total_h = y1 - y0
    gap = (total_h - block_h * n) / max(1, n)        # even spacing
    gap = max(10, min(40, gap))
    # If even the minimum doesn't fit, compress the block instead.
    if block_h * n + gap * (n - 1) > total_h and n > 0:
        block_h = max(46, int((total_h - gap * (n - 1)) / n))

    yy = y0
    for i, (theme, cnt) in enumerate(rows):
        frac = cnt / max_n if max_n else 0
        bar_w = max(8, int(bar_w_max * frac))
        colour = ACCENT if i == 0 else ACCENT_SOFT
        theme_col = ACCENT if i == 0 else INK

        # label + count on the top line of the block
        d.text((x0, yy), theme, font=f_theme, fill=theme_col)
        pct = round((cnt / total) * 100) if total else 0
        cnt_txt = f"{cnt}   {pct}%"
        cw, _ = _text_size(d, cnt_txt, f_count)
        d.text((x1 - cw, yy + 2), cnt_txt, font=f_count, fill=INK_MID)

        # bar sits BELOW the label, no overlap
        by = yy + label_h + label_to_bar
        d.rounded_rectangle([x0, by, x1, by + bar_h], radius=bar_h // 2, fill=CARD)
        d.rounded_rectangle([x0, by, x0 + bar_w, by + bar_h], radius=bar_h // 2, fill=colour)

        yy += block_h + gap


# ----------------------------------------------------------------------------
# Render: yes/no changed card
# ----------------------------------------------------------------------------

def render_changed(yes, no, out_path, is_sample):
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)

    f_eyebrow = _load_font(SANS_CANDIDATES, 17)
    f_title   = _load_font(SERIF_CANDIDATES, 38)
    f_lab     = _load_font(SANS_CANDIDATES, 24)
    f_big     = _load_font(SERIF_CANDIDATES, 110)
    f_n       = _load_font(SANS_CANDIDATES, 20)
    f_foot    = _load_font(SANS_CANDIDATES, 14)

    PAD_X = 84
    top = 56
    total = yes + no

    eyebrow = "SAMPLE DATA - DESIGN PREVIEW" if is_sample else "AND AT THE END, WE ASKED AGAIN"
    d.text((PAD_X, top), eyebrow, font=f_eyebrow, fill=ACCENT if is_sample else INK_SOFT)

    title = "Has tonight changed your mind?"
    d.text((PAD_X, top + 28), title, font=f_title, fill=INK)

    count_line = f"{total} answers" if total else "No answers yet"
    d.text((PAD_X, top + 80), count_line, font=f_lab, fill=INK_MID)

    yp = round((yes / total) * 100) if total else 0
    np_ = (100 - yp) if total else 0

    # Two cards
    card_y = top + 140
    card_h = 320
    gap = 40
    card_w = (W - 2 * PAD_X - gap) // 2

    # Yes card (filled coral)
    yx = PAD_X
    d.rounded_rectangle([yx, card_y, yx + card_w, card_y + card_h], radius=18, fill=ACCENT)
    d.text((yx + 36, card_y + 30), "Changed my mind", font=f_lab, fill=PAPER)
    d.text((yx + 32, card_y + 90), f"{yp}%", font=f_big, fill=PAPER)
    d.text((yx + 36, card_y + card_h - 56), f"{yes} people", font=f_n, fill=PAPER)

    # No card (card bg)
    nx = PAD_X + card_w + gap
    d.rounded_rectangle([nx, card_y, nx + card_w, card_y + card_h], radius=18,
                        fill=CARD, outline=LINE, width=1)
    d.text((nx + 36, card_y + 30), "Not yet", font=f_lab, fill=INK)
    d.text((nx + 32, card_y + 90), f"{np_}%", font=f_big, fill=INK)
    d.text((nx + 36, card_y + card_h - 56), f"{no} people", font=f_n, fill=INK_MID)

    # Proportional bar under the cards
    bar_y = card_y + card_h + 36
    bar_h = 30
    bar_w_total = W - 2 * PAD_X
    yes_w = int(bar_w_total * (yp / 100)) if total else bar_w_total // 2
    d.rounded_rectangle([PAD_X, bar_y, PAD_X + bar_w_total, bar_y + bar_h],
                        radius=bar_h // 2, fill=NEUTRAL)
    if yes_w > 0:
        d.rounded_rectangle([PAD_X, bar_y, PAD_X + max(bar_h, yes_w), bar_y + bar_h],
                            radius=bar_h // 2, fill=ACCENT)

    foot_y = H - 44
    d.text((PAD_X, foot_y), "Code with Claude, debriefed", font=f_foot, fill=INK_MID)
    wm = "INSEAD AI Club"
    ww, _ = _text_size(d, wm, f_foot)
    d.text((W - PAD_X - ww, foot_y), wm, font=f_foot, fill=INK)

    img.save(out_path, "PNG")
    return out_path


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(
        description="Event 3 poll - render a deck-styled themed leaderboard (or yes/no card) PNG.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument("--endpoint", default=DEFAULT_ENDPOINT,
                    help="Google Apps Script /exec URL that returns responses as JSON.")
    ap.add_argument("--out", default=DEFAULT_OUT, help="Output PNG path.")
    ap.add_argument("--sample", action="store_true",
                    help="Force clearly-labelled sample data (preview the design).")
    ap.add_argument("--ai", action="store_true",
                    help="Hybrid polish: Claude sorts the 'Other' words into themes (needs ANTHROPIC_API_KEY).")
    ap.add_argument("--changed", action="store_true",
                    help="Render the yes/no result card from poll 2 instead of the leaderboard.")
    ap.add_argument("--no-open", action="store_true",
                    help="Do not reveal the PNG in Finder.")
    args = ap.parse_args()

    endpoint_set = (
        args.endpoint
        and "PASTE_APPS_SCRIPT" not in args.endpoint
        and args.endpoint.startswith("http")
    )
    is_sample = args.sample or not endpoint_set

    # ---------------- CHANGED (poll 2) ----------------
    if args.changed:
        values = None
        if not args.sample and endpoint_set:
            try:
                values = fetch_responses(args.endpoint, kind="changed", poll_type="poll2")
                print(f"Fetched {len(values)} poll-2 answers from the endpoint.")
                if not values:
                    print("No poll-2 answers yet - falling back to sample data.")
                    is_sample = True
            except Exception as e:
                print(f"Could not fetch poll 2 ({e}). Falling back to sample data.")
                is_sample = True
        if is_sample or not values:
            values = SAMPLE_CHANGED
            print("Using SAMPLE data for the yes/no card.")
        yes = sum(1 for v in values if v.lower() == "yes")
        no = sum(1 for v in values if v.lower() == "no")
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        out = render_changed(yes, no, args.out, is_sample)
        print(f"Wrote: {out}")
        print(f"Changed my mind: {yes}  /  Not yet: {no}")
        if not args.no_open:
            subprocess.run(["open", "-R", out], check=False)
        return

    # ---------------- LEADERBOARD (poll 1, default) ----------------
    themes = load_themes()
    answers = None
    if not args.sample and endpoint_set:
        try:
            answers = fetch_responses(args.endpoint, kind="answer", poll_type="poll1")
            print(f"Fetched {len(answers)} answers from the endpoint.")
            if not answers:
                print("Endpoint returned no answers yet - falling back to sample data.")
                is_sample = True
        except Exception as e:
            print(f"Could not fetch from endpoint ({e}). Falling back to sample data.")
            is_sample = True

    if is_sample or not answers:
        answers = SAMPLE
        if args.sample:
            print("Using SAMPLE data (--sample).")
        elif not endpoint_set:
            print("No endpoint set - using SAMPLE data so you can see the design.")

    ranked, total, other_words = bucket(answers, themes)
    ai_used = False

    if args.ai and other_words:
        print(f"{len(other_words)} answer(s) fell into 'Other': {sorted(set(w.lower() for w in other_words))}")
        mapping = ai_resort_other(other_words)
        if mapping:
            # Re-bucket: reassign Other words per the AI mapping.
            reassigned = []
            for a in answers:
                if theme_for(a, themes) == "Other":
                    reassigned.append(mapping.get(a.lower().strip(), "Other") or "Other")
                else:
                    reassigned.append(theme_for(a, themes))
            counts = Counter(reassigned)
            ranked = [(t, counts[t]) for t in THEME_ORDER if counts[t] > 0]
            ranked.sort(key=lambda kv: -kv[1])
            total = len(answers)
            ai_used = True
            print("Claude tidied the 'Other' bucket and the leaderboard was re-rendered.")
        else:
            print("\n--- No AI result. Sort these by hand if you like, paste this prompt into Claude: ---")
            print(ai_prompt_for_manual(other_words))
            print("--- end prompt ---\n")

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    out = render_leaderboard(ranked, total, args.out, is_sample, ai_used=ai_used)
    print(f"Wrote: {out}")
    if ranked:
        top = ", ".join(f"{t} ({n})" for t, n in ranked[:5])
        print(f"Top themes: {top}")
        if other_words and not ai_used:
            print(f"Note: {len(other_words)} answer(s) in 'Other' - run with --ai to tidy them.")

    if not args.no_open:
        subprocess.run(["open", "-R", out], check=False)


if __name__ == "__main__":
    main()

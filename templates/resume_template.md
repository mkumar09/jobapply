# Tailoring instructions (for the scheduled routine, run by Claude)

This file documents what the scheduled cloud routine should do for every job whose
`status.json` is `prefilter_passed`. It isn't executable — it's the spec Claude
follows during the routine, since the scoring/tailoring itself is an LLM judgment
call, not deterministic code.

## Steps, per job in data/queue/<slug>/ with status "prefilter_passed"

1. Read `job.json` (title, location, description_text) and `data/resume_profile.yaml`
   (the ground-truth facts about Mahendra's background — never invent experience
   he doesn't have).
2. Location check, before scoring: the job must be India-based or explicitly
   "Remote, India" — never a remote role scoped to another country (e.g. "U.S.
   Remote", "Remote (UK)"). The scraper's location_deny list in config/profile.yaml
   already filters most of these out, but re-check the actual job.json location
   and description_text here as a safety net — job boards sometimes list a vague
   "Remote" with the real country restriction only mentioned in the body text. If
   the role isn't India/Remote-India, set status to `"scored_below_threshold"` with
   a rationale noting the location mismatch, and skip scoring/tailoring entirely.
3. Score the match 0-100 against `config/profile.yaml`'s target roles/skills, and
   write `match.json`:
   ```json
   {"score": 82, "rationale": "Strong Java/Spring/Kafka overlap, AWS matches, title matches Senior Backend Engineer."}
   ```
4. If `score < apply_min_score` (see config/profile.yaml): set `status.json` status
   to `"scored_below_threshold"` and stop — no resume gets tailored for it.
5. If `score >= apply_min_score`, build a tailoring dict (see schema below), call:
   ```python
   from resume.render import render
   import yaml
   from pathlib import Path
   resume_profile = yaml.safe_load(open("data/resume_profile.yaml"))
   render(resume_profile, tailoring, Path("data/queue/<slug>/tailored_resume.docx"))
   ```
   and write a short `cover_note.md` (3-4 sentences, truthful, referencing the
   specific JD) into the same folder.
6. Set `status.json` status to `"ready_to_apply"`.

## Tailoring dict schema (passed to `resume.render.render`)

```python
{
  "summary": "AT MOST 2 sentences, rewritten to foreground the JD's priorities, "
             "using only facts already present in resume_profile.yaml",
  "skills_highlight": ["Kafka", "AWS", "Spring Boot"],   # names to move first within their category
  "experience_order": {
    "Standard Chartered Bank (via Capgemini)": [1, 0, 2, 3]  # bullet indices reordered, most relevant first
  },
  "max_bullets_per_role": 4  # optional, defaults to 4 — lower it if a JD needs a shorter resume
}
```

The summary is hard-capped at 2 sentences by `resume/render.py` itself (anything
longer gets truncated), so keep it to 2 regardless — don't rely on the renderer's
truncation to fix an overlong summary, write it tight to begin with.

The renderer is tuned to keep output to one page (A4, tight margins/spacing, capped
bullets) — this is intentional, don't loosen the formatting or raise the bullet cap
without a reason, since one-page is the target length for this profile.

Rules:
- Never fabricate metrics, tech, or responsibilities not already in `resume_profile.yaml`.
- Reordering and rewording for emphasis is fine; adding new claims is not.
- `experience_order` values must be a permutation of `range(len(bullets))` for that
  company — `resume/render.py` silently falls back to original order if malformed.

## After tailoring runs for all prefiltered jobs

Send a PushNotification summarizing: how many new jobs were found, how many passed
the prefilter, how many scored above `apply_min_score` and are now `ready_to_apply`
(with title/company/score for each), and a reminder to run
`python autofill/playwright_apply.py` locally to process the queue.

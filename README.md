# Job Application Bot

Finds Senior/Mid-Senior engineering roles on company ATS boards (Greenhouse,
Lever, Ashby), scores them against Mahendra's resume, tailors the resume per
JD, and helps fill (not submit) the application.

## How it fits together

- **Discovery + tailoring** runs on a schedule (see "Scheduling" below) and
  needs no browser — it only calls public JSON APIs and lets Claude do the
  scoring/tailoring reasoning.
- **Applying** runs locally, on-demand, because it needs a real visible
  browser and your final review before every submit.

```
config/profile.yaml       target roles/skills/locations + score thresholds
config/companies.yaml     which ATS boards to poll (validate tokens before trusting them)
data/resume_profile.yaml  structured source-of-truth resume (edit this if your resume changes)
data/queue/<slug>/        one folder per discovered job, moves through statuses below
```

Job status lifecycle (`data/queue/<slug>/status.json`):
`pending_review` → `prefilter_passed` / `skipped_prefilter` → `scored_below_threshold` / `ready_to_apply` → `applied` / `reviewed_not_applied`

## One-time setup

```
pip install -r requirements.txt
playwright install chromium
```

Fill in `data/resume_profile.yaml`'s `contact.linkedin` / `contact.github` (left
blank — add your profile URLs).

## Adding companies to poll

Board tokens drift, so nothing in `config/companies.yaml`'s `companies` list is
trusted until it's been checked live:

```
python scripts/add_company.py --check-candidates      # test the starter guesses
python scripts/add_company.py greenhouse razorpay "Razorpay"   # add one you've confirmed
```

Find a company's token by checking its careers page URL — e.g. a Greenhouse
board is usually `job-boards.greenhouse.io/<token>`, a Lever board is
`jobs.lever.co/<token>`, an Ashby board is `jobs.ashbyhq.com/<token>`.

## Running it manually (for testing before scheduling)

```
python scraper/run.py          # fetch + filter + write new jobs to data/queue/
python matching/prefilter.py   # cheap keyword score, drops obvious mismatches
```

The scoring/tailoring step (job.json -> match.json -> tailored_resume.docx) is
an LLM judgment call, not a deterministic script — see `templates/resume_template.md`
for the exact spec Claude follows. Run it by asking Claude Code, in this
project directory, to "process the queue" — or once scheduled, the routine
does this automatically.

## Applying (local, run whenever you want to process the queue)

```
python autofill/playwright_apply.py
```

Opens a real Chromium window per `ready_to_apply` job, fills name/email/phone/
LinkedIn/resume upload, then **pauses** — you check the form, fix anything it
missed (cover letter questions, screening questions, etc.), and submit it
yourself. Answer the terminal prompt afterward so it can update the job's status.

## Scheduling the discovery/tailoring routine

Use Claude Code's `schedule` skill to register a daily cloud routine that runs:
`scraper/run.py` → `matching/prefilter.py` → the tailoring step described in
`templates/resume_template.md` → a PushNotification summary. This hasn't been
set up yet — ask Claude to "schedule the job bot to run daily" once you're
happy with the manual runs above.

## Known limitations

- Only Greenhouse/Lever/Ashby boards are covered (not LinkedIn/Indeed/Naukri) —
  those actively prohibit scraping/automation in their ToS.
- Ashby forms are a React app with less predictable field names; autofill
  there is best-effort and may need manual completion more often than
  Greenhouse/Lever.
- Application submission is never automated — you always click submit.

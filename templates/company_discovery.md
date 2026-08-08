# Company discovery instructions (for the weekly routine, run by Claude)

This documents what the weekly discovery routine should do. Like resume
tailoring, this is judgment-driven (web search + evaluation), not deterministic
code — the routine follows this spec directly using its own tools.

## Goal

Find more companies that (a) hire Senior/Mid-Senior engineers in India for
Java/Spring Boot/C#/.NET-style backend roles, and (b) run their hiring on
Greenhouse, Lever, or Ashby (the only ATS platforms this bot is allowed to
scrape/automate against — never LinkedIn/Indeed/Naukri, see README).

## Steps

1. Read `config/companies.yaml` to see which companies/tokens are already
   known (both `companies` and `candidates`), so you don't waste searches
   re-finding the same ones.
2. Run several targeted web searches, varying terms across runs so coverage
   grows over time rather than repeating the same query, e.g.:
   - `"job-boards.greenhouse.io" India "Senior" Java Spring Boot`
   - `"jobs.lever.co" India "Senior" ".NET" OR "C#"`
   - `"jobs.ashbyhq.com" India backend engineer Java`
   - Vary seniority words (Senior/Staff/Lead/Principal) and stack words
     (Java, Spring Boot, C#, .NET, Kafka, microservices) across searches.
   - Skip results that are recruiting agencies/aggregators rather than the
     hiring company itself (e.g. "Jobgether", "Weekday", themuse.com listings)
     — extract the actual employer's own board token, not a middleman's.
3. From result URLs, extract candidate `{provider, token}` pairs:
   - Greenhouse: `job-boards.greenhouse.io/<token>/jobs/...` or `boards.greenhouse.io/<token>`
   - Lever: `jobs.lever.co/<token>/...`
   - Ashby: `jobs.ashbyhq.com/<token>/...`
4. Add genuinely new candidates (skip ones already in `companies` or
   `candidates`) to `config/companies.yaml`'s `candidates` list with a
   reasonable `name`.
5. Validate every candidate live: `python scripts/add_company.py --check-candidates`.
   This hits the real API for each one — never trust a token just because it
   appeared in a search result.
6. For every candidate that came back `[OK]` with a nonzero job count, promote
   it: `python scripts/add_company.py <provider> <token> "<Name>"`. This is
   what actually moves it into the trusted `companies` list the scraper polls.
7. Commit and push: `git add -A && git commit -m "Weekly company discovery: <N> new companies added" && git push`.
   If nothing new was found/validated, skip the commit (don't fail the run).
8. Send exactly one PushNotification: how many candidates were tried, how many
   validated successfully and were added (with name + job count each), and how
   many failed validation (just a count, not each failure).

## Rules

- Never add a company to the trusted `companies` list without it passing the
  live validation in step 5-6 first.
- Don't re-add companies already present in `companies` or `candidates`.
- Keep searches focused on this profile's actual stack (Java/Spring Boot,
  C#/.NET, Kafka, AWS, SQL) and India-relevant seniority — don't broaden into
  unrelated tech stacks just to find more results.
- This routine only ever touches `config/companies.yaml` — it doesn't scrape
  jobs, score matches, or touch the queue. That's the daily routine's job.

"""Orchestrates the scrape step:

  1. Load config/companies.yaml (which boards to poll) and config/profile.yaml (filters).
  2. Fetch jobs from each configured Greenhouse/Lever/Ashby board.
  3. Filter by title (target/exclude lists) and location.
  4. Drop anything already seen (data/seen_jobs.json).
  5. Write a job.json + status.json (pending_review) into data/queue/<slug>/ for each new match.
  6. Write data/new_jobs.json listing just the job_ids discovered in this run, for the
     matching/tailoring step to pick up.

Run: python scraper/run.py
"""
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scraper import greenhouse, lever, ashby  # noqa: E402

PROVIDERS = {
    "greenhouse": greenhouse.fetch_jobs,
    "lever": lever.fetch_jobs,
    "ashby": ashby.fetch_jobs,
}

CONFIG_DIR = ROOT / "config"
DATA_DIR = ROOT / "data"
QUEUE_DIR = DATA_DIR / "queue"
SEEN_JOBS_FILE = DATA_DIR / "seen_jobs.json"
NEW_JOBS_FILE = DATA_DIR / "new_jobs.json"


def load_yaml(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_seen_jobs() -> dict:
    if SEEN_JOBS_FILE.exists():
        with open(SEEN_JOBS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_seen_jobs(seen: dict) -> None:
    SEEN_JOBS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SEEN_JOBS_FILE, "w", encoding="utf-8") as f:
        json.dump(seen, f, indent=2, sort_keys=True)


def html_to_text(html: str) -> str:
    if not html:
        return ""
    return BeautifulSoup(html, "html.parser").get_text(separator=" ", strip=True)


def title_passes(title: str, seniority_keywords: list[str], role_keywords: list[str], exclude_titles: list[str]) -> bool:
    t = title.lower()
    if any(bad in t for bad in exclude_titles):
        return False
    has_seniority = any(kw in t for kw in seniority_keywords)
    has_role = any(kw in t for kw in role_keywords)
    return has_seniority and has_role


def location_passes(location: str, allowed_locations: list[str]) -> bool:
    if not location.strip():
        # Unspecified location: keep for manual review rather than silently dropping.
        return True
    loc = location.lower()
    return any(allowed in loc for allowed in allowed_locations)


def slugify(text: str, max_len: int = 60) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:max_len]


def main() -> None:
    profile = load_yaml(CONFIG_DIR / "profile.yaml")
    companies = load_yaml(CONFIG_DIR / "companies.yaml").get("companies", [])

    seniority_keywords = [t.lower() for t in profile.get("seniority_keywords", [])]
    role_keywords = [t.lower() for t in profile.get("role_keywords", [])]
    exclude_titles = [t.lower() for t in profile.get("exclude_titles", [])]
    allowed_locations = [l.lower() for l in profile.get("locations", [])]

    seen = load_seen_jobs()
    new_job_ids = []

    for company in companies:
        provider = company["provider"]
        token = company["token"]
        fetch = PROVIDERS.get(provider)
        if fetch is None:
            print(f"[skip] unknown provider '{provider}' for token '{token}'")
            continue

        try:
            jobs = fetch(token)
        except Exception as exc:
            print(f"[error] {provider}:{token} -> {exc}")
            continue

        for job in jobs:
            if job["job_id"] in seen:
                continue
            if not title_passes(job["title"], seniority_keywords, role_keywords, exclude_titles):
                continue
            if not location_passes(job["location"], allowed_locations):
                continue

            job["description_text"] = html_to_text(job.get("description_html", ""))
            job["discovered_at"] = datetime.now(timezone.utc).isoformat()

            slug = slugify(f"{company.get('name', token)}-{job['title']}-{job['job_id'][-8:]}")
            job_dir = QUEUE_DIR / slug
            job_dir.mkdir(parents=True, exist_ok=True)
            with open(job_dir / "job.json", "w", encoding="utf-8") as f:
                json.dump(job, f, indent=2)
            with open(job_dir / "status.json", "w", encoding="utf-8") as f:
                json.dump({"status": "pending_review", "updated_at": job["discovered_at"]}, f, indent=2)

            seen[job["job_id"]] = job["discovered_at"]
            new_job_ids.append({"job_id": job["job_id"], "queue_dir": str(job_dir.relative_to(ROOT))})
            print(f"[new] {job['title']} @ {company.get('name', token)} -> {job_dir}")

    save_seen_jobs(seen)
    with open(NEW_JOBS_FILE, "w", encoding="utf-8") as f:
        json.dump(new_job_ids, f, indent=2)

    print(f"\nDone. {len(new_job_ids)} new job(s) written to {QUEUE_DIR}")


if __name__ == "__main__":
    main()

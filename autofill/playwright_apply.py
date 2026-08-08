"""LOCAL-ONLY script: opens a real, visible browser and auto-fills common
application fields for each job in the queue with status "ready_to_apply".
It NEVER clicks submit — you review the filled form and submit it yourself.

This is meant to run on your own machine (not in the cloud routine), since it
needs an interactive browser window and your final sign-off per application.

Setup (one-time):
    pip install -r requirements.txt
    playwright install chromium

Run:
    python autofill/playwright_apply.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from autofill.selectors import FILLERS  # noqa: E402

QUEUE_DIR = ROOT / "data" / "queue"
RESUME_PROFILE_FILE = ROOT / "data" / "resume_profile.yaml"

APPLY_BUTTON_TEXTS = ["Apply for this Job", "Apply for this job", "Apply Now", "Apply for this position", "Apply"]


def _reveal_application_form(page) -> None:
    """Some postings (seen on Ashby) show a job-description page first, with
    the actual form only appearing after clicking an Apply button/link. If the
    page looks like it has no real form yet, try clicking one."""
    if page.locator("input, textarea").count() >= 3:
        return  # form already present
    for text in APPLY_BUTTON_TEXTS:
        try:
            btn = page.get_by_text(text, exact=False).first
            if btn.count() > 0:
                btn.click()
                page.wait_for_load_state("domcontentloaded", timeout=8000)
                try:
                    page.wait_for_load_state("networkidle", timeout=8000)
                except Exception:
                    pass
                if page.locator("input, textarea").count() >= 3:
                    return
        except Exception:
            continue


def load_contact() -> dict:
    with open(RESUME_PROFILE_FILE, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)["contact"]


def ready_jobs():
    if not QUEUE_DIR.exists():
        return
    for job_dir in sorted(QUEUE_DIR.iterdir()):
        status_path = job_dir / "status.json"
        job_path = job_dir / "job.json"
        if not status_path.exists() or not job_path.exists():
            continue
        with open(status_path, "r", encoding="utf-8") as f:
            status = json.load(f)
        if status.get("status") != "ready_to_apply":
            continue
        with open(job_path, "r", encoding="utf-8") as f:
            job = json.load(f)
        yield job_dir, job, status


def mark_status(job_dir: Path, status: dict, new_status: str) -> None:
    status["status"] = new_status
    with open(job_dir / "status.json", "w", encoding="utf-8") as f:
        json.dump(status, f, indent=2)


def main() -> None:
    contact = load_contact()
    jobs = list(ready_jobs())

    if not jobs:
        print("No jobs with status 'ready_to_apply' found in the queue.")
        return

    print(f"Found {len(jobs)} job(s) ready to apply. Opening browser...\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)

        for job_dir, job, status in jobs:
            resume_path = job_dir / "tailored_resume.docx"
            if not resume_path.exists():
                print(f"[skip] {job_dir.name}: no tailored_resume.docx found, run tailoring first.")
                continue

            filler = FILLERS.get(job["source"])
            if filler is None:
                print(f"[skip] {job_dir.name}: no autofill support for source '{job['source']}'.")
                continue

            print(f"\n=== {job['title']} @ {job.get('company_token')} ===")
            print(f"URL: {job['url']}")

            page = browser.new_page()
            page.goto(job["url"], wait_until="domcontentloaded")
            try:
                page.wait_for_load_state("networkidle", timeout=8000)
            except Exception:
                pass  # some forms poll/long-connect and never go fully idle; proceed anyway

            _reveal_application_form(page)

            try:
                results = filler(page, contact, resume_path)
            except Exception as exc:
                print(f"[warn] autofill raised an error, form may need manual entry: {exc}")
                results = {}

            for field, ok in results.items():
                print(f"  {'OK ' if ok else 'MISS'} {field}")
            if not results.get("resume"):
                print(f"  -> Attach the resume manually: {resume_path}")

            answer = input(
                "\nReview the form in the browser window. Fill anything missed, then submit it yourself.\n"
                "Type 'applied' once submitted, 'skip' to leave for later, or anything else to just move on: "
            ).strip().lower()

            if answer == "applied":
                mark_status(job_dir, status, "applied")
            elif answer == "skip":
                pass  # leave status as ready_to_apply for next run
            else:
                mark_status(job_dir, status, "reviewed_not_applied")

            page.close()

        browser.close()

    print("\nDone.")


if __name__ == "__main__":
    main()

"""Fetch + normalize job postings from an Ashby job board.

Public endpoint, no auth required:
    https://api.ashbyhq.com/posting-api/job-board/{token}
"""
import requests

API_URL = "https://api.ashbyhq.com/posting-api/job-board/{token}"


def fetch_jobs(token: str, timeout: int = 15) -> list[dict]:
    resp = requests.get(API_URL.format(token=token), timeout=timeout)
    resp.raise_for_status()
    resp.encoding = "utf-8"
    payload = resp.json()
    return [_normalize(token, job) for job in payload.get("jobs", [])]


def _normalize(token: str, job: dict) -> dict:
    return {
        "source": "ashby",
        "company_token": token,
        "job_id": f"ashby:{token}:{job['id']}",
        "title": job.get("title", ""),
        "location": job.get("location", ""),
        "url": job.get("jobUrl", ""),
        "updated_at": job.get("publishedAt", ""),
        "description_html": job.get("descriptionHtml", ""),
    }

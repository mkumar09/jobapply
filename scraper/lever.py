"""Fetch + normalize job postings from a Lever job board.

Public endpoint, no auth required:
    https://api.lever.co/v0/postings/{token}?mode=json
"""
import requests

API_URL = "https://api.lever.co/v0/postings/{token}?mode=json"


def fetch_jobs(token: str, timeout: int = 15) -> list[dict]:
    resp = requests.get(API_URL.format(token=token), timeout=timeout)
    resp.raise_for_status()
    resp.encoding = "utf-8"
    postings = resp.json()
    return [_normalize(token, job) for job in postings]


def _normalize(token: str, job: dict) -> dict:
    categories = job.get("categories", {}) or {}
    return {
        "source": "lever",
        "company_token": token,
        "job_id": f"lever:{token}:{job['id']}",
        "title": job.get("text", ""),
        "location": categories.get("location", ""),
        "url": job.get("hostedUrl", ""),
        "updated_at": str(job.get("createdAt", "")),
        "description_html": job.get("descriptionPlain", "") or job.get("description", ""),
    }

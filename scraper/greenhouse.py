"""Fetch + normalize job postings from a Greenhouse job board.

Public endpoint, no auth required:
    https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true
"""
import requests

API_URL = "https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true"


def fetch_jobs(token: str, timeout: int = 15) -> list[dict]:
    resp = requests.get(API_URL.format(token=token), timeout=timeout)
    resp.raise_for_status()
    resp.encoding = "utf-8"
    payload = resp.json()
    return [_normalize(token, job) for job in payload.get("jobs", [])]


def _normalize(token: str, job: dict) -> dict:
    return {
        "source": "greenhouse",
        "company_token": token,
        "job_id": f"greenhouse:{token}:{job['id']}",
        "title": job.get("title", ""),
        "location": (job.get("location") or {}).get("name", ""),
        "url": job.get("absolute_url", ""),
        "updated_at": job.get("updated_at", ""),
        "description_html": job.get("content", ""),
    }

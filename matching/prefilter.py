"""Cheap keyword-overlap scoring used to cut obvious mismatches before spending
an LLM call on a job during the scheduled routine.

Run standalone to sweep the queue:
    python matching/prefilter.py

For each data/queue/<slug>/ with status "pending_review":
  - scores job.json's title+description against config/profile.yaml skills
  - writes prefilter_score.json {score, matched}
  - if score < profile.prefilter_min_score -> status becomes "skipped_prefilter"
    else -> status becomes "prefilter_passed" (ready for Claude scoring/tailoring)
"""
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT / "config"
QUEUE_DIR = ROOT / "data" / "queue"


def load_yaml(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def score_text(text: str, skills_cfg: dict) -> tuple[int, list[str]]:
    """Returns (0-100 score, list of matched skill names)."""
    text_lower = text.lower()
    all_skills = skills_cfg.get("core", []) + skills_cfg.get("secondary", [])
    total_weight = sum(s["weight"] for s in all_skills) or 1
    matched_weight = 0
    matched = []
    for skill in all_skills:
        if skill["name"].lower() in text_lower:
            matched_weight += skill["weight"]
            matched.append(skill["name"])
    score = round(100 * matched_weight / total_weight)
    return score, matched


def score_job(job: dict, profile: dict) -> tuple[int, list[str]]:
    text = f"{job.get('title', '')} {job.get('description_text', '')}"
    return score_text(text, profile.get("skills", {}))


def main() -> None:
    profile = load_yaml(CONFIG_DIR / "profile.yaml")
    threshold = profile.get("prefilter_min_score", 25)

    if not QUEUE_DIR.exists():
        print("No queue directory found, nothing to score.")
        return

    for job_dir in sorted(QUEUE_DIR.iterdir()):
        status_path = job_dir / "status.json"
        job_path = job_dir / "job.json"
        if not status_path.exists() or not job_path.exists():
            continue

        with open(status_path, "r", encoding="utf-8") as f:
            status = json.load(f)
        if status.get("status") != "pending_review":
            continue

        with open(job_path, "r", encoding="utf-8") as f:
            job = json.load(f)

        score, matched = score_job(job, profile)
        with open(job_dir / "prefilter_score.json", "w", encoding="utf-8") as f:
            json.dump({"score": score, "matched_skills": matched}, f, indent=2)

        status["status"] = "prefilter_passed" if score >= threshold else "skipped_prefilter"
        with open(status_path, "w", encoding="utf-8") as f:
            json.dump(status, f, indent=2)

        print(f"[{status['status']}] score={score} matched={matched} -> {job_dir.name}")


if __name__ == "__main__":
    main()

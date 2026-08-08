"""Best-effort field heuristics for auto-filling common application fields on
Greenhouse, Lever, and Ashby forms. These are the 3 most common candidate
fields across all providers: name, email, phone, LinkedIn URL, resume upload.

Everything here is best-effort: ATS forms change and vary per posting
(especially Ashby, which is a React app with less predictable DOM structure).
Fields that fail to fill are reported, not silently ignored — the caller
always leaves the browser open for the human to check/fix/finish before
submitting.
"""
from __future__ import annotations

from pathlib import Path


def _try_fill(page, selectors: list[str], value: str) -> bool:
    if not value:
        return False
    for sel in selectors:
        try:
            locator = page.locator(sel).first
            if locator.count() > 0:
                locator.fill(value)
                return True
        except Exception:
            continue
    return False


def _try_upload(page, selectors: list[str], file_path: Path) -> bool:
    for sel in selectors:
        try:
            locator = page.locator(sel).first
            if locator.count() > 0:
                locator.set_input_files(str(file_path))
                return True
        except Exception:
            continue
    return False


def fill_greenhouse(page, contact: dict, resume_path: Path) -> dict:
    results = {}
    results["first_name"] = _try_fill(page, ["#first_name", "input[name='first_name']"], contact["name"].split(" ")[0])
    results["last_name"] = _try_fill(
        page, ["#last_name", "input[name='last_name']"], " ".join(contact["name"].split(" ")[1:])
    )
    results["email"] = _try_fill(page, ["#email", "input[name='email']"], contact["email"])
    results["phone"] = _try_fill(page, ["#phone", "input[name='phone']"], contact["phone"])
    if contact.get("linkedin"):
        results["linkedin"] = _try_fill(
            page, ["input[name*='linkedin' i]", "input[aria-label*='LinkedIn' i]"], contact["linkedin"]
        )
    results["resume"] = _try_upload(page, ["#resume", "input[name='resume']", "input[type='file']"], resume_path)
    return results


def fill_lever(page, contact: dict, resume_path: Path) -> dict:
    results = {}
    results["name"] = _try_fill(page, ["input[name='name']"], contact["name"])
    results["email"] = _try_fill(page, ["input[name='email']"], contact["email"])
    results["phone"] = _try_fill(page, ["input[name='phone']"], contact["phone"])
    if contact.get("linkedin"):
        results["linkedin"] = _try_fill(
            page, ["input[name='urls[LinkedIn]']", "input[name*='linkedin' i]"], contact["linkedin"]
        )
    results["resume"] = _try_upload(page, ["input[name='resume']", "input[type='file']"], resume_path)
    return results


def fill_ashby(page, contact: dict, resume_path: Path) -> dict:
    """Ashby forms are React-driven with less predictable `name` attributes,
    so we fall back to matching on nearby label text. Expect this to need
    iteration once tested against real postings."""
    results = {}

    def fill_by_label(label_substr: str, value: str) -> bool:
        if not value:
            return False
        try:
            field = page.get_by_label(label_substr, exact=False).first
            if field.count() > 0:
                field.fill(value)
                return True
        except Exception:
            pass
        return False

    results["name"] = fill_by_label("Name", contact["name"])
    results["email"] = fill_by_label("Email", contact["email"])
    results["phone"] = fill_by_label("Phone", contact["phone"])
    if contact.get("linkedin"):
        results["linkedin"] = fill_by_label("LinkedIn", contact["linkedin"])
    results["resume"] = _try_upload(page, ["input[type='file']"], resume_path)
    return results


FILLERS = {
    "greenhouse": fill_greenhouse,
    "lever": fill_lever,
    "ashby": fill_ashby,
}

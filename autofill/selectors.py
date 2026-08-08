"""Best-effort field heuristics for auto-filling common application fields on
Greenhouse, Lever, and Ashby forms. These are the 3 most common candidate
fields across all providers: name, email, phone, LinkedIn URL, resume upload.

Everything here is best-effort: ATS forms change and vary per posting.
Greenhouse in particular has both a "classic" embed (stable #first_name-style
ids) and a newer job-boards.greenhouse.io UI that doesn't use those ids at
all — so every text field tries CSS selectors first, then falls back to
matching on the field's visible label text, which tends to survive UI
redesigns better than ids/names do.

Resume upload is the riskiest part: some ATS upload widgets wrap the native
<input type="file"> with their own JS state, and forcing a value into the
wrong file input (or one that widget doesn't expect to be set programmatically)
can throw a JS error in the page. So resume upload only ever targets specific,
purpose-built selectors — never a blind generic `input[type='file']` grab —
and any failure is reported so the human can drag the file in manually instead.
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


def _try_fill_by_label(page, label_substrings: list[str], value: str) -> bool:
    if not value:
        return False
    for label in label_substrings:
        try:
            field = page.get_by_label(label, exact=False).first
            if field.count() > 0:
                field.fill(value)
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


def _try_upload_by_label(page, label_substrings: list[str], file_path: Path) -> bool:
    for label in label_substrings:
        try:
            field = page.get_by_label(label, exact=False).first
            if field.count() > 0:
                field.set_input_files(str(file_path))
                return True
        except Exception:
            continue
    return False


def fill_greenhouse(page, contact: dict, resume_path: Path) -> dict:
    results = {}
    first_name = contact["name"].split(" ")[0]
    last_name = " ".join(contact["name"].split(" ")[1:])

    results["first_name"] = _try_fill(
        page, ["#first_name", "input[name='first_name']"], first_name
    ) or _try_fill_by_label(page, ["First Name"], first_name)
    results["last_name"] = _try_fill(
        page, ["#last_name", "input[name='last_name']"], last_name
    ) or _try_fill_by_label(page, ["Last Name"], last_name)
    results["email"] = _try_fill(page, ["#email", "input[name='email']"], contact["email"]) or _try_fill_by_label(
        page, ["Email"], contact["email"]
    )
    results["phone"] = _try_fill(page, ["#phone", "input[name='phone']"], contact["phone"]) or _try_fill_by_label(
        page, ["Phone"], contact["phone"]
    )
    if contact.get("linkedin"):
        results["linkedin"] = _try_fill(
            page, ["input[name*='linkedin' i]", "input[aria-label*='LinkedIn' i]"], contact["linkedin"]
        ) or _try_fill_by_label(page, ["LinkedIn"], contact["linkedin"])

    results["resume"] = _try_upload(
        page, ["#resume", "input[name='resume']"], resume_path
    ) or _try_upload_by_label(page, ["Resume", "Resume/CV", "Resume or CV", "Attach Resume/CV"], resume_path)
    return results


def fill_lever(page, contact: dict, resume_path: Path) -> dict:
    results = {}
    results["name"] = _try_fill(page, ["input[name='name']"], contact["name"]) or _try_fill_by_label(
        page, ["Full name", "Name"], contact["name"]
    )
    results["email"] = _try_fill(page, ["input[name='email']"], contact["email"]) or _try_fill_by_label(
        page, ["Email"], contact["email"]
    )
    results["phone"] = _try_fill(page, ["input[name='phone']"], contact["phone"]) or _try_fill_by_label(
        page, ["Phone"], contact["phone"]
    )
    if contact.get("linkedin"):
        results["linkedin"] = _try_fill(
            page, ["input[name='urls[LinkedIn]']", "input[name*='linkedin' i]"], contact["linkedin"]
        ) or _try_fill_by_label(page, ["LinkedIn"], contact["linkedin"])

    results["resume"] = _try_upload(page, ["input[name='resume']"], resume_path) or _try_upload_by_label(
        page, ["Resume", "Resume/CV"], resume_path
    )
    return results


def fill_ashby(page, contact: dict, resume_path: Path) -> dict:
    """Ashby forms are React-driven with less predictable `name` attributes,
    so this relies entirely on matching visible label text."""
    results = {}
    results["name"] = _try_fill_by_label(page, ["Name"], contact["name"])
    results["email"] = _try_fill_by_label(page, ["Email"], contact["email"])
    results["phone"] = _try_fill_by_label(page, ["Phone"], contact["phone"])
    if contact.get("linkedin"):
        results["linkedin"] = _try_fill_by_label(page, ["LinkedIn"], contact["linkedin"])
    results["resume"] = _try_upload_by_label(page, ["Resume", "Resume/CV"], resume_path)
    return results


FILLERS = {
    "greenhouse": fill_greenhouse,
    "lever": fill_lever,
    "ashby": fill_ashby,
}

"""Renders data/resume_profile.yaml (+ optional per-job tailoring) into a DOCX resume.

Tailoring never invents facts — it only:
  - swaps in a JD-tailored summary paragraph (still truthful, written from resume_profile facts)
  - reorders bullets within a role so the most relevant ones lead
  - reorders skill names within a category so JD-relevant ones lead

Usage as a library:
    from resume.render import render
    render(resume_profile_dict, tailoring_dict, Path("out.docx"))

Usage standalone (renders the untailored base resume, useful for testing):
    python resume/render.py data/resume_profile.yaml out.docx
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml
from docx import Document
from docx.shared import Pt

ROOT = Path(__file__).resolve().parent.parent


def _reorder(items: list, order: list[int] | None) -> list:
    if not order:
        return items
    if sorted(order) != list(range(len(items))):
        return items  # malformed order, fall back to original rather than dropping content
    return [items[i] for i in order]


def _reorder_by_name(names: list[str], highlight: list[str] | None) -> list[str]:
    if not highlight:
        return names
    highlight_lower = {h.lower() for h in highlight}
    front = [n for n in names if n.lower() in highlight_lower]
    back = [n for n in names if n.lower() not in highlight_lower]
    return front + back


def render(resume_profile: dict, tailoring: dict, output_path: Path) -> None:
    tailoring = tailoring or {}
    doc = Document()

    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(10.5)

    contact = resume_profile["contact"]
    title = doc.add_heading(contact["name"], level=0)
    title.alignment = 1

    contact_line = " | ".join(
        v for v in [contact.get("phone"), contact.get("email"), contact.get("linkedin"), contact.get("github")] if v
    )
    p = doc.add_paragraph(contact_line)
    p.alignment = 1

    doc.add_heading("Professional Summary", level=1)
    doc.add_paragraph(tailoring.get("summary") or resume_profile["summary_base"].strip())

    doc.add_heading("Technical Skills", level=1)
    skills = resume_profile["skills"]
    highlight = tailoring.get("skills_highlight", [])
    labels = {
        "languages": "Languages",
        "frameworks": "Frameworks",
        "distributed_systems": "Distributed Systems",
        "cloud_infra": "Cloud & Infrastructure",
        "databases": "Databases",
        "tooling": "Tooling & Practices",
        "ai": "AI",
    }
    for key, label in labels.items():
        values = skills.get(key, [])
        if not values:
            continue
        ordered = _reorder_by_name(values, highlight)
        doc.add_paragraph(f"{label}: {', '.join(ordered)}")

    doc.add_heading("Experience", level=1)
    experience_order = tailoring.get("experience_order", {})
    for role in resume_profile["experience"]:
        heading = doc.add_paragraph()
        run = heading.add_run(f"{role['title']} — {role['company']}")
        run.bold = True
        doc.add_paragraph(f"{role['start']} to {role['end']}").italic = True

        bullets = [b["text"] for b in role["bullets"]]
        bullets = _reorder(bullets, experience_order.get(role["company"]))
        for bullet_text in bullets:
            doc.add_paragraph(bullet_text, style="List Bullet")

    if resume_profile.get("open_source"):
        doc.add_heading("Open Source Contributions", level=1)
        for proj in resume_profile["open_source"]:
            p = doc.add_paragraph()
            run = p.add_run(f"{proj['project']} — {proj['role']}")
            run.bold = True
            for bullet_text in proj["bullets"]:
                doc.add_paragraph(bullet_text, style="List Bullet")

    if resume_profile.get("achievements"):
        doc.add_heading("Achievements & Awards", level=1)
        for ach in resume_profile["achievements"]:
            p = doc.add_paragraph()
            run = p.add_run(f"{ach['title']}: ")
            run.bold = True
            p.add_run(ach["text"])

    doc.add_heading("Education", level=1)
    for edu in resume_profile["education"]:
        doc.add_paragraph(f"{edu['school']} — {edu['degree']} ({edu['start']}-{edu['end']})")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output_path))


def main() -> None:
    if len(sys.argv) != 3:
        print("Usage: python resume/render.py <resume_profile.yaml> <output.docx>")
        sys.exit(1)

    with open(sys.argv[1], "r", encoding="utf-8") as f:
        resume_profile = yaml.safe_load(f)

    render(resume_profile, {}, Path(sys.argv[2]))
    print(f"Wrote {sys.argv[2]}")


if __name__ == "__main__":
    main()

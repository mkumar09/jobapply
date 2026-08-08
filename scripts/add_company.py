"""Validate a candidate ATS board token against the live API before trusting it,
then append it to config/companies.yaml's `companies` list.

Usage:
    python scripts/add_company.py greenhouse razorpay "Razorpay"
    python scripts/add_company.py --check-candidates   # test every entry under `candidates`
"""
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scraper import greenhouse, lever, ashby  # noqa: E402

PROVIDERS = {
    "greenhouse": greenhouse.fetch_jobs,
    "lever": lever.fetch_jobs,
    "ashby": ashby.fetch_jobs,
}

COMPANIES_FILE = ROOT / "config" / "companies.yaml"


def load_config() -> dict:
    with open(COMPANIES_FILE, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def save_config(cfg: dict) -> None:
    with open(COMPANIES_FILE, "w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f, sort_keys=False, allow_unicode=True)


def validate(provider: str, token: str) -> int:
    """Returns the number of jobs found, or raises on failure."""
    fetch = PROVIDERS[provider]
    jobs = fetch(token)
    return len(jobs)


def add_company(provider: str, token: str, name: str) -> None:
    cfg = load_config()
    companies = cfg.setdefault("companies", [])
    if any(c["provider"] == provider and c["token"] == token for c in companies):
        print(f"[skip] {provider}:{token} already in companies list")
        return

    try:
        count = validate(provider, token)
    except Exception as exc:
        print(f"[FAIL] {provider}:{token} -> {exc}")
        return

    companies.append({"provider": provider, "token": token, "name": name})
    save_config(cfg)
    print(f"[OK] {provider}:{token} ({name}) -> {count} jobs found, added to companies.yaml")


def check_candidates() -> None:
    cfg = load_config()
    for candidate in cfg.get("candidates", []):
        provider, token = candidate["provider"], candidate["token"]
        name = candidate.get("name", token)
        try:
            count = validate(provider, token)
            print(f"[OK]   {provider}:{token} ({name}) -> {count} jobs")
        except Exception as exc:
            print(f"[FAIL] {provider}:{token} ({name}) -> {exc}")


def main() -> None:
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(1)

    if args[0] == "--check-candidates":
        check_candidates()
        return

    if len(args) < 3:
        print("Usage: python scripts/add_company.py <provider> <token> \"<Display Name>\"")
        sys.exit(1)

    provider, token, name = args[0], args[1], args[2]
    if provider not in PROVIDERS:
        print(f"Unknown provider '{provider}'. Choose from: {', '.join(PROVIDERS)}")
        sys.exit(1)

    add_company(provider, token, name)


if __name__ == "__main__":
    main()

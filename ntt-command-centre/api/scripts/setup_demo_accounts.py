"""Run python -m api.scripts.setup_demo_accounts to create walkthrough accounts.

Passwords go only to the ignored local credentials sheet, never stdout.
Existing accounts and passwords are preserved on rerun.
"""
from __future__ import annotations
import csv
import json
import secrets
import unicodedata
from pathlib import Path
from ..config import OPPORTUNITIES_CSV, ROOT
from ..demo_accounts import hash_password, registry_path

MANAGERS = ("Dana Whitfield", "Marcus Lindqvist", "Priya Raghavan", "Tomás Oliveira", "Hannah Brecht", "Kenji Nakamura")

def slug(name: str) -> str:
    return unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower().replace(" ", ".")

def setup(path: Path | None = None, sheet: Path | None = None) -> tuple[int, Path]:
    path = path or registry_path()
    sheet = sheet or ROOT.parent / "Context" / "Plans" / "DEMO_CREDENTIALS.local.md"
    registry = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {
        "version": 1, "signingSecret": secrets.token_urlsafe(48), "accounts": [],
    }
    with OPPORTUNITIES_CSV.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    definitions = []
    owner_emails: dict[str, set[str]] = {}
    for row in rows:
        name = row["OpportunityOwnerFullName"].strip()
        email = row["OpportunityOwnerEmailAdress"].strip().lower()
        if name and email:
            owner_emails.setdefault(name, set()).add(email)
    for name in sorted(owner_emails):
        emails = owner_emails[name]
        canonical = f"{slug(name)}@global.ntt"
        email = canonical if canonical in emails else sorted(emails)[0]
        definitions.append(dict(id=f"sales-{slug(name)}", name=name, email=email,
                                aliases=sorted(emails - {email}), role="ae", identity=name))
    for i, name in enumerate(MANAGERS):
        definitions.append(dict(id=f"manager-{chr(65+i)}", name=name,
                                email=f"{slug(name)}@demo.ntt.example", aliases=[],
                                role="manager", identity=f"pod-{chr(65+i)}"))
    definitions.append(dict(id="executive-na", name="Vikesh",
                            email="executive.na@demo.ntt.example", aliases=[],
                            role="executive", identity="north-america"))
    existing = {a["id"] for a in registry["accounts"]}
    additions = []
    for definition in definitions:
        if definition["id"] in existing:
            continue
        password = secrets.token_urlsafe(18)
        registry["accounts"].append({**definition, "enabled": True, "passwordHash": hash_password(password)})
        additions.append(f"| {definition['name']} | `{definition['email']}` | `{password}` | {definition['role']} | {definition['identity']} |")
    if additions:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(registry, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        sheet.parent.mkdir(parents=True, exist_ok=True)
        previous = sheet.read_text(encoding="utf-8") if sheet.exists() else (
            "# Local demo credentials\n\nGenerated for this installation only. Do not commit or share publicly.\n"
            "Emails at demo.ntt.example are demo identifiers, not mailboxes.\n\n"
            "| User | Email | Password | Role | Scope |\n|---|---|---|---|---|\n")
        sheet.write_text(previous.rstrip() + "\n" + "\n".join(additions) + "\n", encoding="utf-8")
    return len(additions), sheet

if __name__ == "__main__":
    count, sheet = setup()
    print(f"Created {count} accounts; existing passwords unchanged.")
    print(f"Local credentials sheet: {sheet}")

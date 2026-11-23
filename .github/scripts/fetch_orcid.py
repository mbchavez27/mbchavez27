import json
import os
import re
import urllib.request

ORCID_ID = os.environ["ORCID_ID"].strip()
ORCID_URL = f"https://pub.orcid.org/v3.0/{ORCID_ID}/works"


def fetch_json(url: str, headers: dict | None = None) -> dict:
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_crossref_venue(doi: str) -> str:
    try:
        data = fetch_json(
            f"https://api.crossref.org/works/{doi}",
            headers={
                "User-Agent": "github-readme-orcid-sync (mailto:noreply@github.com)"
            },
        )
        containers = data.get("message", {}).get("container-title", [])
        return containers[0] if containers else ""
    except Exception:
        return ""


def main() -> None:
    data = fetch_json(ORCID_URL, headers={"Accept": "application/json"})
    entries = []

    for group in data.get("group", []):
        summary = group["work-summary"][0]
        title = summary["title"]["title"]["value"].strip()

        pub_date = summary.get("publication-date") or {}
        year = (pub_date.get("year") or {}).get("value") or "n.d."
        month = (pub_date.get("month") or {}).get("value") or "00"

        venue = ((summary.get("journal-title") or {}).get("value") or "").strip()

        doi = ""
        url = ""
        for ext_id in summary.get("external-ids", {}).get("external-id", []):
            id_type = ext_id.get("external-id-type")
            id_val = ext_id.get("external-id-value", "").strip()
            if id_type == "doi" and id_val:
                doi = id_val
                url = f"https://doi.org/{doi}"
                break
            if id_type == "uri" and id_val and not url:
                url = id_val

        if not venue and doi:
            venue = get_crossref_venue(doi)

        # Match your lowercase README aesthetic
        title_clean = title.lower()
        venue_clean = venue.lower()

        link_md = f"[{title_clean}]({url})" if url else title_clean
        meta_parts = [p for p in [venue_clean, str(year)] if p]
        meta_str = f" · *{' · '.join(meta_parts)}*" if meta_parts else ""

        entries.append((f"{year}-{month}", f"**{link_md}**{meta_str}"))

    entries.sort(key=lambda x: x[0], reverse=True)

    # Render as clean centered lines matching your header block
    rendered = (
        "<br />\n".join(item[1] for item in entries)
        if entries
        else "*no public works found.*"
    )

    with open("README.md", "r", encoding="utf-8") as f:
        readme = f.read()

    updated = re.sub(
        r"<!-- ORCID_WORKS_START -->.*?<!-- ORCID_WORKS_END -->",
        f"<!-- ORCID_WORKS_START -->\n{rendered}\n<!-- ORCID_WORKS_END -->",
        readme,
        flags=re.DOTALL,
    )

    with open("README.md", "w", encoding="utf-8") as f:
        f.write(updated)


if __name__ == "__main__":
    main()

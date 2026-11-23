import html
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
        year = str((pub_date.get("year") or {}).get("value") or "n.d.")
        month = str((pub_date.get("month") or {}).get("value") or "00").zfill(2)

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

        # Lowercase formatting to match your README vibe
        title_esc = html.escape(title.lower())
        venue_esc = html.escape(venue.lower())

        title_html = (
            f'<a href="{url}"><b>{title_esc}</b></a>' if url else f"<b>{title_esc}</b>"
        )

        meta_items = []
        if venue_esc:
            meta_items.append(f"<i>{venue_esc}</i>")
        if doi:
            meta_items.append(f'<a href="https://doi.org/{html.escape(doi)}">doi</a>')

        meta_line = f"<br /><sub>{' · '.join(meta_items)}</sub>" if meta_items else ""

        row_html = (
            f"  <tr>\n"
            f'    <td align="center" valign="top" width="64"><code>{html.escape(year)}</code></td>\n'
            f'    <td align="left" valign="top">{title_html}{meta_line}</td>\n'
            f"  </tr>"
        )
        entries.append((f"{year}-{month}", row_html))

    entries.sort(key=lambda x: x[0], reverse=True)

    if entries:
        rows = "\n".join(item[1] for item in entries)
        rendered = f'<table width="620">\n{rows}\n</table>'
    else:
        rendered = "<p><i>no public works found.</i></p>"

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

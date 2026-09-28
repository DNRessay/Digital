from datetime import datetime, timezone

from . import Item, get

FEED = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"


def fetch(max=15):
    vulns = sorted(get(FEED).json()["vulnerabilities"], key=lambda v: v["dateAdded"], reverse=True)[:max]
    return [
        Item(
            id=f"cve:{v['cveID']}",
            title=f"{v['cveID']}: {v['vulnerabilityName']}",
            url=f"https://nvd.nist.gov/vuln/detail/{v['cveID']}",
            summary=f"{v['vendorProject']} {v['product']}. {v['shortDescription']} Required action: {v['requiredAction']}",
            source="CISA KEV",
            published=datetime.fromisoformat(v["dateAdded"]).replace(tzinfo=timezone.utc),
            extra={"ransomware": v.get("knownRansomwareCampaignUse")},
        )
        for v in vulns
    ]

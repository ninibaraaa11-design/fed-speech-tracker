#!/usr/bin/env python3
"""Discover new official Fed speeches by Warsh and Waller. No unverified AI summaries."""
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urljoin
from bs4 import BeautifulSoup

BASE = "https://www.federalreserve.gov"
OUT = Path("data/official_updates.json")
BASELINE = date(2026, 11, 23)
AGENT = {"User-Agent": "Fed-Speech-Tracker/1.0 (research; public pages)"}

def fetch(url):
    request = Request(url, headers=AGENT)
    with urlopen(request, timeout=25) as response:
        return BeautifulSoup(response.read(), "html.parser")

def scan_year(year):
    soup = fetch(f"{BASE}/newsevents/{year}-speeches.htm")
    output = []
    for anchor in soup.find_all("a", href=True):
        href = anchor["href"]
        match = re.search(r"/newsevents/speech/(warsh|waller)(20\d{6})[a-z]?\.htm", href, re.I)
        if not match:
            continue
        day = datetime.strptime(match.group(2), "%Y%m%d").date()
        if day <= BASELINE or day > date.today():
            continue
        url = urljoin(BASE, href)
        title = anchor.get_text(" ", strip=True)
        if not title or title.lower() in ("video", "watch live"):
            continue
        output.append({
            "id": match.group(1).lower() + match.group(2) + "-" + url.rsplit("/", 1)[-1],
            "person": "Warsh" if match.group(1).lower() == "warsh" else "Waller",
            "date": day.isoformat(),
            "title": title,
            "url": url,
            "source": "Federal Reserve Board official speech archive",
            "type": "正式演讲",
            "status": "待逐篇核验",
            "summary": "已发现美联储官方演讲。完整核心观点、AI态度、利率基点与前后变化尚未人工或逐字核验。",
            "aiView": "未核实",
            "rateDirection": "未核实",
            "rateBp": None,
            "change": "待核验"
        })
    return output

def main():
    existing = []
    if OUT.exists():
        existing = json.loads(OUT.read_text(encoding="utf-8"))
    by_url = {r["url"]: r for r in existing if r.get("url")}
    errors = []
    for year in range(2026, min(date.today().year + 1, 2030)):
        try:
            for row in scan_year(year):
                if row["url"] not in by_url:
                    by_url[row["url"]] = row
        except Exception as exc:
            errors.append(f"{year}: {exc}")
    if errors:
        raise RuntimeError("官方检索失败，不覆盖旧数据: " + "; ".join(errors))
    rows = sorted(by_url.values(), key=lambda r: (r["date"], r["person"], r["url"]), reverse=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    new_text = json.dumps(rows, ensure_ascii=False, indent=2) + "\n"
    if not OUT.exists() or OUT.read_text(encoding="utf-8") != new_text:
        OUT.write_text(new_text, encoding="utf-8")
        print(f"Stored {len(rows)} official records")
    else:
        print(f"No change; {len(rows)} official records")

if __name__ == "__main__":
    main()

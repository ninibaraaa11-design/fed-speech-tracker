#!/usr/bin/env python3
"""Translate one official Federal Reserve Board speech into full Chinese text.

Only written speeches on federalreserve.gov are eligible; never translate copyrighted
third-party interview transcripts without permission.
"""
import json
import os
import re
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from bs4 import BeautifulSoup

DATA = Path("data/translations.json")
MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
KEY = os.getenv("OPENAI_API_KEY", "")
TARGET = os.getenv("TRANSLATE_URL", "").strip()
LIMIT = int(os.getenv("TRANSLATE_MAX_PARAGRAPHS", "16"))
AGENT = {"User-Agent": "Mozilla/5.0 Fed-Speech-Tracker/1.1"}
URL_RE = re.compile(r"^https://www\.federalreserve\.gov/newsevents/speech/(waller|warsh)20\d{6}[a-z]?\.htm$")


def request(url, data=None, headers=None):
    hdr = dict(AGENT)
    hdr.update(headers or {})
    req = urllib.request.Request(url, data=data, headers=hdr,
                                 method="POST" if data else "GET")
    with urllib.request.urlopen(req, timeout=90) as response:
        return response.read()


def article(url):
    soup = BeautifulSoup(request(url), "html.parser")
    root = (soup.select_one("#article")
            or soup.select_one("div.col-xs-12.col-sm-8.col-md-8")
            or soup.select_one("main"))
    if root is None:
        raise RuntimeError("无法识别官方演讲正文区域，已停止，防止不完整翻译")
    for n in root.select("script, style, nav, header, footer, aside, .share, .footnotes, .social-media, .related-links"):
        n.decompose()
    paragraphs = []
    for element in root.find_all(["h1", "h2", "h3", "p", "li"]):
        if element.find_parent(["p", "li"]):  # avoid duplicate descendants
            continue
        value = element.get_text(" ", strip=True)
        if len(value) < 2:
            continue
        if value.lower().startswith(("share", "related links", "return to top")):
            continue
        paragraphs.append({"kind": element.name, "en": value})
    if sum(len(p["en"]) for p in paragraphs) < 400:
        raise RuntimeError("提取正文过短，不可标为全文")
    title = (soup.find("h1").get_text(" ", strip=True) if soup.find("h1") else url)
    return title, paragraphs


def ai_translate(batch):
    request_body = {
        "model": MODEL,
        "input": [
            {"role": "developer", "content":
             "你是美联储政策研究专业译者。严格逐段完整翻译英文为简体中文，不删除任何句子、不自行添加分析，不改数字和基点。保留段落顺序。输出JSON对象，唯一键 translations，其值是与输入段落一一对应的中文字符串数组。不翻译源文缺失内容。"},
            {"role": "user", "content": json.dumps({"paragraphs": batch}, ensure_ascii=False)}
        ],
        "text": {"format": {"type": "json_object"}},
        "max_output_tokens": 5500
    }
    resp = json.loads(request("https://api.openai.com/v1/responses",
               json.dumps(request_body).encode("utf-8"),
               {"Authorization": "Bearer " + KEY, "Content-Type": "application/json"}))
    text = resp.get("output_text") or "\n".join(
        part.get("text", "") for entry in resp.get("output", [])
        for part in entry.get("content", []) if part.get("type") == "output_text"
    )
    translations = json.loads(text)["translations"]
    if len(translations) != len(batch) or not all(isinstance(x, str) and x.strip() for x in translations):
        raise ValueError("译文段落数不一致或有空段，拒绝保存")
    return translations


def choose_url(records):
    if TARGET:
        if not URL_RE.fullmatch(TARGET):
            raise ValueError("仅支持美联储官网沃什/沃勒书面演讲")
        return TARGET
    # Backfill short, historical written Federal Reserve speech first, one per run.
    html = Path("index.html").read_text(encoding="utf-8")
    raw = html.split("const DATA=", 1)[1]
    existing, _ = json.JSONDecoder().raw_decode(raw)
    candidates = [
        r for r in existing
        if r.get("official") and URL_RE.fullmatch(r.get("url", ""))
        and r["url"] not in records
    ]
    candidates.sort(key=lambda r: (r["date"], r.get("person", "")), reverse=True)
    return candidates[0]["url"] if candidates else None


def main():
    if not KEY:
        print("未配置OPENAI_API_KEY，跳过翻译")
        return
    records = json.loads(DATA.read_text(encoding="utf-8")) if DATA.exists() else {}
    url = choose_url(records)
    if not url:
        print("没有需要处理的官方书面演讲")
        return
    title, segments = article(url)
    # Limit API cost and avoid mislabeling incomplete work as a full translation.
    if len(segments) > LIMIT:
        print(f"原文段落数 {len(segments)} 超过本次预算 {LIMIT}，不保存不完整译稿：{url}")
        return
    full = []
    for i in range(0, len(segments), 4):
        chunk = segments[i:i + 4]
        output = ai_translate([x["en"] for x in chunk])
        full.extend({"kind": p["kind"], "en": p["en"], "zh": zh}
                    for p, zh in zip(chunk, output))
        time.sleep(0.25)
    if len(full) != len(segments):
        raise RuntimeError("未完成全部段落，拒绝发布")
    records[url] = {
        "title": title,
        "source": url,
        "status": "AI逐段完整译稿（非官方译文，尚待人工审校）",
        "paragraphCount": len(full),
        "translatedAtUTC": datetime.now(timezone.utc).isoformat(),
        "paragraphs": full
    }
    DATA.parent.mkdir(parents=True, exist_ok=True)
    DATA.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"已完成 {len(full)} 段翻译：{url}")


if __name__ == "__main__":
    main()

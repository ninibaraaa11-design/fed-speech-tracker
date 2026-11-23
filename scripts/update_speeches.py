#!/usr/bin/env python3
"""Incremental, source-grounded Fed speech monitor. AI analysis requires OPENAI_API_KEY."""
import json, os, re, sys, time, urllib.request, urllib.parse, xml.etree.ElementTree as ET
from datetime import datetime, date, timezone
from pathlib import Path
from bs4 import BeautifulSoup

BASE = "https://www.federalreserve.gov"
START = date(2026, 11, 23)
AGENT = {"User-Agent": "Mozilla/5.0 Fed-Speech-Tracker/1.1 (public research)"}
OFFICIAL = Path("data/official_updates.json")
MEDIA = Path("data/media_candidates.json")
ANALYSIS = Path("data/analyses.json")
MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
API_KEY = os.getenv("OPENAI_API_KEY", "")
MAX_AI_PER_RUN = int(os.getenv("MAX_AI_PER_RUN", "6"))

def request(url, data=None, headers=None):
    h = dict(AGENT)
    if headers: h.update(headers)
    r = urllib.request.Request(url, data=data, headers=h, method="POST" if data else "GET")
    with urllib.request.urlopen(r, timeout=50) as res:
        return res.read()

def read_json(path, fallback):
    if not path.exists(): return fallback
    return json.loads(path.read_text(encoding="utf-8"))

def save_json(path, obj):
    body = json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() or path.read_text(encoding="utf-8") != body:
        path.write_text(body, encoding="utf-8")
        print("Updated", path, "entries", len(obj))
    else: print("Unchanged", path)

def official_scan():
    rows = read_json(OFFICIAL, [])
    by_url = {r["url"]:r for r in rows}
    errors = []
    for year in range(2026, datetime.now(timezone.utc).year + 1):
        try:
            soup = BeautifulSoup(request(f"{BASE}/newsevents/{year}-speeches.htm"), "html.parser")
            found = 0
            for a in soup.find_all("a", href=True):
                url = urllib.parse.urljoin(BASE, a["href"]).split("?")[0]
                m = re.fullmatch(r"https://www\.federalreserve\.gov/newsevents/speech/(warsh|waller)(20\d{6})[a-z]?\.htm", url, re.I)
                if not m: continue
                when = datetime.strptime(m.group(2), "%Y%m%d").date()
                if when <= START or when > datetime.now(timezone.utc).date(): continue
                if url in by_url: continue
                title = a.get_text(" ", strip=True)
                by_url[url] = dict(
                    id=m.group(1).lower() + m.group(2), person=m.group(1).capitalize(),
                    date=when.isoformat(), title=title or "新增官方发言", url=url,
                    source="Federal Reserve Board official archive",
                    type="正式演讲", status="待逐篇核验",
                    summary="新发现官方发言，尚未完成内容核验。",
                    aiView="未核实", rateDirection="未核实", rateBp=None, change="待核验"
                )
                found += 1
            print(f"Official {year}: added {found}")
        except Exception as exc: errors.append(f"{year}: {exc}")
    if errors: raise RuntimeError("Official archive unavailable; no data overwritten: " + "; ".join(errors))
    rows = sorted(by_url.values(), key=lambda x:(x["date"],x["person"],x["url"]), reverse=True)
    save_json(OFFICIAL, rows)
    return rows

def media_scan():
    """Google News RSS is discovery ONLY, never proof that a full interview occurred."""
    rows = read_json(MEDIA, [])
    by_id = {r["id"]:r for r in rows}
    for person, fullname in (("Warsh","Kevin Warsh"),("Waller","Christopher Waller")):
        for medium in ("interview CNBC Bloomberg Reuters", "speech remarks interview"):
            q = urllib.parse.quote(f'"{fullname}" {medium} when:7d')
            url = f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"
            try:
                root = ET.fromstring(request(url))
                for item in root.findall(".//item")[:30]:
                    title = (item.findtext("title") or "").strip()
                    link = (item.findtext("link") or "").strip()
                    date_text = (item.findtext("pubDate") or "").strip()
                    if not link or fullname.casefold() not in title.casefold(): continue
                    if not re.search(r"interview|remarks|speech|says|tells|speaks|comments|discusses",title,re.I): continue
                    ident = re.sub(r"[^a-z0-9]", "", link.casefold())[-100:]
                    if ident in by_id: continue
                    by_id[ident] = dict(id=ident,person=person,datePublished=date_text,title=title,
                        url=link,source="Google News RSS search (secondary discovery)",
                        status="媒体线索：未核验原始采访及全文",rateBp=None,aiView="未核实")
            except Exception as exc: print("Media discovery unavailable (nonfatal):",person,str(exc),file=sys.stderr)
    rows = sorted(by_id.values(),key=lambda r:r.get("datePublished",""),reverse=True)[:250]
    save_json(MEDIA,rows)

def extract_official(url):
    soup = BeautifulSoup(request(url),"html.parser")
    for node in soup(["script","style","nav","header","footer"]): node.decompose()
    # Official site currently places the speech text in the main article column.
    root = soup.select_one("#article") or soup.select_one(".col-xs-12.col-sm-8.col-md-8") or soup.find("main")
    if root is None: raise ValueError("Missing article container")
    for node in root.select(".share, .social-media, .related-links, .footnotes, aside"):
        node.decompose()
    parts = [p.get_text(" ",strip=True) for p in root.find_all(["h2","h3","p","li"]) if p.get_text(" ",strip=True)]
    text = "\n".join(parts)
    if len(text) < 300: raise ValueError("Official text too short to analyze")
    return text[:22000]

def extract_output_text(resp):
    if resp.get("output_text"): return resp["output_text"]
    return "\n".join(c.get("text","") for item in resp.get("output",[]) for c in item.get("content",[]) if c.get("type")=="output_text")

def ask_ai(record, text, predecessor):
    instructions = """你是严格证据优先的美联储研究员。只根据提供的官方演讲原文提炼事实，中文回答。
请输出纯JSON对象，不要markdown，字段必须包含：
summary(详细中文概要字符串),
details(数组，每项{tag,text}，至少5条，尽量覆盖货币政策、通胀、就业、增长、AI/生产率、支付/监管中原文实际提到的主题),
aiStatus(明确提及AI/未提及AI/证据不足),
aiDetail(有AI时详细陈述，没提到则写未提及，不推论),
rateDirection(加息/降息/维持/条件性/未提出),
rateBp(仅当讲话明确支持或提到基点时填写如+25bp、-50bp，未明确写未提出；FOMC决议不是个人主张),
rateMeeting(具体会议或未提出),
rateNote(准确解释本人主张与条件性，不自行推断),
rateProof(支持基点判断的英文原文短摘录，最多20个英文词，或写未提出),
delta(新增/强化/弱化/调整/反转/无法判断),
change(只与提供的同一人物前次已核验资料比较，若前次不可验证则写无法判断),
evidence(2至4条，每条{claim,quote}，quote为本次原文中的精确英文短引文不超20词)。
绝不编造发言场合、引文、数值、基点；原文没有AI则明确无AI观点。输出可解析JSON。"""
    payload = {
        "model": MODEL,
        "input":[{"role":"developer","content":instructions},
           {"role":"user","content":json.dumps({"date":record["date"],"person":record["person"],
                "title":record["title"],"source":record["url"],"previous_verified":predecessor,
                "official_full_text":text},ensure_ascii=False)}],
        "text":{"format":{"type":"json_object"}},
        "max_output_tokens":2800
    }
    body=request("https://api.openai.com/v1/responses",
        data=json.dumps(payload).encode(),headers={"Authorization":"Bearer "+API_KEY,
        "Content-Type":"application/json"})
    out=json.loads(extract_output_text(json.loads(body)))
    for field in ("summary","details","aiStatus","aiDetail","rateDirection","rateBp",
                  "rateMeeting","rateNote","rateProof","delta","change","evidence"):
        if field not in out: raise ValueError("AI JSON missing "+field)
    if not isinstance(out["details"],list): raise ValueError("Invalid details")
    # Simple evidence check: no invented textual quote can pass.
    lower_text=" ".join(text.split()).casefold()
    for item in out["evidence"]:
        quote=" ".join(str(item.get("quote","")).split())
        if quote and quote.casefold() not in lower_text: raise ValueError("Unverifiable evidence quote")
    proof=out["rateProof"]
    if proof!="未提出" and " ".join(proof.split()).casefold() not in lower_text:
        raise ValueError("Unverifiable rate quote")
    return out

def historical_baseline():
    """Use original dashboard summaries as comparison context, not verified transcripts."""
    try:
        html = Path("index.html").read_text(encoding="utf-8")
        raw = html.split("const DATA=", 1)[1]
        parsed, _ = json.JSONDecoder().raw_decode(raw)
        return parsed if isinstance(parsed, list) else []
    except (OSError, ValueError, IndexError):
        return []

def analyze(rows):
    baseline=historical_baseline()
    analyses=read_json(ANALYSIS,{})
    if not API_KEY:
        print("OPENAI_API_KEY not configured: skip AI analysis, no fabricated conclusions")
        return
    count=0
    chronological=sorted(rows,key=lambda r:(r["date"],r["person"],r["url"]))
    for row in chronological:
        if row["url"] in analyses or count>=MAX_AI_PER_RUN:continue
        try:
            previous=[v for v in analyses.values() if v.get("person")==row["person"] and v.get("date","")<row["date"]]
            previous=sorted(previous,key=lambda p:p["date"])
            prior={"date":previous[-1]["date"],"summary":previous[-1]["summary"],
                   "rateDirection":previous[-1]["rateDirection"],"aiDetail":previous[-1]["aiDetail"],
                   "confidence":"AI-generated analysis, citation check"} if previous else None
            if prior is None:
                historical=[v for v in baseline if v.get("person")==row["person"] and v.get("date","")<row["date"]]
                historical.sort(key=lambda v:v["date"])
                if historical:
                    v=historical[-1]
                    prior={"date":v["date"],"summary":v.get("summary",""),
                           "rateDirection":v.get("rateDirection",""),
                           "aiDetail":v.get("aiDetail",""),
                           "confidence":"历史看板研究摘要，尚未在本任务中逐字重新核对，比较需谨慎"}
            text=extract_official(row["url"])
            output=ask_ai(row,text,prior)
            analyses[row["url"]]=dict(output,person=row["person"],date=row["date"],
                title=row["title"],url=row["url"],source="Official Federal Reserve speech",
                status="AI初稿：短引文机器核验通过；仍建议人工复核",fullTextAvailable=True)
            count += 1
            print("AI analyzed",row["date"],row["person"])
            time.sleep(0.5)
        except Exception as exc:
            print("AI analysis failed; retains provisional record:",row["url"],str(exc),file=sys.stderr)
    save_json(ANALYSIS,analyses)

def main():
    rows=official_scan()
    media_scan()
    analyze(rows)
    print("Completed. Official records:",len(rows))

if __name__=="__main__":
    main()

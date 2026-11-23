#!/usr/bin/env python3
"""Official-source Fedspeak archive since 2026-09-01. No API use, no invented quotes."""
import json, re, urllib.request, urllib.parse, sys
from pathlib import Path
from datetime import datetime, date, timezone
from bs4 import BeautifulSoup

OUT=Path("data/all_fed_officials.json")
START=date(2026,9,1)
CUTOFF=datetime.now(timezone.utc).date()
HEADERS={"User-Agent":"Mozilla/5.0 (compatible; fed-speech-research/1.0)"}
BOARD="https://www.federalreserve.gov/newsevents/2026-speeches.htm"
NAMES={"warsh":"Kevin Warsh","waller":"Christopher Waller","bowman":"Michelle Bowman",
"barr":"Michael Barr","cook":"Lisa Cook","jefferson":"Philip Jefferson",
"powell":"Jerome Powell","miran":"Stephen Miran","kugler":"Adriana Kugler"}
REGIONAL=[
("New York Fed","John Williams","https://www.newyorkfed.org/newsevents/speeches/index"),
("St. Louis Fed","Alberto Musalem","https://www.stlouisfed.org/from-the-president/remarks"),
("Dallas Fed","Lorie Logan","https://www.dallasfed.org/news/speeches/logan"),
("Cleveland Fed","Beth Hammack","https://www.clevelandfed.org/collections/speeches"),
("San Francisco Fed","Mary Daly","https://www.frbsf.org/news-and-media/speeches/"),
("Kansas City Fed","Jeff Schmid","https://www.kansascityfed.org/speeches/"),
("Philadelphia Fed","Anna Paulson","https://www.philadelphiafed.org/the-economy/speeches-anna-paulson"),
("Chicago Fed","Austan Goolsbee","https://www.chicagofed.org/publications/speeches"),
("Boston Fed","Susan Collins","https://www.bostonfed.org/news-and-events/speeches.aspx"),
("Richmond Fed","Thomas Barkin","https://www.richmondfed.org/press_room/speeches"),
("Minneapolis Fed","Neel Kashkari","https://www.minneapolisfed.org/speeches"),
("Atlanta Fed","Cheryl Venable","https://www.atlantafed.org/about/atlantafed/officers/president/speeches"),
]
DOMAINS=("federalreserve.gov","newyorkfed.org","stlouisfed.org","dallasfed.org","clevelandfed.org",
"frbsf.org","kansascityfed.org","philadelphiafed.org","chicagofed.org","bostonfed.org",
"richmondfed.org","minneapolisfed.org","atlantafed.org")
MONTHS={x:i for i,x in enumerate(("January","February","March","April","May","June","July","August","September","October","November","December"),1)}

def fetch(url):
    if urllib.parse.urlparse(url).hostname not in DOMAINS:raise ValueError("Source domain not official")
    req=urllib.request.Request(url,headers=HEADERS)
    with urllib.request.urlopen(req,timeout=22) as f:return BeautifulSoup(f.read(),"html.parser")

def date_from(text):
    patterns=[r"\b(20\d{2})-(\d\d)-(\d\d)\b",r"\b(\d\d?)/(\d\d?)/(20\d{2})\b",
              r"\b("+"|".join(MONTHS)+r")\s+(\d\d?),?\s+(20\d{2})\b"]
    for i,p in enumerate(patterns):
        m=re.search(p,text,re.I)
        if not m:continue
        try:
            a,b,c=m.groups()
            if i==0:return date(int(a),int(b),int(c))
            if i==1:return date(int(c),int(a),int(b))
            return date(int(c),MONTHS[a.title()],int(b))
        except (ValueError,KeyError):continue

def valid_when(day):return day is not None and START<=day<=CUTOFF

def discover_board():
    rows=[]
    soup=fetch(BOARD)
    for a in soup.select('a[href]'):
        url=urllib.parse.urljoin(BOARD,a["href"]).split("?")[0]
        match=re.search(r"/newsevents/speech/([a-z]+)(20\d{6})[a-z]?\.htm$",url,re.I)
        if not match:continue
        slug=match.group(1).lower()
        if slug not in NAMES:continue
        try:day=datetime.strptime(match.group(2),"%Y%m%d").date()
        except ValueError:continue
        if not valid_when(day):continue
        title=a.get_text(" ",strip=True)
        if title.lower() in ("video","watch live") or len(title)<5:continue
        rows.append(dict(date=day.isoformat(),speaker=NAMES[slug],title=title,url=url,
                         source="Federal Reserve Board",kind="正式演讲"))
    return rows

def discover_regional(bank,name,index):
    soup=fetch(index)
    rows=[]
    for a in soup.select("a[href]"):
        url=urllib.parse.urljoin(index,a["href"]).split("?")[0]
        domain=urllib.parse.urlparse(url).hostname or ""
        if domain not in DOMAINS or url==index:continue
        path=urllib.parse.urlparse(url).path.lower()
        if not any(k in path for k in ("speech","remark","president","address")):continue
        title=a.get_text(" ",strip=True)
        if len(title)<13 or len(title)>190 or title.lower() in ("read more","read the speech","watch the speech"):continue
        container=a.find_parent(["article","li","div"])
        context=container.get_text(" ",strip=True)[:350] if container else title
        day=date_from(context)
        if not valid_when(day):continue
        rows.append(dict(date=day.isoformat(),speaker=name,title=title,url=url,source=bank,kind="官方演讲页面"))
    return rows

def sentences(text):
    # Do not summarize with model; retain original exact sentences.
    return [x.strip() for x in re.split(r"(?<=[.!?])\s+(?=[A-Z“\"'])",text) if len(x.strip())>32 and len(x)<650]

HAWK=(r"\braise (?:the )?(?:policy |interest )?rates?\b",r"\bhike (?:the )?rates?\b",
      r"\bfurther (?:tightening|rate increases?)\b",r"\bneed to (?:increase|raise) (?:the )?(?:policy )?rates?\b",
      r"\binflation (?:remains|is) (?:too|unacceptably) high\b")
DOVE=(r"\bcut (?:the )?(?:policy |interest )?rates?\b",r"\blower (?:the )?(?:policy |interest )?rates?\b",
      r"\brate cuts? (?:are|is) (?:appropriate|warranted|needed)\b",
      r"\bneed to (?:reduce|lower) (?:the )?(?:policy )?rates?\b")
NEG=r"\b(?:not|no|don't|doesn't|wouldn't|shouldn't|cannot|can't)\b"
TOPICS=[("通胀","inflation"),("就业/劳动力","labor market"),("经济增长","economic growth"),
        ("生产率","productivity"),("人工智能","artificial intelligence"),("利率","interest rates"),
        ("金融稳定","financial stability"),("支付","payments")]

def enrich(row):
    if row.get("reviewedAt") or row.get("reviewStatus")=="原文访问失败":return row
    try:
        soup=fetch(row["url"])
        main=(soup.select_one("#article") or soup.select_one("main")
              or soup.select_one("article") or soup.select_one('[role="main"]'))
        if main is None:raise ValueError("article not found")
        for a in main.select("nav,footer,header,script,style,aside,.related,.share"):a.decompose()
        paragraphs=[x.get_text(" ",strip=True) for x in main.find_all("p")]
        paragraphs=[s for s in paragraphs if len(s)>40]
        if len(" ".join(paragraphs))<350:raise ValueError("insufficient full text")
        ss=sentences(" ".join(paragraphs))
        matched=[]
        for sentence in ss:
            h=any(re.search(p,sentence,re.I) for p in HAWK)
            d=any(re.search(p,sentence,re.I) for p in DOVE)
            if not (h or d):continue
            # A negation or conditional clause needs human interpretation, never forced to binary stance.
            if re.search(NEG,sentence,re.I) or re.search(r"\bif\b|\bunless\b|\bwould\b",sentence,re.I):continue
            matched.append((h,d,sentence))
        hawks=[s for h,d,s in matched if h and not d]
        doves=[s for h,d,s in matched if d and not h]
        if hawks and not doves:stance="偏鹰（规则初判）"; evidence=hawks[0]
        elif doves and not hawks:stance="偏鸽（规则初判）"; evidence=doves[0]
        elif hawks and doves:stance="混合（规则初判）"; evidence=hawks[0]+" "+doves[0]
        else:stance="未明确表态";evidence=""
        selected=[]
        for zh,en in TOPICS:
            item=next((s for s in ss if en in s.lower() and len(s)<350),None)
            if item:selected.append(dict(topic=zh,quote=item))
            if len(selected)>=4:break
        if evidence and not any(p.get("quote")==evidence for p in selected):
            selected.insert(0,dict(topic="政策方向",quote=evidence))
        bp=re.findall(r"\b(?:25|50|75|100)\s*(?:basis points?|bps?)\b",evidence,re.I)
        row.update(stance=stance,evidence=evidence[:500],points=selected[:5],
                   summary=("；".join(p["topic"] for p in selected) or "未在正文中提取到可明确分类的政策句子")+"（自动主题索引，点击原文核对）",
                   rateBp="、".join(bp) if bp else "未明确提及",
                   confidence="官方网页正文+关键词规则初判；非人工政策评级",
                   reviewStatus="自动提取",reviewedAt=datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    except Exception as e:
        row.setdefault("stance","未判定")
        row.setdefault("summary","已记录官方来源，正文或政策立场尚未核验")
        row.setdefault("rateBp","未核实")
        row["reviewStatus"]="原文访问失败"
        row["reviewError"]=str(e)[:140]
    return row

def main():
    rows=json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else []
    by_url={r["url"]:r for r in rows if r.get("url")}
    diagnostics={}
    try:
        board=discover_board()
        diagnostics["Board"]=len(board)
        for x in board:by_url.setdefault(x["url"],x)
    except Exception as e:diagnostics["Board error"]=str(e)
    # Parallel archives not guaranteed to publish every interview; source coverage is explicit.
    for bank,name,index in REGIONAL:
        try:
            found=discover_regional(bank,name,index)
            diagnostics[bank]=len(found)
            for x in found:by_url.setdefault(x["url"],x)
        except Exception as e:diagnostics[bank+" error"]=str(e)[:100]
    if not by_url and "Board error" in diagnostics:raise RuntimeError(str(diagnostics))
    # Bound external requests; older records are processed gradually, newest first.
    results=sorted(by_url.values(),key=lambda x:(x.get("date",""),x.get("speaker","")),reverse=True)
    pending=[r for r in results if not r.get("reviewedAt") and r.get("reviewStatus")!="原文访问失败"]
    for row in pending[:12]:enrich(row)
    OUT.parent.mkdir(exist_ok=True)
    new=json.dumps(results,ensure_ascii=False,indent=2)+"\n"
    if not OUT.exists() or OUT.read_text(encoding="utf-8")!=new:OUT.write_text(new,encoding="utf-8")
    print("Sources",json.dumps(diagnostics,ensure_ascii=False))
    print("Total",len(results),"processed",min(len(pending),12),"api_calls=0")
if __name__=="__main__":main()

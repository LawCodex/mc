#!/usr/bin/env python3
"""Convert Legimonaco HTML pages cached by mc_fetch.py into Markdown files."""
import datetime
import hashlib
import json
import os
import re
import shutil
import sys
import unicodedata
from collections import Counter

from bs4 import BeautifulSoup, NavigableString, Tag
from markdownify import MarkdownConverter

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
RAW = os.path.abspath(os.environ.get("MC_RAW", os.path.join(REPO, "..", "_raw", "mc")))
BASE = "https://legimonaco.mc"
RETRIEVED = os.environ.get("MC_RETRIEVED", datetime.date.today().isoformat())

NATURE_DIR = {
    "loi": ("lois", "act"),
    "ordonnance-loi": ("lois", "ordinance_law"),
    "ordonnance": ("ordonnances-souveraines", "sovereign_ordinance"),
    "arrete-ministeriel": ("arretes-ministeriels", "ministerial_order"),
    "arrete-municipal": ("arretes-municipaux", "municipal_order"),
    "decision-ministerielle": ("decisions-ministerielles", "ministerial_decision"),
    "autre-texte-reglementaire": ("autres-textes-reglementaires", "regulation"),
    "arrete-directorial": ("arretes-directoriaux", "directorial_order"),
    "decision-souveraines": ("decisions-souveraines", "sovereign_decision"),
    "decision": ("decisions", "decision"),
}


def slugify(s, maxlen=80):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return s[:maxlen].rstrip("-") or "texte"


class MD(MarkdownConverter):
    def convert_u(self, el, text, *a, **k):
        return text

    def convert_span(self, el, text, *a, **k):
        return text


def md(html_frag):
    t = MD(heading_style="ATX", bullets="-", strip=["a"] if False else None).convert(html_frag)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def heading_text(sec):
    h = sec.find(re.compile(r"^h[1-6]$"), class_="section_ti", recursive=False)
    if not h:
        return None
    tt = h.find(class_="title_text") or h
    for x in tt.find_all(class_="noIndex"):
        x.decompose()
    t = re.sub(r"\s+", " ", tt.get_text("")).strip()
    return t


class Conv:
    def __init__(self):
        self.out = []
        self.notes = {}

    def note_ref(self, sup):
        a = sup.find("a")
        nid = (a.get("href") or "#").lstrip("#") if a else ""
        if nid not in self.notes:
            self.notes[nid] = len(self.notes) + 1
        return f"[^{self.notes[nid]}]"

    def prep(self, el):
        """Clean a content fragment in place (drop UI widgets, convert note refs)."""
        for x in el.find_all(class_=re.compile(r"noIndex|histoLink|pageOutline|artList|docList|title_tools")):
            x.decompose()
        for x in el.find_all("button"):
            x.decompose()
        for x in el.find_all("span", class_="note"):
            x.decompose()
        for sup in el.find_all("sup", class_="editoNote_ref"):
            sup.replace_with(NavigableString(self.note_ref(sup)))
        for img in el.find_all("img"):
            src = img.get("src") or ""
            if src and not src.startswith("http"):
                src = BASE + "/" + src.lstrip("./")
            img.replace_with(NavigableString(f"[Image : {src}]({src})" if src else ""))

    def walk(self, el, depth):
        for c in el.children:
            if not isinstance(c, Tag):
                continue
            cls = c.get("class") or []
            if c.name == "section" and "legContainer" in cls:
                t = heading_text(c)
                lvl = depth + 2
                if t:
                    self.out.append(("#" * lvl + " " + t) if lvl <= 6 else f"**{t}**")
                co = c.find("div", class_="section_co", recursive=False)
                if co:
                    self.walk(co, depth + 1)
                continue
            if c.name == "section" and "art" in cls:
                t = heading_text(c)
                lvl = depth + 2
                if t:
                    self.out.append(("#" * lvl + " " + t) if lvl <= 6 else f"**{t}**")
                co = c.find("div", class_="section_co", recursive=False)
                if co:
                    self.walk(co, depth + 1)
                continue
            if c.name == "section" and "block" in cls or c.name == "div" and "text" in cls:
                self.prep(c)
                t = md(str(c))
                if t:
                    self.out.append(t)
                continue
            if c.name == "aside" and "histo" in cls:
                if "noIndex" in cls or c.get("hidden"):
                    continue
                self.prep(c)
                t = md(str(c))
                if t:
                    self.out.append("\n".join("> " + x if x else ">" for x in t.split("\n")))
                continue
            if c.name == "aside" and "editoNotes" in cls:
                continue
            if c.name in ("header", "nav", "script", "style", "button"):
                continue
            if c.name == "p" and "histoLink" in cls:
                continue
            if c.name in ("ul", "i") and set(cls) & {"pageOutline", "artList"}:
                continue
            if c.name in ("div", "section") and not (set(cls) & {"docList_frame", "docList_dialog", "referencedDocuments"}):
                self.walk(c, depth)
                continue
            if c.name in ("p", "table", "ul", "ol", "blockquote"):
                self.prep(c)
                t = md(str(c))
                if t:
                    self.out.append(t)


def info(soup):
    d = {}
    for b in soup.select("header.documentInfo div.infoBlock"):
        lab = b.find(class_="infoLabel")
        val = b.find(class_="infoValue")
        if not lab or not val:
            continue
        key = lab.get("data-l10n") or lab.get_text(strip=True)
        a = val.find("a")
        d[key] = {"text": re.sub(r"\s+", " ", val.get_text(" ", strip=True)),
                  "date": val.get("data-l10n-date"), "href": a.get("href") if a else None}
    return d


def convert(it, raw):
    soup = BeautifulSoup(raw, "lxml")
    content = soup.find(id="content")
    if content is None:
        return None, None
    h1 = content.find("h1")
    title = re.sub(r"\s+", " ", h1.get_text(" ", strip=True)) if h1 else it.get("title", "")
    inf = info(content)
    conv = Conv()
    # editorial notes
    notes_aside = content.find("aside", class_="editoNotes")
    note_texts = {}
    if notes_aside:
        for li in notes_aside.find_all("li", class_="editoNotes_it"):
            co = li.find(class_="editoNotes_itco")
            if co:
                conv.prep(co)
                note_texts[li.get("id")] = md(str(co)).replace("\n\n", " ").replace("\n", " ")
    for x in content.find_all("header", class_=re.compile("documentTitle|documentInfo")):
        x.decompose()
    conv.walk(content, 0)
    typ = it["type"]
    nature = it.get("tncNature")
    if typ == "constitution":
        ftype = "constitution"
    elif typ == "tc":
        ftype = "code"
    elif typ == "tai":
        ftype = "treaty"
    else:
        ftype = NATURE_DIR.get(nature, ("autres", "other"))[1]
    path = it["path"]
    m = re.search(r"@(\d{4})\.(\d{2})\.(\d{2})", path)
    version = f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else None
    meta = {"title": title}
    if it.get("number"):
        meta["identifier"] = it["number"]
    meta["type"] = ftype
    meta["jurisdiction"] = "mc"
    meta["language"] = "fr"
    date = (inf.get("textDate") or {}).get("date") or (it.get("date") if typ not in ("tc", "constitution") else None)
    if typ == "constitution":
        date = "1962-12-17"
    if date:
        meta["date"] = date
    if version:
        meta["last_amended"] = version
    elif typ == "constitution":
        meta["last_amended"] = "2002-04-02"  # loi n° 1.249 du 2 avril 2002 portant révision de la Constitution
    meta["status"] = "in_force"
    if inf.get("party"):
        meta["party"] = inf["party"]["text"]
    if inf.get("enteredForceDomestic") and inf["enteredForceDomestic"].get("date"):
        meta["in_force_domestic"] = inf["enteredForceDomestic"]["date"]
    pub = inf.get("publication")
    if pub:
        href = pub.get("href") or ""
        if href.startswith("/"):
            # treaties: link to the sovereign ordinance that made the text enforceable
            meta["published_by"] = BASE + href.split("@")[0]
        else:
            meta["publication"] = pub["text"]
            if href:
                meta["publication_url"] = href
    if inf.get("theme"):
        meta["thematic"] = inf["theme"]["text"]
    meta["source"] = BASE + path.split("@")[0] if typ not in ("constitution",) else BASE + "/constitution"
    if version:
        meta["source_version"] = BASE + path + "/"
    meta["retrieved"] = RETRIEVED
    fm = ["---"]
    for k, v in meta.items():
        if k in ("type", "jurisdiction", "language", "status", "date", "last_amended", "retrieved", "in_force_domestic"):
            fm.append(f"{k}: {v}")
        else:
            fm.append(f"{k}: " + json.dumps(v, ensure_ascii=False))
    fm.append("---")
    body = "\n\n".join(x for x in conv.out if x)
    parts = ["\n".join(fm), f"# {title}", body]
    if conv.notes:
        nl = []
        for nid, n in sorted(conv.notes.items(), key=lambda x: x[1]):
            nl.append(f"[^{n}]: {note_texts.get(nid, '')}".rstrip())
        parts.append("---\n\n" + "\n\n".join(nl))
    return "\n\n".join(p for p in parts if p).rstrip() + "\n", ftype


def rel_path(it, used):
    typ = it["type"]
    if typ == "constitution":
        return "constitution/constitution.md"
    if typ == "tc":
        name = it["path"].split("/")[2].split("@")[0]
        return f"codes/{name}.md"
    if typ == "tai":
        date = it.get("date") or "0000-00-00"
        nat = it.get("taiNature") or it["path"].split("/")[2]
        name = f"{date}-{slugify(nat, 30)}-{slugify(it.get('number') or it['path'].split('/')[-1].split('@')[0], 30)}"
        base, k = name, 2
        while f"traites/{date[:4]}/{name}" in used:
            name = f"{base}-{k}"
            k += 1
        used.add(f"traites/{date[:4]}/{name}")
        return f"traites/{date[:4]}/{name}.md"
    nature = it.get("tncNature") or "autre"
    d = NATURE_DIR.get(nature, ("autres", "other"))[0]
    date = it.get("date") or "0000-00-00"
    num = (it.get("number") or "").replace(".", "")
    num = slugify(num) if num else slugify(it["path"].split("/")[-1].split("@")[0])
    name = f"{date}-{nature}-{num}"
    base = name
    k = 2
    while f"{d}/{date[:4]}/{name}" in used:
        name = f"{base}-{k}"
        k += 1
    used.add(f"{d}/{date[:4]}/{name}")
    return f"{d}/{date[:4]}/{name}.md"


def main():
    items = json.load(open(os.path.join(RAW, "index.json")))
    items = [i for i in items if i.get("legislationAbrogated") != "yes" and i.get("regulationAbrogated") != "yes"]
    for d in ["constitution", "codes", "traites"] + sorted({v[0] for v in NATURE_DIR.values()}) + ["autres"]:
        p = os.path.join(REPO, d)
        if os.path.isdir(p):
            shutil.rmtree(p)
    used = set()
    stats = Counter()
    missing = []
    for it in sorted(items, key=lambda i: (i["type"], i.get("date") or "", i.get("number") or "", i["path"])):
        f = os.path.join(RAW, "pages", hashlib.sha1(it["path"].encode()).hexdigest() + ".html")
        if not os.path.exists(f):
            missing.append(it["path"])
            continue
        md_text, ftype = convert(it, open(f, "rb").read().decode("utf-8", "replace"))
        if not md_text:
            missing.append(it["path"])
            continue
        rp = rel_path(it, used)
        fp = os.path.join(REPO, rp)
        os.makedirs(os.path.dirname(fp), exist_ok=True)
        open(fp, "w", encoding="utf-8").write(md_text)
        stats[rp.split("/")[0]] += 1
    print(dict(stats), file=sys.stderr)
    print("missing", len(missing), missing[:10], file=sys.stderr)


if __name__ == "__main__":
    main()

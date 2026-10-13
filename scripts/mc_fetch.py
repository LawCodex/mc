#!/usr/bin/env python3
"""Fetch Monegasque legislation in force from Legimonaco (legimonaco.mc).

The document list comes from the site's public search endpoint (/~~search/depot/_search,
the same Elasticsearch query its "Types de contenu" explorer issues); each current
version page is then downloaded as HTML and cached under _raw/mc/.
"""
import concurrent.futures as cf
import hashlib
import json
import os
import sys
import time

import requests

UA = "LawCodex/1.0 (+https://github.com/LawCodex)"
BASE = "https://legimonaco.mc"
RAW = os.path.abspath(os.environ.get("MC_RAW", os.path.join(os.path.dirname(__file__), "..", "..", "_raw", "mc")))
S = requests.Session()
S.headers["User-Agent"] = UA

MUST_NOT = [
    {"terms": {"processing": ["home"]}}, {"terms": {"trashed": ["true"]}},
    {"terms": {"excludeFromSearch": ["true"]}}, {"range": {"startDate": {"gt": "now"}}},
    {"range": {"endDate": {"lte": "now"}}},
]
FIELDS = ["path", "title", "type", "date", "tncNature", "number", "startDate", "endDate",
          "legislationAbrogated", "regulationAbrogated", "thematic", "contentId", "taiNature", "tai",
          "intoForceDate"]


def search(types):
    out, frm = [], 0
    while True:
        body = {"size": 500, "from": frm, "track_total_hits": True, "_source": FIELDS,
                "query": {"bool": {"must": [{"terms": {"type": types}}], "must_not": MUST_NOT}},
                "sort": [{"date": {"order": "asc"}}, {"number": {"order": "asc"}}]}
        r = S.post(BASE + "/~~search/depot/_search", json=body, timeout=120)
        r.raise_for_status()
        d = r.json()
        hits = d["hits"]["hits"]
        out += [h["_source"] for h in hits]
        frm += len(hits)
        print(types, frm, d["hits"]["total"]["value"], file=sys.stderr)
        if not hits or frm >= d["hits"]["total"]["value"]:
            return out
        time.sleep(1)


def get(url, tries=5):
    for i in range(tries):
        try:
            r = S.get(url, timeout=300)
            if r.status_code == 200:
                return r.content
            if r.status_code == 404:
                return None
            print("HTTP", r.status_code, url, file=sys.stderr)
        except requests.RequestException as e:
            print("ERR", e, url, file=sys.stderr)
        time.sleep(10 * (i + 1))
    print("FAILED", url, file=sys.stderr)
    return None


def cache_name(path):
    return hashlib.sha1(path.encode()).hexdigest() + ".html"


def fetch_one(it):
    f = os.path.join(RAW, "pages", cache_name(it["path"]))
    if os.path.exists(f):
        return
    c = get(BASE + it["path"] + "/")
    if c is not None:
        open(f, "wb").write(c)
    time.sleep(0.5)


def main():
    os.makedirs(os.path.join(RAW, "pages"), exist_ok=True)
    idx = os.path.join(RAW, "index.json")
    if not os.path.exists(idx):
        items = [{"path": "/constitution", "type": "constitution", "title": "Constitution de la Principauté"}]
        items += search(["tc"]) + search(["legislation"]) + search(["regulation"]) + search(["tai"])
        json.dump(items, open(idx, "w"), ensure_ascii=False, indent=0)
    items = json.load(open(idx))
    if not any(i["type"] == "tai" for i in items):  # index built before treaties were added
        items += search(["tai"])
        json.dump(items, open(idx, "w"), ensure_ascii=False, indent=0)
    items = [i for i in items if i.get("legislationAbrogated") != "yes" and i.get("regulationAbrogated") != "yes"]
    # codes, constitution and laws first
    items.sort(key=lambda i: {"constitution": 0, "tc": 1, "legislation": 2, "tai": 4}.get(i["type"], 3))
    print(len(items), "documents to fetch", file=sys.stderr)
    n = 0
    with cf.ThreadPoolExecutor(2) as ex:
        for _ in ex.map(fetch_one, items):
            n += 1
            if n % 200 == 0:
                print("fetched", n, file=sys.stderr, flush=True)


if __name__ == "__main__":
    main()

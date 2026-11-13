"""GitHub Actions 用：重查重点日期 -> 更新 data/fares_all.json -> 重建 index.html"""
import json, os, random, sys, threading
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import api

DATA = os.path.join(ROOT, "data", "fares_all.json")
HOL = [("2027-01-24", "2027-02-21"), ("2027-07-10", "2027-08-31")]

def win(d, r):
    for a, b in HOL:
        if a <= d and r <= b: return "hol"
    return "term"

rows = json.load(open(DATA))
have = {k for k, v in rows.items() if v.get("price")}
key = lambda v: v["price"]
ordered = sorted([v for v in rows.values() if v.get("price")], key=key)
pairs = []
for v in ordered:
    if win(v["dep"], v["ret"]) == "hol":
        pairs.append((v["dep"], v["ret"]))
for v in ordered[:30]:
    pairs.append((v["dep"], v["ret"]))
for v in ordered[:5]:
    d, r = date.fromisoformat(v["dep"]), date.fromisoformat(v["ret"])
    for dd in (-1, 1):
        pairs.append(((d + timedelta(days=dd)).isoformat(), (r + timedelta(days=dd)).isoformat()))
pairs = list(dict.fromkeys(pairs))[:56]
print(f"checking {len(pairs)} pairs", flush=True)

lock = threading.Lock(); ok = [0]

def work(p):
    r = api.search(*p)
    if not r.get("price"):
        return
    k = f"{p[0]}|{p[1]}"
    with lock:
        rows[k] = r
        ok[0] += 1

with ThreadPoolExecutor(max_workers=3) as ex:
    list(ex.map(work, pairs))

json.dump(rows, open(DATA, "w"), ensure_ascii=False, separators=(",", ":"))
print(f"updated {ok[0]}/{len(pairs)}", flush=True)
os.system(f'"{sys.executable}" "{os.path.join(HERE, "build.py")}"')

changed = ok[0] > 0
open(os.path.join(ROOT, ".changed"), "w").write("1" if changed else "0")
with open(os.environ.get("GITHUB_OUTPUT", os.devnull), "a") as f:
    f.write(f"changed={'true' if changed else 'false'}\n")

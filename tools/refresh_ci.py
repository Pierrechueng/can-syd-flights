"""CI 增量巡检：每次检查全网格的 1/7（按星期轮转）+ 假期全部 + 当前最便宜的 30 组。
       一周内把 2026-12-01 -> 2027-08-25 每天出发 × 10..15 天全部覆盖一遍。"""
import json, os, sys, threading
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import api

DATA = os.path.join(ROOT, "data", "fares_all.json")
START, END, STAYS = date(2026, 12, 1), date(2027, 8, 25), range(10, 16)
HOL = [("2027-01-24", "2027-02-21"), ("2027-07-10", "2027-08-31")]

def in_hol(d, r):
    return any(a <= d and r <= b for a, b in HOL)

# 全网格
grid = []
d = START
while d <= END:
    for s in STAYS:
        r = d + timedelta(days=s)
        if r <= date(2027, 8, 31):
            grid.append((d.isoformat(), r.isoformat()))
    d += timedelta(days=1)

slot = date.today().toordinal() % 7          # 今天负责第几片
pairs = [p for i, p in enumerate(grid) if i % 7 == slot]

rows = json.load(open(DATA))
if isinstance(rows, list):
    rows = {f"{v['dep']}|{v['ret']}": v for v in rows}
ordered = sorted([v for v in rows.values() if v.get("price")], key=lambda v: v["price"])
pairs += [(v["dep"], v["ret"]) for v in ordered if in_hol(v["dep"], v["ret"])]
pairs += [(v["dep"], v["ret"]) for v in ordered[:30]]
pairs = list(dict.fromkeys(pairs))
print(f"grid={len(grid)} slot={slot} checking={len(pairs)}", flush=True)

lock = threading.Lock(); ok = [0]

def work(p):
    r = api.search(*p)
    if not r.get("price"):
        return
    with lock:
        rows[f"{p[0]}|{p[1]}"] = r
        ok[0] += 1
        if ok[0] % 40 == 0:
            print(f"  {ok[0]} ok", flush=True)

with ThreadPoolExecutor(max_workers=4) as ex:
    list(ex.map(work, pairs))

json.dump(rows, open(DATA, "w"), ensure_ascii=False, separators=(",", ":"))
print(f"updated {ok[0]}/{len(pairs)}, total pairs {len(rows)}", flush=True)
os.system(f'"{sys.executable}" "{os.path.join(HERE, "build.py")}"')
with open(os.environ.get("GITHUB_OUTPUT", os.devnull), "a") as f:
    f.write(f"changed={'true' if ok[0] else 'false'}\n")

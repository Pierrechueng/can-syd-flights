import json, sys, threading, time, random
from datetime import date, timedelta
from concurrent.futures import ThreadPoolExecutor
from api import search

STAYS = [10, 11, 12, 13, 14, 15]
OUT = "fares_all.json"

def build():
    pairs = []
    d = date(2026, 12, 1)
    while d <= date(2027, 8, 25):
        for s in STAYS:
            r = d + timedelta(days=s)
            if r <= date(2027, 8, 31):
                pairs.append((d.isoformat(), r.isoformat()))
        d += timedelta(days=4)
    return pairs

def main():
    pairs = build()
    res = {}
    for f in ("fares2.json", "fares3.json", "fares_all.json"):
        try: res.update({k: v for k, v in json.load(open(f)).items() if v.get("price")})
        except Exception: pass
    todo = [p for p in pairs if f"{p[0]}|{p[1]}" not in res]
    print("total", len(pairs), "todo", len(todo), flush=True)
    lock = threading.Lock()
    done = [0]
    def work(p):
        time.sleep(random.uniform(0, .8))
        r = search(*p)
        with lock:
            if r.get("price"):
                res[f"{p[0]}|{p[1]}"] = r
            done[0] += 1
            if done[0] % 20 == 0:
                json.dump(res, open(OUT, "w"), ensure_ascii=False)
                print("progress", done[0], "/", len(todo), flush=True)
    with ThreadPoolExecutor(max_workers=4) as ex:
        list(ex.map(work, todo))
    json.dump(res, open(OUT, "w"), ensure_ascii=False)
    print("DONE", len(res), flush=True)

main()

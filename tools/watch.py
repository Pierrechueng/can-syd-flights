"""定时巡检：重查重点日期的价格，与已记录的最低价对比。"""
import json, os, threading, random
from datetime import datetime, date, timedelta
from concurrent.futures import ThreadPoolExecutor
import api, server

BASE = os.path.dirname(os.path.abspath(__file__))

def main():
    server.load_all()
    before = min((v["price"] for v in server.STATE["pairs"].values()), default=None)
    pairs = server.targets(limit=40)
    lock = threading.Lock()
    def work(p):
        random.uniform(0, .5)
        r = api.search(*p)
        with lock:
            if r.get("price"):
                n = server._norm(r)
                if n:
                    server.STATE["pairs"][f"{p[0]}|{p[1]}"] = n
    with ThreadPoolExecutor(max_workers=3) as ex:
        list(ex.map(work, pairs))
    server.save()
    ps = sorted(server.STATE["pairs"].values(), key=lambda v: v["price"])
    after = ps[0]["price"] if ps else None
    hol = [v for v in ps if server.in_holiday(v["dep"], v["ret"])]
    out = {
        "checked_at": datetime.now().isoformat(timespec="seconds"),
        "queries": len(pairs),
        "min_before": before, "min_now": after,
        "drop": (before - after) if (before and after) else 0,
        "best": ps[0] if ps else None,
        "best_holiday": hol[0] if hol else None,
    }
    json.dump(out, open(os.path.join(BASE, "last_watch.json"), "w"), ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1))

if __name__ == "__main__":
    main()

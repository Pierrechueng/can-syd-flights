#!/usr/bin/env python3
"""广州⇄悉尼 机票看板：本地服务 + 一键刷新。"""
import json, os, random, threading, time
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from datetime import datetime, date, timedelta
from concurrent.futures import ThreadPoolExecutor
import api

BASE = os.path.dirname(os.path.abspath(__file__))
STORE = os.path.join(BASE, "store.json")
SOURCES = ["fares_all.json"]

# 儿子放假日（可在页面上改）
HOLIDAYS = [("2027-01-24", "2027-02-21"), ("2027-07-10", "2027-08-31")]

LOCK = threading.Lock()
STATE = {"pairs": {}, "meta": {}, "job": None}


def _norm(v):
    if not v or not v.get("price"):
        return None
    return {"dep": v["dep"], "ret": v["ret"], "price": v["price"],
            "options": [{k: o.get(k) for k in ("price", "airlines", "stops", "minutes")}
                        for o in (v.get("options") or [])[:4]]}


_MTIME = [0]


def reload_if_changed():
    fp = os.path.join(BASE, "fares_all.json")
    try:
        m = os.path.getmtime(fp)
    except OSError:
        return
    if m <= _MTIME[0]:
        return
    _MTIME[0] = m
    try:
        d = json.load(open(fp))
    except Exception:
        return
    n = 0
    for k, v in d.items():
        x = _norm(v)
        if x and 10 <= (date.fromisoformat(x["ret"]) - date.fromisoformat(x["dep"])).days <= 15:
            STATE["pairs"][k] = x
            n += 1
    if n:
        STATE["meta"]["updated"] = datetime.now().isoformat(timespec="seconds")


def load_all():
    pairs = {}
    for f in SOURCES:
        p = os.path.join(BASE, f)
        if not os.path.exists(p):
            continue
        try:
            d = json.load(open(p))
        except Exception:
            continue
        for k, v in d.items():
            n = _norm(v)
            if n and 10 <= (date.fromisoformat(n["ret"]) - date.fromisoformat(n["dep"])).days <= 15:
                pairs[k] = n
    if os.path.exists(STORE):
        try:
            d = json.load(open(STORE))
            pairs.update(d.get("pairs") or {})
            STATE["meta"] = d.get("meta") or {}
        except Exception:
            pass
    STATE["pairs"] = pairs
    STATE["meta"].setdefault("history", [])


def save():
    tmp = STORE + ".tmp"
    json.dump({"pairs": STATE["pairs"], "meta": STATE["meta"]}, open(tmp, "w"), ensure_ascii=False)
    os.replace(tmp, STORE)


def in_holiday(dep, ret):
    return any(h0 <= dep and ret <= h1 for h0, h1 in HOLIDAYS)


def targets(limit=48):
    ps = list(STATE["pairs"].values())
    ps.sort(key=lambda v: v["price"])
    sel = {}

    def add(dep, ret):
        if len(sel) < limit:
            sel[f"{dep}|{ret}"] = (dep, ret)

    for v in ps:
        if in_holiday(v["dep"], v["ret"]):
            add(v["dep"], v["ret"])
    for v in ps[:24]:
        add(v["dep"], v["ret"])
    for v in ps[:5]:  # 最优解附近再挖一挖
        d0, r0 = date.fromisoformat(v["dep"]), date.fromisoformat(v["ret"])
        for dd in (-1, 1):
            for dr in (-1, 1):
                add((d0 + timedelta(days=dd)).isoformat(), (r0 + timedelta(days=dr)).isoformat())
    rest = [v for v in ps if f'{v["dep"]}|{v["ret"]}' not in sel]
    random.shuffle(rest)
    for v in rest[:4]:
        add(v["dep"], v["ret"])
    return list(sel.values())


def do_refresh():
    pairs = targets()
    job = {"running": True, "done": 0, "total": len(pairs), "started": datetime.now().isoformat(timespec="seconds"),
           "before": min((v["price"] for v in STATE["pairs"].values()), default=None)}
    with LOCK:
        STATE["job"] = job
    lock = threading.Lock()

    def work(p):
        r = api.search(*p)
        with lock:
            if r.get("price"):
                n = _norm(r)
                if n:
                    with LOCK:
                        old = STATE["pairs"].get(f"{p[0]}|{p[1]}")
                        n["seen"] = (old or {}).get("seen", []) + [{"price": n["price"],
                                    "at": datetime.now().isoformat(timespec="seconds")}][-5:]
                        n["first"] = (old or {}).get("first", n["price"])
                        STATE["pairs"][f"{p[0]}|{p[1]}"] = n
            job["done"] += 1

    try:
        with ThreadPoolExecutor(max_workers=3) as ex:
            list(ex.map(work, pairs))
    finally:
        with LOCK:
            save()
            mn = min((v["price"] for v in STATE["pairs"].values()), default=None)
            STATE["meta"]["updated"] = datetime.now().isoformat(timespec="seconds")
            STATE["meta"]["min"] = mn
            h = STATE["meta"].setdefault("history", [])
            h.append({"at": STATE["meta"]["updated"], "min": mn})
            STATE["meta"]["history"] = h[-40:]
            job["running"] = False
            job["after"] = mn
            STATE["job"] = job
            save()


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        b = body if isinstance(body, bytes) else str(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        p = self.path.split("?")[0]
        if p in ("/", "/index.html"):
            return self._send(200, open(os.path.join(BASE, "app.html"), "rb").read(),
                              "text/html; charset=utf-8")
        if p == "/api/data":
            reload_if_changed()
            rows = [v for v in STATE["pairs"].values()]
            rows.sort(key=lambda v: v["price"])
            return self._send(200, json.dumps({
                "rows": rows, "meta": STATE["meta"], "job": STATE["job"],
                "holidays": HOLIDAYS, "generated": datetime.now().isoformat(timespec="seconds")},
                ensure_ascii=False))
        if p == "/api/status":
            return self._send(200, json.dumps({"job": STATE["job"], "meta": STATE["meta"]},
                                              ensure_ascii=False))
        return self._send(404, "{}")

    def do_POST(self):
        if self.path.split("?")[0] == "/api/refresh":
            job = STATE.get("job") or {}
            if job.get("running"):
                return self._send(200, json.dumps({"ok": False, "reason": "running"}))
            threading.Thread(target=do_refresh, daemon=True).start()
            return self._send(200, json.dumps({"ok": True}))
        return self._send(404, "{}")


if __name__ == "__main__":
    load_all()
    port = int(os.environ.get("PORT", "8791"))
    srv = ThreadingHTTPServer(("127.0.0.1", port), H)
    print(f"http://127.0.0.1:{port}/", flush=True)
    srv.serve_forever()

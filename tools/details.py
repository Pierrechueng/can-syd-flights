"""完整行程解析：航段时刻/机场/转机等待/航班号 + 单程与往返取价。"""
import json, time, random
from lxml import html as LH
import api

def payload(url, tries=5):
    for i in range(tries):
        host = api.HOSTS[i % len(api.HOSTS)]
        base = url.split("?", 1)[1] if "?" in url else ""
        try:
            h = api._get(f"{host}?{base}")
            doc = LH.fromstring(h)
            sc = doc.xpath('//script[contains(@class,"ds:1")]')
            if not sc:
                time.sleep(1.2 + random.random()); continue
            js = sc[0].text_content()
            data = js.split("data:", 1)[1].rsplit(",", 1)[0]
            if "errorHasStatus" in data:
                time.sleep(1.5 + random.random() * 1.5); continue
            return json.loads(data)
        except Exception:
            time.sleep(1.2 + random.random())
    return None

def hhmm(t):
    if not t: return None
    return f"{t[0]:02d}:{t[1]:02d}"

def ymd(d):
    return f"{d[0]:04d}-{d[1]:02d}-{d[2]:02d}" if d else None

def seg_info(s):
    return {
        "flight": (s[22][0] + s[22][1]) if s[22] else None,
        "airline": (s[22][3] if s[22] and len(s[22]) > 3 else None),
        "from": s[3], "from_name": s[4], "to": s[6], "to_name": s[5],
        "dep": ymd(s[20]), "dep_t": hhmm(s[8]),
        "arr": ymd(s[21]), "arr_t": hhmm(s[10]),
        "min": s[11], "aircraft": s[17],
    }

def itinerary(fl):
    segs = [seg_info(s) for s in (fl[2] or [])]
    lay = []
    for i in range(len(segs) - 1):
        a, b = segs[i], segs[i + 1]
        lay.append({"at": b["from"], "at_name": b["from_name"], "min": b.get("min") and None})
    # 转机等待：下一段起飞 - 上一段落地
    for i in range(len(segs) - 1):
        a, b = segs[i], segs[i + 1]
        try:
            from datetime import datetime
            t1 = datetime.fromisoformat(f"{a['arr']}T{a['arr_t']}")
            t2 = datetime.fromisoformat(f"{b['dep']}T{b['dep_t']}")
            lay[i]["min"] = int((t2 - t1).total_seconds() // 60)
        except Exception:
            lay[i]["min"] = None
    return {
        "price": None, "stops": max(0, len(segs) - 1),
        "minutes": fl[9], "segs": segs, "layovers": lay,
        "dep": segs[0]["dep"] if segs else None, "dep_t": segs[0]["dep_t"] if segs else None,
        "arr": segs[-1]["arr"] if segs else None, "arr_t": segs[-1]["arr_t"] if segs else None,
        "from": segs[0]["from"] if segs else None, "to": segs[-1]["to"] if segs else None,
        "airlines": fl[1] or [],
    }

def _list(p, limit=6):
    if not p or not p[3] or not p[3][0]: return []
    out = []
    for k in p[3][0][:limit]:
        try:
            it = itinerary(k[0]); it["price"] = k[1][0][1]; out.append(it)
        except Exception:
            continue
    return out

def roundtrip(dep, ret, limit=4):
    p = payload(f"?tfs={api._tfs(dep, ret)}&hl=en&curr=CNY")
    return _list(p, limit)

def oneway(d, frm="CAN", to="SYD", limit=4):
    import base64
    from enc import flight_data, ld, vi
    info = ld(3, flight_data(d, frm, to)) + b"".join(vi(8, x) for x in api.PAX) + vi(9, 1) + vi(19, 2)
    p = payload(f"?tfs={base64.b64encode(info).decode()}&hl=en&curr=CNY")
    return _list(p, limit)

def full(dep, ret):
    rt = roundtrip(dep, ret, 3)
    out = oneway(dep, "CAN", "SYD", 3)
    back = oneway(ret, "SYD", "CAN", 3)
    return {"dep": dep, "ret": ret, "rt": rt, "out": out, "back": back}

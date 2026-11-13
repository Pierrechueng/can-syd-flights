"""Google Flights 抓取层：多域名轮换 + 重试 + 结构化解析。"""
import base64, json, subprocess, urllib.parse, random, time
from lxml import html as LH
from enc import varint, ld, vi, airport, flight_data, PAX

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36")
HOSTS = ["https://www.google.com.hk/travel/flights",
         "https://www.google.co.jp/travel/flights"]

def _tfs(dep, ret=None, frm="CAN", to="SYD", seat=1, pax=PAX):
    legs = [flight_data(dep, frm, to)]
    trip = 2
    if ret:
        legs.append(flight_data(ret, to, frm)); trip = 1
    info = b"".join(ld(3, x) for x in legs) + b"".join(vi(8, p) for p in pax) + vi(9, seat) + vi(19, trip)
    return base64.b64encode(info).decode()

def _get(url, timeout=45):
    return subprocess.run(["curl", "-sL", "--compressed", f"--max-time", str(timeout),
        "-H", f"user-agent: {UA}", "-H", "accept-language: en-US,en;q=0.9,zh-CN;q=0.8", url],
        capture_output=True, text=True).stdout

def _minutes(seg):
    try:
        d, a = seg[20], seg[21]
        from datetime import date
        t1 = (seg[8][0] or 0)*60 + (seg[8][1] if len(seg[8])>1 else 0)
        t2 = (seg[10][0] or 0)*60 + (seg[10][1] if len(seg[10])>1 else 0)
        d1 = date(*d); d2 = date(*a)
        diff = (d2-d1).days*1440 + t2 - t1
        return diff if diff > 0 else None
    except Exception:
        return None

def parse(html):
    doc = LH.fromstring(html)
    sc = doc.xpath('//script[contains(@class,"ds:1")]')
    if not sc: return None
    js = sc[0].text_content()
    if "data:" not in js: return None
    data = js.split("data:", 1)[1].rsplit(",", 1)[0]
    if "errorHasStatus" in data: return "ERR"
    p = json.loads(data)
    if p[3][0] is None: return []
    out = []
    for k in p[3][0]:
        try:
            fl = k[0]; price = k[1][0][1]
            segs = fl[2]
            carrier = [c for c in (fl[1] or [])]
            out.append({
                "price": price,
                "airlines": carrier,
                "stops": len(segs) - 1,
                "minutes": _minutes(segs[-1]) if segs else None,
                "legs": [[s[3], s[6]] for s in segs],
            })
        except Exception:
            continue
    return out

def search(dep, ret=None, tries=4, host=None, top=6):
    t = _tfs(dep, ret)
    err = None
    for i in range(tries):
        h = host or HOSTS[i % len(HOSTS)]
        q = urllib.parse.urlencode({"tfs": t, "hl": "en", "curr": "CNY", "gl": "US"})
        html = _get(f"{h}?{q}")
        try:
            r = parse(html)
        except Exception as e:
            r = None
        if r != "ERR" and r is not None:
            return {"dep": dep, "ret": ret, "price": r[0]["price"] if r else None,
                    "options": sorted(r, key=lambda x: x["price"])[:top]}
        err = "blocked"
        time.sleep(1.5 + i * 1.5)
    return {"dep": dep, "ret": ret, "price": None, "options": [], "err": err}

if __name__ == "__main__":
    import sys
    print(search("2026-12-07", "2027-01-21")["price"])

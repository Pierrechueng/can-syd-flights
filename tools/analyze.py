import json
from datetime import date
INC={"China Southern","Cathay Pacific","Singapore Airlines","China Eastern","Xiamen Airlines","Qantas","Air China",
"Sichuan Airlines","Hainan Airlines","Emirates","Qatar Airways","Thai Airways","Malaysia Airlines","Korean Air",
"Asiana Airlines","EVA Air","China Airlines","Hong Kong Airlines","Shenzhen Airlines","Juneyao Airlines","Shanghai Airlines",
"Beijing Capital Airlines","Air Macau","Vietnam Airlines","Philippine Airlines"}
BAG=360
HOL=[("2027-01-24","2027-02-21","寒假"),("2027-07-10","2027-08-31","暑假")]

def cost(price,airlines,pax=4):
    inc=any(a in INC for a in airlines)
    return price + (0 if inc else pax*2*BAG), inc

def window(dep,ret):
    for a,b,n in HOL:
        if a<=dep and ret<=b: return n
    return "学期中"

d=json.load(open("fares_all.json"))
rows=[]
for v in d.values():
    if not v.get("price"): continue
    o=v["options"][0]
    tot,inc=cost(v["price"],o.get("airlines",[]))
    best=tot; bestair=o.get("airlines",[]); bestinc=inc
    for alt in v.get("options",[]):
        t,i2=cost(alt["price"],alt.get("airlines",[]))
        if t<best: best,bestair,bestinc=t,alt.get("airlines",[]),i2
    nights=(date.fromisoformat(v["ret"])-date.fromisoformat(v["dep"])).days
    rows.append(dict(dep=v["dep"],ret=v["ret"],nights=nights,fare=v["price"],
                     total=best,air="、".join(bestair),inc=bestinc,win=window(v["dep"],v["ret"]),
                     per=best/4))
rows.sort(key=lambda r:(r["total"],r["dep"]))
print("priced pairs:",len(rows))
print("\n== 整体最便宜 10 ==")
for r in rows[:10]: print(f"{r['total']:>6} {r['dep']} {r['ret']} {r['nights']:>2}d {r['air'][:22]:<22} {r['win']}  fare={r['fare']}")
for w in ("寒假","暑假","学期中"):
    sub=[r for r in rows if r["win"]==w]
    if not sub: continue
    print(f"\n== {w} 最便宜 6（共 {len(sub)} 组）==")
    for r in sub[:6]: print(f"{r['total']:>6} {r['dep']} {r['ret']} {r['nights']:>2}d {r['air'][:22]:<22} fare={r['fare']} 人均={r['per']:,.0f}")
print("\n== 按月最低（含行李）==")
mm={}
for r in rows: mm.setdefault(r["dep"][:7],[]).append(r)
for m in sorted(mm):
    b=min(mm[m],key=lambda x:x["total"])
    print(f"{m}  {b['total']:>6}  {b['dep']}->{b['ret']} {b['nights']}d {b['air'][:20]}  ({len(mm[m])}组)")

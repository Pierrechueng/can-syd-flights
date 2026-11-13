import json, datetime
rows=[v for v in json.load(open("fares_all.json")).values() if v.get("price")]
rows.sort(key=lambda v: v["price"])
meta={"updated": datetime.datetime.now().isoformat(timespec="seconds"), "min": rows[0]["price"]}
html=open("app.html").read()
inject = "<script>window.__ROWS__=%s;window.__META__=%s;</script>\n" % (
    json.dumps(rows, ensure_ascii=False), json.dumps(meta, ensure_ascii=False))
html = html.replace("<script>\nconst INCLUDED", inject + "<script>\nconst INCLUDED", 1)
open("snapshot.html","w").write(html)
print("snapshot.html", len(html)//1024, "KB,", len(rows), "rows")

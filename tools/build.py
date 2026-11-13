"""把 data/fares_all.json 注入 app.html，生成可离线/可托管的 index.html"""
import json, os, datetime
HERE=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.dirname(HERE)
rows=[v for v in json.load(open(os.path.join(ROOT,"data","fares_all.json"))).values() if v.get("price")]
rows.sort(key=lambda v: v["price"])
meta={"updated": datetime.datetime.now().astimezone().isoformat(timespec="seconds"), "rows": len(rows)}
html=open(os.path.join(HERE,"app.html")).read()
inject="<script>window.__ROWS__=%s;window.__META__=%s;</script>\n" % (
    json.dumps(rows, ensure_ascii=False, separators=(",",":")), json.dumps(meta, ensure_ascii=False))
html=html.replace("<script>\nconst INCLUDED", inject+"<script>\nconst INCLUDED", 1)
open(os.path.join(ROOT,"index.html"),"w").write(html)
print("index.html", len(rows), "rows,", len(html)//1024, "KB")

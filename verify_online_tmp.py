# 临时脚本：验证线上 logic-notes.html 是否已包含一笔画新内容
import urllib.request, ssl, time

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

urls = {
    "root": "https://1780184306.github.io/xingce-notes/",
    "logic": "https://1780184306.github.io/xingce-notes/logic-notes.html",
    "all-in-one": "https://1780184306.github.io/xingce-notes/all-in-one.html",
}
marker = "两个条件缺一不可"

for attempt in range(1, 11):
    ok = True
    for name, url in urls.items():
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            resp = urllib.request.urlopen(req, timeout=60, context=ctx)
            body = resp.read()
            has = marker.encode("utf-8") in body
            print(f"attempt {attempt} [{name}] {resp.status} {len(body)//1024}KB marker={has}")
            if name == "logic" and not has:
                ok = False
        except Exception as e:
            print(f"attempt {attempt} [{name}] ERROR {e}")
            ok = False
    if ok:
        print("VERIFY_DONE")
        break
    time.sleep(30)

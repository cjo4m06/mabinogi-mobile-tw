#!/usr/bin/env python3
"""Nexon Peak（peak.nexon.com）抓取工具 —— NEXON 官方創作者專欄平台

全站約 2,300 篇，瑪奇 Mobile 佔 600+ 篇。是韓服情報最好抓的來源：
沒有 Cloudflare、有 JSON API、一次可以撈全部清單。

★ 為什麼重要：韓服 2025-08 ～ 2025-09 的文章 = 韓服 S0 時期 = 台服現在的版本。
   那個區間的文章對台服直接適用；2025-10 之後是 S1、2026-06 之後是 S2。

用法:
    python3 peak.py sync                    抓全站清單並快取（約 3MB，5 秒）
    python3 peak.py find <關鍵字> [起] [迄]  從快取搜尋標題／標籤，可限日期 YYYY-MM
    python3 peak.py mabi [起] [迄]           只列瑪奇 Mobile 的文章
    python3 peak.py read <id>               讀全文（韓文純文字，圖片標成 [圖片]）

範例:
    python3 peak.py sync
    python3 peak.py mabi 2025-08 2025-09     # ← 韓服 S0 時期，對台服最有用
    python3 peak.py find 어비스
    python3 peak.py read 63

API（自己要臨時查時直接用）:
    清單  https://api.streamlens.nexon.com/peak/post/list/recommend/0/6000?lang=ko
    單篇  https://api.streamlens.nexon.com/peak/post/{id}?lang=ko
    需要 header: Referer: https://peak.nexon.com/
    「recommend」是唯一可用的清單端點，latest/popular/all 都回 SYSTEM_ERROR。

注意:
  - 文章內文常把數值放在截圖裡，抓下來只會看到 [圖片]，這種要換來源或請使用者確認。
  - 標籤 tagList 可靠：마비노기모바일 / 모비노기 / 마비노기 모바일 三種都要一起比對。
  - 「피크 챌린지」開頭的是活動投稿，沒有攻略內容，可直接濾掉。
"""
import json, os, re, sys, html, subprocess, time

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "Chrome/131.0.0.0 Safari/537.36")
API = "https://api.streamlens.nexon.com/peak"
CACHE = os.path.expanduser("~/.cache/mabi/peak-index.json")
MM = re.compile(r'마비노기\s*모바일|모비노기|mabinogi\s*mobile', re.I)
CHALLENGE = re.compile(r'피크\s*챌린지|피크챌린지')


def curl(url):
    p = subprocess.run(["curl", "-sS", "-A", UA, "-H", "Referer: https://peak.nexon.com/",
                        "--max-time", "60", url], capture_output=True, text=True)
    return p.stdout


def sync():
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    raw = curl(f"{API}/post/list/recommend/0/6000?lang=ko")
    lst = json.loads(raw).get("list", [])
    slim = [{"id": p["id"], "date": (p.get("createdDate") or "")[:10], "title": p.get("title", ""),
             "tags": p.get("tagList") or [], "like": p.get("likeCount") or 0}
            for p in lst]
    json.dump(slim, open(CACHE, "w"), ensure_ascii=False)
    mm = [p for p in slim if is_mabi(p)]
    print(f"已快取 {len(slim)} 篇 → {CACHE}")
    print(f"其中瑪奇 Mobile {len(mm)} 篇（含活動投稿 {sum(1 for p in mm if CHALLENGE.search(p['title']))} 篇）")
    return slim


def load():
    if not os.path.exists(CACHE):
        return sync()
    return json.load(open(CACHE))


def is_mabi(p):
    return bool(MM.search(p["title"] + " " + " ".join(p["tags"])))


def show(rows):
    for p in sorted(rows, key=lambda x: x["date"]):
        era = ("韓S0" if p["date"] <= "2025-09-30" else
               "韓S1" if p["date"] <= "2026-05-31" else "韓S2")
        print(f'{p["id"]:>5} {p["date"]} [{era}] ♥{p["like"]:<3} {p["title"][:78]}')
    print(f"\n共 {len(rows)} 篇")


def read(pid):
    d = json.loads(curl(f"{API}/post/{pid}?lang=ko"))["data"]
    c = d.get("blogContent") or ""
    c = re.sub(r'<img[^>]*>', '\n[圖片]\n', c)
    c = re.sub(r'</(p|div|li|tr|h[1-6]|blockquote)>', '\n', c)
    c = html.unescape(re.sub(r'<[^>]+>', '', c))
    c = re.sub(r'[ \t]+', ' ', c)
    c = re.sub(r'\n\s*\n+', '\n', c)
    print(f'== ID {d["id"]} | {d["createdDate"][:10]} | {d["title"]}')
    print(c.strip())


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(0)
    cmd = sys.argv[1]
    if cmd == "sync":
        sync()
    elif cmd == "read":
        read(sys.argv[2])
    elif cmd in ("find", "mabi"):
        rows = load()
        if cmd == "find":
            kw = sys.argv[2]
            rows = [p for p in rows if kw in p["title"] or kw in " ".join(p["tags"])]
            rng = sys.argv[3:5]
        else:
            rows = [p for p in rows if is_mabi(p) and not CHALLENGE.search(p["title"])]
            rng = sys.argv[2:4]
        if len(rng) >= 1:
            rows = [p for p in rows if p["date"] >= rng[0]]
        if len(rng) >= 2:
            rows = [p for p in rows if p["date"][:7] <= rng[1]]
        show(rows)
    else:
        print(__doc__)

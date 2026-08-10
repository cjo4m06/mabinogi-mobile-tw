#!/usr/bin/env python3
"""巴哈姆特《瑪奇 Mobile》哈啦板抓取工具（台服社群第一手來源）

板號 bsn=32564 是台服瑪奇 Mobile。不要用其他 bsn（32227 是 PC 版瑪奇）。

用法:
    python3 baha.py list [頁數]          列出文章（snA / GP / 人氣 / 分類 / 標題）
    python3 baha.py find <關鍵字> [頁數]  在標題中搜尋（板內搜尋功能壞掉，只能自己撈列表過濾）
    python3 baha.py read <snA> [頁數]     讀文章內文＋回文

範例:
    python3 baha.py list 10
    python3 baha.py find 符文 15
    python3 baha.py read 756 3

注意:
  - 必須帶桌面版 User-Agent，否則 403。
  - 板內搜尋 B.php?qt=2&q= 會回傳整個板的列表、忽略關鍵字，所以用 find 自己過濾。
  - 圖片內容抓不到（會標成 [IMG url]）。攻略常把關鍵數值放在圖裡，遇到就要換來源。
"""
import re, html, sys, subprocess, time

BSN = 32564
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")


def get(url, min_len=1000):
    out = ""
    for _ in range(3):
        p = subprocess.run(["curl", "-sS", "--compressed", "-A", UA, "--max-time", "30", url],
                           capture_output=True, text=True)
        out = p.stdout
        if p.returncode == 0 and len(out) > min_len:
            return out
        time.sleep(1)
    return out


def strip_html(s):
    s = re.sub(r'<(br|/p|/div|/tr|/li|/h\d)\s*/?>', '\n', s, flags=re.I)
    s = re.sub(r'</td>', ' | ', s, flags=re.I)
    s = re.sub(r'<img[^>]*data-src="([^"]+)"[^>]*>', r'[IMG \1]', s)
    s = re.sub(r'<img[^>]*src="([^"]+)"[^>]*>', r'[IMG \1]', s)
    s = re.sub(r'<[^>]+>', '', s)
    s = html.unescape(s)
    s = re.sub(r'\n{3,}', '\n\n', s)
    return re.sub(r'[ \t]{2,}', ' ', s).strip()


def list_board(pages=8):
    """回傳 [(snA, gp, hits, category, title), ...]"""
    rows = []
    seen = set()
    for pg in range(1, pages + 1):
        t = get(f"https://forum.gamer.com.tw/B.php?bsn={BSN}&page={pg}")
        # 兩種版面：表格列 與 縮圖列，都抓
        for m in re.finditer(
                r'href="C\.php\?bsn=%d&snA=(\d+)[^"]*"[^>]*class="b-list__main__title[^"]*"[^>]*>([^<]+)<' % BSN, t):
            sn, title = m.group(1), html.unescape(m.group(2)).strip()
            if sn not in seen:
                seen.add(sn); rows.append((sn, "", "", "", title))
        for m in re.finditer(
                r'<p[^>]*href="C\.php\?bsn=%d&snA=(\d+)[^"]*"[^>]*class="b-list__main__title">([^<]+)</p>' % BSN, t):
            sn, title = m.group(1), html.unescape(m.group(2)).strip()
            if sn not in seen:
                seen.add(sn); rows.append((sn, "", "", "", title))
        # 補齊 GP / 人氣 / 分類（表格版面才有）
        for blk in re.split(r'<tr class="b-list__row', t)[1:]:
            m = re.search(r'snA=(\d+)', blk)
            if not m:
                continue
            sn = m.group(1)
            gp = (re.search(r'b-list__summary__gp[^>]*>(\d+)<', blk) or [None, ""])[1]
            hit = (re.search(r'b-list__count__number[^>]*><span>([\d,]+)</span>', blk) or [None, ""])[1]
            cat = (re.search(r'b-list__summary__sort[^>]*>([^<]+)<', blk) or [None, ""])[1]
            rows = [(s, gp if s == sn else g, hit if s == sn else h,
                     cat.strip() if s == sn else c, ti) for s, g, h, c, ti in rows]
        time.sleep(0.3)
    return rows


def read_thread(sn, pages=2):
    out = []
    for pg in range(1, pages + 1):
        url = f"https://forum.gamer.com.tw/C.php?bsn={BSN}&snA={sn}" + (f"&page={pg}" if pg > 1 else "")
        t = get(url)
        if not t:
            break
        bodies = re.findall(r'class="c-article__content"[^>]*>(.*?)</article>', t, re.S)
        if not bodies:
            break
        for i, b in enumerate(bodies):
            txt = strip_html(b)
            if txt:
                out.append(f"\n----- [p{pg}#{i}] -----\n{txt}")
        time.sleep(0.3)
    return "\n".join(out)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(0)
    cmd = sys.argv[1]
    if cmd == "list":
        for sn, gp, hit, cat, ti in list_board(int(sys.argv[2]) if len(sys.argv) > 2 else 8):
            print(f"{sn:>6} GP:{gp:<5} {hit:<8} {cat:<8} {ti}")
    elif cmd == "find":
        kw = sys.argv[2]
        pages = int(sys.argv[3]) if len(sys.argv) > 3 else 15
        for sn, gp, hit, cat, ti in list_board(pages):
            if kw in ti:
                print(f"{sn:>6} GP:{gp:<5} {hit:<8} {cat:<8} {ti}")
    elif cmd == "read":
        print(read_thread(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 2))
    else:
        print(__doc__)

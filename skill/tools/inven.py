#!/usr/bin/env python3
"""韓服 Inven 資料庫（mabimo.inven.co.kr）抓取工具

用途：符文與技能的**精確效果與數值**。韓服官方資料庫等級，數值最可靠。
⚠ 但它是韓服**最新賽季**的資料，抓回來的東西一定要先過 verify.py 篩過。

用法:
    python3 inven.py runes [部位]     符文資料庫（部位: 무기/방어구/엠블럼/장신구，省略=全部）
    python3 inven.py skills           全職業技能＋技能標籤＋對應符文
    python3 inven.py enchant          附魔捲軸
    python3 inven.py unique           獨特（유니크）裝備

輸出到 stdout，自己重導向存檔：
    python3 inven.py skills > /tmp/skills.txt

網址（要手動查時直接開）:
    符文  https://mabimo.inven.co.kr/dataninfo/rune/
    技能  https://mabimo.inven.co.kr/db/skill/?class=<職業編號>
    附魔  https://mabimo.inven.co.kr/db/enchant
    獨特  https://mabimo.inven.co.kr/db/unique

⚠ Inven 的符文卡片會標「시즌1」「시즌2」，那是**韓服賽季**，
   標了 시즌1 以上的台服一定沒有；沒標的也未必有，還是要跑 verify.py。
"""
import re, html, subprocess, sys, time

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "Chrome/131.0.0.0 Safari/537.36")


def get(u, min_len=5000):
    for _ in range(3):
        p = subprocess.run(["curl", "-sS", "--compressed", "-L", "-A", UA, "--max-time", "40", u],
                           capture_output=True, text=True)
        if p.returncode == 0 and len(p.stdout) > min_len:
            return p.stdout
        time.sleep(1)
    return ""


def clean(s):
    s = re.sub(r'<br\s*/?>', ' / ', s, flags=re.I)
    s = re.sub(r'<[^>]+>', ' ', s)
    return re.sub(r'\s+', ' ', html.unescape(s).replace('\xa0', ' ')).strip()


def runes(part=None):
    t = get("https://mabimo.inven.co.kr/dataninfo/rune/")
    for c in re.split(r'<div class="card_area"', t)[1:]:
        txt = clean(c.split('</section>')[0])
        if not txt:
            continue
        if part and part not in txt[:60]:
            continue
        season = "시즌1+" if re.search(r'시즌\s*[1-9]', txt[:60]) else "시즌0?"
        print(f"[{season}] {txt[:400]}")


def skills():
    base = get("https://mabimo.inven.co.kr/db/skill/")
    labels = {m.group(1): clean(m.group(2))
              for m in re.finditer(r'href="\?class=(\d+)"[^>]*>(.*?)</a>', base, re.S)}
    tags = set()
    for c in sorted(labels, key=int):
        h = get(f"https://mabimo.inven.co.kr/db/skill/?class={c}")
        cards = re.split(r'<div class="card_area">', h)[1:]
        print(f"\n########## {labels[c]} (class={c}) — {len(cards)} 技能 ##########")
        for card in cards:
            slot = re.search(r'<span class="type_icon[^"]*">(.*?)</span>', card)
            name = re.search(r'name_text">.*?<a [^>]*>(.*?)</a>', card, re.S)
            tg = re.findall(r'<span>#(.*?)</span>', card)
            desc = re.search(r'<div class="skill_desc">(.*?)</div>', card, re.S)
            rn = re.findall(r'<div class="rune_desc">\s*<h3>(.*?)</h3>\s*<p>(.*?)</p>', card, re.S)
            tags.update(clean(x) for x in tg)
            print(f"\n[{clean(slot.group(1)) if slot else '?'}] "
                  f"{clean(name.group(1)) if name else '?'}  #{' #'.join(clean(x) for x in tg)}")
            if desc:
                print(f"  說明: {clean(desc.group(1))}")
            for a, b in rn:
                print(f"  ★符文「{clean(a)}」: {clean(b)}")
        time.sleep(0.4)
    print(f"\n\n########## 全部技能標籤 ##########\n{sorted(tags)}")


def simple(url, title):
    print(f"########## {title} ##########")
    for card in re.split(r'<div class="card_area">', get(url))[1:]:
        t = clean(card.split('</section>')[0])
        if t:
            print("- " + t[:600])


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        print(__doc__)
    elif a[0] == "runes":
        runes(a[1] if len(a) > 1 else None)
    elif a[0] == "skills":
        skills()
    elif a[0] == "enchant":
        simple("https://mabimo.inven.co.kr/db/enchant", "인챈트 附魔捲軸")
    elif a[0] == "unique":
        simple("https://mabimo.inven.co.kr/db/unique", "유니크 獨特裝備")
    else:
        print(__doc__)

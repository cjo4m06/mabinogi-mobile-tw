#!/usr/bin/env python3
"""★★ 台服／韓服辨別器 —— 更新資料時最重要的一支

從韓服來源（Inven、Nexon Peak、나무위키、韓國部落格）抄回來的東西，
**有很高比例是 S1／S2 內容，台服沒有**。憑印象判斷一定會出錯。
這支工具把判斷變成查表。

用法:
    python3 verify.py <名詞> [名詞...]      判斷該名詞在台服的狀態
    python3 verify.py --file <檔案>          批次檢查（每行一個名詞）
    python3 verify.py --scan <檔案>          掃描檔案內所有韓文詞並逐一判定

範例:
    python3 verify.py 평원 방랑자 현란함 매 검무
    python3 verify.py --scan /tmp/從韓服抓回來的筆記.md

判定結果:
    🚫 台服未開放   → 明列在 references/04 §6 或 references/09 的封鎖清單，**絕對不能寫進正文**
    ✅ 台服有       → 出現在 data/符文-*-韓文原表.md（這份表已核對過與台服 S0 高度吻合）
    ⚙ 是技能不是符文 → 出現在 data/技能與標籤-全職業.md，別把技能名當符文名
    ❓ 查無         → 台服符文池沒有 ⇒ **預設當成韓服 S1+，不要寫進正文**

⚠ 「查無」不等於「台服沒有」，但**預設就是不要寫**。
   真的需要那條資訊時，去官方遊戲指南／更新日誌／巴哈找台服證據，找不到就不寫。

★ 台服後來開放了怎麼辦（改版時最常遇到）:
   在任何 references/*.md 加一行 HTML 註解，判定就會翻成「✅ 台服有」並顯示你寫的依據:

       <!-- UNBLOCKED: 잊힌 시대 | 台服 2026-08-05 開放深淵地獄1，可從深淵許願壺取得 -->

   為什麼需要這個: 封鎖清單是從標記往後硬抓 4000 字，
   而「這顆已經開放了」的更正說明本身就得提到那個韓文名，
   不另外標記的話會被自己的更正文字判成未開放。
   ⇒ 從封鎖清單刪掉名字**還不夠**，要補一行 UNBLOCKED 才算數。
"""
import os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

RUNE_TABLES = [f"data/符文-{p}-韓文原表.md" for p in ("武器", "防具", "徽章", "飾品-各職業")]
SKILL_TABLE = "data/技能與標籤-全職業.md"
BLOCK_SRC = [("references/04-各職業符文配置.md", "## 6. 台服未開放的符文"),
             ("references/09-賽季台韓差異與長期規劃.md", "台服 S0 **沒有**的韓服符文")]

# 台服後來開放的東西：在任何 references/*.md 寫一行
#     <!-- UNBLOCKED: 韓文名 | 何時開放／依據 -->
# 就會覆蓋封鎖清單的判定。
# 需要這個機制的原因：封鎖區塊是從標記往後硬抓 4000 字，
# 而「這顆已經開放了」的更正說明本身就得提到那個韓文名，
# 不另外標記的話會被自己的更正文字判成未開放。
UNBLOCK_RE = re.compile(r"<!--\s*UNBLOCKED:\s*([^|>]+?)\s*(?:\|([^>]*?))?-->")


def read(rel):
    p = os.path.join(ROOT, rel)
    return open(p, encoding="utf-8").read() if os.path.exists(p) else ""


def load():
    pool = {}
    for rel in RUNE_TABLES:
        # 去掉檔頭警語（裡面故意列了未開放符文的名字，會造成誤判）
        body = read(rel)
        body = body.split("```", 1)[-1] if "```" in body else body
        pool[rel.split("-")[1]] = body
    blocked = ""
    for rel, marker in BLOCK_SRC:
        t = read(rel)
        if marker in t:
            blocked += t.split(marker, 1)[1][:4000]
    unblocked = {}
    refs = os.path.join(ROOT, "references")
    for fn in sorted(os.listdir(refs)) if os.path.isdir(refs) else []:
        if not fn.endswith(".md"):
            continue
        for m in UNBLOCK_RE.finditer(read(os.path.join("references", fn))):
            unblocked[m.group(1).strip()] = (m.group(2) or "").strip() or "已解除封鎖"
    return pool, read(SKILL_TABLE), blocked, unblocked


def judge(term, pool, skills, blocked, unblocked=None):
    term = term.strip()
    if not term:
        return None
    unblocked = unblocked or {}
    where = [k for k, v in pool.items() if term in v]
    if term in unblocked:
        return "✅ 台服有", unblocked[term]
    if term in blocked:
        return "🚫 台服未開放", "明列於封鎖清單，不可寫進正文"
    if where:
        return "✅ 台服有", "符文表：" + "／".join(where)
    if term in skills:
        return "⚙ 是技能不是符文", "出現在技能與標籤表"
    return "❓ 查無", "預設當韓服 S1+，不要寫進正文"


def main():
    pool, skills, blocked, unblocked = load()
    args = sys.argv[1:]
    if not args:
        print(__doc__); return
    terms = []
    if args[0] == "--file":
        terms = [l.strip() for l in open(args[1], encoding="utf-8") if l.strip()]
    elif args[0] == "--scan":
        t = open(args[1], encoding="utf-8").read()
        terms = sorted({m.group(1).strip() for m in
                        re.finditer(r'[（(「『]([가-힣][가-힣\s]{1,12})[）)」』]', t)})
        terms += sorted({m.group(0) for m in re.finditer(r'[가-힣]{2,}(?:\s[가-힣]{2,})?', t)} - set(terms))
        terms = terms[:200]
    else:
        # 允許用空白分隔的多字詞：先整串試，失敗再逐字
        joined = " ".join(args)
        terms = [joined] if judge(joined, pool, skills, blocked, unblocked)[0] != "❓ 查無" else args
    width = max((len(t) for t in terms), default=10)
    counts = {}
    for t in terms:
        r = judge(t, pool, skills, blocked, unblocked)
        if not r:
            continue
        verdict, why = r
        counts[verdict] = counts.get(verdict, 0) + 1
        print(f"{t:<{width+2}} {verdict:<14} {why}")
    if len(terms) > 3:
        print("\n" + "  ".join(f"{k}×{v}" for k, v in sorted(counts.items())))


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""树状思维导图生成器（中心节点 → 向右逐级延伸，贝塞尔连线）。

用法：
  python mind_svg.py apply <笔记.html> <trees.json>   # 按锚点插入
  python mind_svg.py preview <trees.json> <out.html>  # 只生成预览页，不改动笔记

trees.json 格式（数组，每项一棵树）：
  [{
     "anchor": "<h2 class=\"section-title\"><span class=\"num\">1</span>题型识别",   # 插入锚点：该 h2 起始片段
     "title": "中心理解题·题型识别思维导图",
     "root": ["中心理解题", "题型识别 · 先看问法", [
        ["问法特征", null, [["“主要意思是”", null, []], ...]],
        ...
     ]]
  }]
"""
import io
import json
import sys
import html as _html

MARK = "<!-- 树状思维导图 -->"

PALETTE = [
    ("#b5563f", "#f6e3dc"),
    ("#2f6f8f", "#dfeef5"),
    ("#7a5ea8", "#ece5f6"),
    ("#3f7d4f", "#e2f0e6"),
    ("#a8791f", "#f6ecd6"),
]
ROOT_FILL, ROOT_STROKE, BG = "#b5563f", "#8f3f2c", "#fbf7f1"
INK = "#3f3a36"
ROW_H, COL_GAP, PAD_X, PAD = 34, 58, 13, 22


def esc(s):
    return _html.escape(str(s), quote=False)


def text_w(s, fs):
    return sum(fs * (0.62 if ord(c) < 128 else 1.0) for c in str(s))


class N(object):
    def __init__(self, spec, depth):
        label = spec[0]
        sub = spec[1] if len(spec) > 1 else None
        kids = spec[2] if len(spec) > 2 else []
        self.label, self.sub, self.depth = label, sub, depth
        # sub 支持 \n 多行（对应 ProcessOn 导图里类目节点的多行特征说明）
        self.lines = [label] + (sub.split("\n") if sub else [])
        self.fs = 17 if depth == 0 else (13.5 if depth == 1 else 12.5)
        lh = 26 if depth == 0 else 20
        self.w = max(text_w(t, self.fs) for t in self.lines) + PAD_X * 2
        self.h = lh * len(self.lines) + 12
        self.lh = lh
        self.children = [N(c, depth + 1) for c in kids]


def layout(n, st):
    if not n.children:
        n.y = st["leaf"] * ROW_H
        st["leaf"] += 1
    else:
        for c in n.children:
            layout(c, st)
        n.y = (n.children[0].y + n.children[-1].y) / 2.0
    st["maxw"][n.depth] = max(st["maxw"].get(n.depth, 0), n.w)
    st["maxy"] = max(st["maxy"], n.y + n.h / 2)
    st["miny"] = min(st["miny"], n.y - n.h / 2)


def draw(n, out, fam):
    x, y, w, h = n.x, n.y - n.h / 2, n.w, n.h
    if n.depth == 0:
        fill, stroke, tcol, rx, col = ROOT_FILL, ROOT_STROKE, "#ffffff", 10, ROOT_FILL
    elif n.depth == 1:
        col, soft = PALETTE[fam % len(PALETTE)]
        fill, stroke, tcol, rx = soft, col, col, 8
    else:
        fill = stroke = tcol = None
        rx, col = 0, "#c9beb2"

    if fill:
        out.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="%d" fill="%s"/>'
                   % (x, y, w, h, rx, fill))
        out.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="%d" fill="none" '
                   'stroke="%s" stroke-width="%.1f" stroke-opacity="%.2f"/>'
                   % (x, y, w, h, rx, stroke, 1.6 if n.depth == 0 else 1.1, 1 if n.depth == 0 else .55))

    total = n.lh * len(n.lines)
    ty = n.y - total / 2 + n.lh / 2 + 5
    for i, t in enumerate(n.lines):
        bold = "700" if (n.depth <= 1 or i == 0) else "500"
        size = n.fs if i == 0 else n.fs - 2
        out.append('<text x="%.1f" y="%.1f" fill="%s" font-size="%s" font-weight="%s">%s</text>'
                   % (x + PAD_X, ty + i * n.lh, tcol or INK, size, bold, esc(t)))

    for i, c in enumerate(n.children):
        cf = fam if n.depth >= 1 else i
        if n.depth == 0:
            s, sw, op = ROOT_FILL, 2.2, 0.90
        elif n.depth == 1:
            s, sw, op = PALETTE[fam % len(PALETTE)][0], 1.6, 0.75
        else:
            s, sw, op = "#c9beb2", 1.2, 0.9
        x1, y1, x2, y2 = x + w, n.y, c.x, c.y
        mx = (x1 + x2) / 2.0
        out.append('<path d="M%.1f %.1f C%.1f %.1f %.1f %.1f %.1f %.1f" fill="none" stroke="%s" '
                   'stroke-width="%.1f" stroke-opacity="%.2f" stroke-linecap="round"/>'
                   % (x1, y1, mx, y1, mx, y2, x2, y2, s, sw, op))
        draw(c, out, cf)


def snippet(spec, title):
    root = N(spec, 0)
    st = {"leaf": 0, "maxw": {}, "maxy": 0, "miny": 0}
    layout(root, st)
    off = PAD - st["miny"]  # 整体下移，保证顶部内容与画布上边缘留出 PAD
    def sety(n):
        n.y += off
        for c in n.children:
            sety(c)
    sety(root)
    colx, acc = {}, 0
    for d in sorted(st["maxw"]):
        colx[d] = acc
        acc += st["maxw"][d] + COL_GAP

    def setx(n):
        n.x = colx[n.depth] + PAD
        for c in n.children:
            setx(c)
    setx(root)
    out = []
    draw(root, out, 0)
    W = acc - COL_GAP + PAD * 2
    H = st["maxy"] + off + PAD
    return (MARK + '\n<div class="mm-tree">\n<svg viewBox="0 0 %.0f %.0f" width="%.0f" height="%.0f" '
            'role="img" aria-label="%s" style="font-family:\'Microsoft YaHei\',\'PingFang SC\',sans-serif;'
            'display:block">\n<rect x="0" y="0" width="%.0f" height="%.0f" rx="14" fill="%s"/>\n%s\n</svg>\n</div>'
            % (W, H, W, H, esc(title), W, H, BG, "\n".join(out)))


def apply(path, trees):
    src = io.open(path, encoding="utf-8").read()
    lines = src.split("\n")
    done, skip, fail = [], [], []
    for t in trees:
        anchor, idx = t["anchor"], None
        for i, ln in enumerate(lines):
            if anchor in ln:
                idx = i
                break
        if idx is None:
            fail.append(anchor[:40])
            continue
        if MARK in lines[idx + 1] or MARK in lines[idx + 2]:
            skip.append(t["title"])
            continue
        lines.insert(idx + 1, snippet(t["root"], t["title"]))
        done.append(t["title"])
    io.open(path, "w", encoding="utf-8", newline="\n").write("\n".join(lines))
    print("inserted=%d skipped=%d notfound=%d" % (len(done), len(skip), len(fail)))
    for d in done:
        print("  +", d)
    for s in skip:
        print("  =", s)
    for f in fail:
        print("  ! 锚点未找到:", f)
    return 0 if not fail else 1


def preview(trees, outp):
    body = "".join(snippet(t["root"], t["title"]) for t in trees)
    io.open(outp, "w", encoding="utf-8").write(
        '<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1"><title>预览</title>'
        '<style>body{margin:0;padding:24px;background:#f8fafc;font-family:"Microsoft YaHei",sans-serif}'
        '.mm-tree{margin:1.5rem 0;overflow-x:auto;-webkit-overflow-scrolling:touch;padding-bottom:.4rem;max-width:980px}'
        '.mm-tree svg{width:100%;height:auto;max-width:860px}'
        '@media (max-width:760px){.mm-tree svg{width:auto;max-width:none}}</style></head><body>'
        + body + "</body></html>")
    print("written", outp)


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "apply":
        sys.exit(apply(sys.argv[2], json.load(io.open(sys.argv[3], encoding="utf-8"))))
    elif cmd == "preview":
        preview(json.load(io.open(sys.argv[2], encoding="utf-8")), sys.argv[3])
    else:
        print(__doc__)

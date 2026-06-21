#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一选项图尺寸
================
把同一道题的若干选项配图统一成"完全相同的尺寸"——以该组里【最大的宽】和
【最大的高】为准组成画布；原图贴到画布的指定位置，不足的部分用【透明 alpha
通道】填充。输出为 PNG（只有 PNG 能保存透明通道，JPG 不行）。

例：A=50x50、B=25x50  ->  画布统一为 50x50，B 右侧缺的 25 像素补透明。

两种用法
--------
1) 处理整个目录（按文件名 "题号-选项" 自动分组，如 13-a.png / 13-b.png ...）：
       python3 统一选项图尺寸.py 模拟卷2题目配图

2) 手动指定一组图（把传入的这几张当成同一组一起统一）：
       python3 统一选项图尺寸.py 1-a.png 1-b.png 1-c.png 1-d.png

常用参数
--------
  --out 目录      输出目录（默认：在输入目录下新建 "统一尺寸输出/"，不动原图）
  --align 位置    原图在画布里的对齐位置，默认 top-left（左上角，右/下补透明）。
                  可选：top-left / top-center / top-right / center-left / center /
                        center-right / bottom-left / bottom-center / bottom-right
  --inplace       直接覆盖原图（谨慎！会把原图替换成统一尺寸后的 PNG）
"""

import argparse
import collections
import glob
import os
import sys

try:
    from PIL import Image
except ImportError:
    sys.exit("缺少 Pillow 库，请先安装：  pip3 install Pillow")


# 支持读取的输入格式
INPUT_EXTS = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif")

# 九宫格对齐方式 -> (水平, 垂直)
ALIGN = {
    "top-left":      ("left",   "top"),
    "top-center":    ("center", "top"),
    "top-right":     ("right",  "top"),
    "center-left":   ("left",   "center"),
    "center":        ("center", "center"),
    "center-right":  ("right",  "center"),
    "bottom-left":   ("left",   "bottom"),
    "bottom-center": ("center", "bottom"),
    "bottom-right":  ("right",  "bottom"),
}


def offset(canvas_w, canvas_h, img_w, img_h, align):
    """计算原图贴到画布上的左上角坐标 (dx, dy)。"""
    halign, valign = ALIGN[align]
    dx = {"left": 0, "center": (canvas_w - img_w) // 2, "right": canvas_w - img_w}[halign]
    dy = {"top": 0,  "center": (canvas_h - img_h) // 2, "bottom": canvas_h - img_h}[valign]
    return dx, dy


def unify_group(group_name, paths, out_dir, align, inplace):
    """把一组图统一到相同尺寸。返回 (统一宽, 统一高)。"""
    # 读图并统一转 RGBA（保证有 alpha 通道；原图本身像素全不透明）
    items = []
    for p in paths:
        try:
            im = Image.open(p).convert("RGBA")
        except Exception as e:
            print(f"    跳过无法读取的文件 {os.path.basename(p)}：{e}")
            continue
        items.append((p, im))

    if not items:
        return None

    canvas_w = max(im.width for _, im in items)
    canvas_h = max(im.height for _, im in items)

    print(f"  组「{group_name}」：共 {len(items)} 张  ->  统一为 {canvas_w}x{canvas_h}")

    for p, im in items:
        canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))  # 全透明画布
        dx, dy = offset(canvas_w, canvas_h, im.width, im.height, align)
        canvas.paste(im, (dx, dy))  # RGBA 原图直接贴上，其余区域保持透明

        stem = os.path.splitext(os.path.basename(p))[0]
        if inplace:
            out_path = os.path.splitext(p)[0] + ".png"
        else:
            out_path = os.path.join(out_dir, stem + ".png")
        canvas.save(out_path)

        # 报告每张图补了多少透明边
        pad_r = canvas_w - im.width - dx
        pad_b = canvas_h - im.height - dy
        note = ""
        if (im.width, im.height) != (canvas_w, canvas_h):
            bits = []
            if dx:    bits.append(f"左{dx}")
            if pad_r: bits.append(f"右{pad_r}")
            if dy:    bits.append(f"上{dy}")
            if pad_b: bits.append(f"下{pad_b}")
            note = "  补透明 " + " ".join(bits)
        print(f"      {os.path.basename(p):<16} {im.width}x{im.height} -> {canvas_w}x{canvas_h}{note}")

    return canvas_w, canvas_h


def group_directory(directory):
    """扫描目录，按 '题号-选项' 命名分组（取最后一个 '-' 前的部分作为组名）。"""
    files = []
    for ext in INPUT_EXTS:
        files += glob.glob(os.path.join(directory, "*" + ext))
        files += glob.glob(os.path.join(directory, "*" + ext.upper()))
    files = sorted(set(files))

    groups = collections.OrderedDict()
    for f in files:
        stem = os.path.splitext(os.path.basename(f))[0]
        key = stem.rsplit("-", 1)[0] if "-" in stem else stem
        groups.setdefault(key, []).append(f)
    return groups


def natural_key(s):
    """让组名按自然顺序排序：'2' < '10'。"""
    import re
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", s)]


def main():
    ap = argparse.ArgumentParser(
        description="统一选项图尺寸：以最大宽高为准，不足处补透明 alpha。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("inputs", nargs="+", help="一个目录，或若干张图片（当成同一组）")
    ap.add_argument("--out", help="输出目录（默认在输入目录下新建 统一尺寸输出/）")
    ap.add_argument("--align", default="top-left", choices=list(ALIGN.keys()),
                    help="原图在画布里的对齐位置（默认 top-left 左上角）")
    ap.add_argument("--inplace", action="store_true", help="直接覆盖原图（谨慎）")
    args = ap.parse_args()

    if args.align not in ALIGN:
        sys.exit(f"--align 取值无效，可选：{', '.join(ALIGN.keys())}")

    # 判断是「目录模式」还是「手动一组模式」
    if len(args.inputs) == 1 and os.path.isdir(args.inputs[0]):
        directory = args.inputs[0]
        groups = group_directory(directory)
        if not groups:
            sys.exit(f"目录里没找到可处理的图片：{directory}")
        default_out = os.path.join(directory, "统一尺寸输出")
    else:
        for p in args.inputs:
            if not os.path.isfile(p):
                sys.exit(f"找不到文件：{p}")
        groups = {"指定组": list(args.inputs)}
        directory = os.path.dirname(os.path.abspath(args.inputs[0]))
        default_out = os.path.join(directory, "统一尺寸输出")

    out_dir = None
    if not args.inplace:
        out_dir = args.out or default_out
        os.makedirs(out_dir, exist_ok=True)

    print(f"对齐方式：{args.align}    输出：{'覆盖原图' if args.inplace else out_dir}")
    print("-" * 60)

    total_imgs = 0
    for key in sorted(groups.keys(), key=natural_key):
        res = unify_group(key, groups[key], out_dir, args.align, args.inplace)
        if res:
            total_imgs += len(groups[key])

    print("-" * 60)
    print(f"完成：共处理 {len(groups)} 组、{total_imgs} 张图。")
    if not args.inplace:
        print(f"输出目录：{out_dir}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_trace_include_path.py — CI 内执行：修复全树 TRACE_INCLUDE_PATH（clang 兼容）

用法（在工作目录 = 内核根下）：
    python3 fix_trace_include_path.py

原理：
  include/trace/define_trace.h 展开出 **引号形式** include：
      #include "TRACE_INCLUDE_PATH/TRACE_INCLUDE_FILE.h"
  引号 include 的搜索顺序：
      1) 当前头文件所在目录（= <root>/include/trace/）
      2) 依次尝试 -I 列表
  define_trace.h 顶部注释亦明说：
      "the path is relative to define_trace.h, not the file including it"

  所以 TRACE_INCLUDE_PATH 必须是「相对 include/trace/ 的路径」。
  上游正确样例：drivers/dma-buf/sync_trace.h → ../../drivers/dma-buf
  错误写法（clang 下必失败）：
      "."                  → "./x.h" → include/trace/./x.h 不存在
      "arch/arm64/kernel"  → include/trace/arch/... 不存在（-I 里也没有内核根）

修复：改写为 relpath(头文件所在目录, <root>/include/trace)
"""
import os
import re
import sys

PAT = re.compile(r'^([ \t]*#define[ \t]+TRACE_INCLUDE_PATH[ \t]+)(\S+)[ \t]*$', re.M)


def normalize(v):
    v = v.strip().strip('/')
    if v.startswith('./'):
        v = v[2:]
    return v


def main():
    root = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.getcwd()
    trace_dir = os.path.join(root, 'include', 'trace')
    if not os.path.isdir(trace_dir):
        print('  !! 找不到 %s' % trace_dir)
        return 1

    changed = []
    skipped = 0
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in ('.git', '.repo')]
        for fn in fns:
            if not fn.endswith('.h'):
                continue
            full = os.path.join(dp, fn)
            try:
                txt = open(full, encoding='utf-8', errors='ignore').read()
            except OSError:
                continue
            if 'define_trace.h' not in txt:
                continue
            m = PAT.search(txt)
            if not m:
                continue
            rel = os.path.relpath(dp, trace_dir).replace(os.sep, '/')
            if normalize(m.group(2)) == normalize(rel):
                skipped += 1
                continue
            new_txt = PAT.sub(lambda mm: mm.group(1) + rel, txt, count=1)
            with open(full, 'w', encoding='utf-8', newline='') as f:
                f.write(new_txt)
            changed.append((os.path.relpath(full, root).replace(os.sep, '/'),
                            m.group(2), rel))

    print('  已修复 %d 个，原本正确 %d 个' % (len(changed), skipped))
    for relp, old, new in changed[:8]:
        print('    %-64s %s -> %s' % (relp, old, new))
    if len(changed) > 8:
        print('    ...（其余 %d 个略）' % (len(changed) - 8))
    return 0


if __name__ == '__main__':
    sys.exit(main())

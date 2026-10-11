#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_trace_include_path.py — CI 内自校验：模拟 clang 引号 include 搜索

用法（工作目录 = 内核根）：
    python3 check_trace_include_path.py

对每个含 define_trace.h 引用的头文件：
  - 有 TRACE_INCLUDE_PATH：检查 "PATH/NAME.h" 相对 <root>/include/trace 是否存在
  - 无 TRACE_INCLUDE_PATH：走 <trace/events/NAME.h>，单独判定
退出码：0 = 全部通过；1 = 有失败项
"""
import os
import re
import sys

PAT = re.compile(r'^[ \t]*#define[ \t]+TRACE_INCLUDE_PATH[ \t]+(\S+)', re.M)
PATF = re.compile(r'^[ \t]*#define[ \t]+TRACE_INCLUDE_FILE[ \t]+(\S+)', re.M)
PATS = re.compile(r'^[ \t]*#define[ \t]+TRACE_SYSTEM[ \t]+(\S+)', re.M)


def main():
    root = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.getcwd()
    trace_dir = os.path.join(root, 'include', 'trace')
    bad = []
    tot = 0
    nopath = 0
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
            mf = PATF.search(txt)
            ms = PATS.search(txt)
            name = None
            if mf:
                name = mf.group(1)
            elif ms:
                name = ms.group(1)
            if not name:
                continue
            name += '.h'
            mp = PAT.search(txt)
            disp = os.path.relpath(full, root).replace(os.sep, '/')
            if not mp:
                nopath += 1
                continue
            cand = os.path.normpath(os.path.join(trace_dir, mp.group(1), name))
            tot += 1
            if not os.path.exists(cand):
                bad.append((disp, mp.group(1), name))

    print('  >>> 带 TRACE_INCLUDE_PATH 的头文件: %d 个' % tot)
    print('  >>> 不带 TRACE_INCLUDE_PATH（走 <trace/events/>）: %d 个' % nopath)
    print('  >>> 解析失败: %d 个' % len(bad))
    for d, p, n in bad:
        print('      X %s  (%s/%s)' % (d, p, n))
    if bad:
        print('  !! 校验未通过')
        return 1
    print('  OK 全部可解析')
    return 0


if __name__ == '__main__':
    sys.exit(main())

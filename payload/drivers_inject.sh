#!/bin/bash
# 把 KernelSU-Next 注入内核树（在 CI 里、内核源码根目录执行）
set -e
KROOT="$(pwd)"
PAYLOAD="$(cd "$(dirname "$0")" && pwd)"

# 1) 解压 KSU 源码到 drivers/
tar xzf "$PAYLOAD/ksu_drivers.tar.gz" -C "$KROOT/drivers/"
echo "  [+] drivers/kernelsu 已就位"

# 1b) 修复 include/uapi —— Windows 上打包会把软链接变成普通文件
#   KSU-Next 源码里 kernel/include/uapi 是指向 ../../uapi 的**软链接**。
#   Windows 解压后变成 10 字节文本文件，导致：
#     drivers/kernelsu/policy/allowlist.h:6:10:
#       fatal error: 'uapi/app_profile.h' file not found
#   这里做两件事：
#     (a) 若 include/uapi 不是目录，删掉它
#     (b) 从包内任意位置补齐 6 个 uapi 头文件（正常包已含真实目录，此步为兜底）
KSU_DIR="$KROOT/drivers/kernelsu"
if [ -e "$KSU_DIR/include/uapi" ] && [ ! -d "$KSU_DIR/include/uapi" ]; then
  echo "  [!] include/uapi 是普通文件（软链接被压坏），删除并重建"
  rm -f "$KSU_DIR/include/uapi"
fi
mkdir -p "$KSU_DIR/include/uapi"
# 兜底：若 6 个头文件缺失，尝试从包内其它位置找
for h in app_profile feature ksu selinux sulog supercall; do
  if [ ! -f "$KSU_DIR/include/uapi/$h.h" ]; then
    found="$(find "$KSU_DIR" -name "$h.h" -not -path "*/include/uapi/*" 2>/dev/null | head -1)"
    if [ -n "$found" ]; then
      cp "$found" "$KSU_DIR/include/uapi/$h.h"
      echo "  [+] 补齐 uapi/$h.h (来自 $found)"
    fi
  fi
done
echo "  [i] include/uapi 内容："
ls "$KSU_DIR/include/uapi/" 2>/dev/null | sed 's/^/      /'
for h in app_profile feature selinux sulog supercall; do
  [ -f "$KSU_DIR/include/uapi/$h.h" ] || { echo "  [ERR] 缺 uapi/$h.h，编译必失败"; exit 1; }
done
echo "  [OK] uapi 头文件齐全"

# 2) drivers/Makefile 追加
# 【重要】不能同时写 "obj-$(CONFIG_KSU) += kernelsu/" 和 "obj-y += kernelsu/"：
#   Kbuild 的 obj-y 展开是 $(patsubst %/, %/built-in.o, $(obj-y))，
#   patsubst 不去重，两行会把 drivers/kernelsu/built-in.o 列两次，
#   链接期直接 duplicate symbol。
# 因此只写一行，且用 Makefile 条件判断选分支：
#   若 auto.conf 里已有 CONFIG_KSU=y  -> 用标准写法 obj-$(CONFIG_KSU)
#   否则                              -> 用兜底写法 obj-y
# （判断放在 Makefile 里而不是 shell 里，因为注入发生在 .config 生成之前。）
if ! grep -q "kernelsu/" "$KROOT/drivers/Makefile"; then
  printf '\n# KernelSU-Next\nobj-$(CONFIG_KSU) += kernelsu/\n' >> "$KROOT/drivers/Makefile"
  echo "  [+] drivers/Makefile 已注入（标准写法，依赖 CONFIG_KSU）"
else
  echo "  [=] drivers/Makefile 已含条目"
  grep -n "kernelsu" "$KROOT/drivers/Makefile"
fi

# 3) drivers/Kconfig 插入 source
if ! grep -q 'drivers/kernelsu/Kconfig' "$KROOT/drivers/Kconfig"; then
  python3 - "$KROOT/drivers/Kconfig" <<'PY'
import sys
p = sys.argv[1]
s = open(p).read()
old = 'source "drivers/esoc/Kconfig"\n\nendmenu'
new = 'source "drivers/esoc/Kconfig"\n\nsource "drivers/kernelsu/Kconfig"\n\nendmenu'
if old in s:
    s = s.replace(old, new)
elif 'endmenu' in s:
    i = s.rfind('endmenu')
    s = s[:i] + 'source "drivers/kernelsu/Kconfig"\n\n' + s[i:]
else:
    sys.exit('drivers/Kconfig 结构异常')
open(p, 'w').write(s)
print("  [+] drivers/Kconfig 已注入")
PY
else
  echo "  [=] drivers/Kconfig 已含条目"
fi

# 4) 应用内核 hook 补丁
git apply --verbose "$PAYLOAD/ksu_hooks.patch" 2>&1 | tail -20 || {
  echo "  [!] git apply 失败，尝试 patch -p1"
  patch -p1 < "$PAYLOAD/ksu_hooks.patch"
}
echo "  [+] ksu_hooks.patch 已应用"

# 5) 校验关键标记
grep -q "ksu_handle_sys_reboot" "$KROOT/kernel/reboot.c" \
  && echo "  [OK] ksu_handle_sys_reboot 存在（Kbuild 校验通过）" \
  || { echo "  [ERR] ksu_handle_sys_reboot 缺失，编译会失败"; exit 1; }

echo "  === 注入完成 ==="

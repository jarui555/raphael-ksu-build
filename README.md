# raphael KernelSU-Next 内核编译

用 GitHub Actions 编译一颗集成 **KernelSU-Next** 的 4.14 内核，
用于 Redmi K20 Pro (raphael / SM8150)。

- 基座：`qaz6750/android_kernel_xiaomi_sm8150` @ `a14-xiaomi-4.14.y`
- 配置：真机 /proc/config.gz + `CONFIG_KSU=y` + `CONFIG_KSU_MANUAL_HOOK=y`
- 工具链：AOSP clang-r383902 + aarch64-linux-android-4.9

## 怎么编

1. 打开仓库 **Actions** 页
2. 左侧选 **Build raphael kernel (KernelSU-Next)**
3. 点 **Run workflow** → 绿色按钮
4. 等 30~60 分钟
5. 进入该次 run，页面底部 **Artifacts** 下载 `raphael-ksu-Image`
6. 解压得到 `Image.gz`

## 编译完怎么刷

```bash
python pack_boot.py rom/boot.img Image.gz boot_ksu.img
adb reboot bootloader
fastboot flash boot boot_ksu.img
fastboot reboot
```

## 验证

```bash
adb shell su -c id          # 应返回 uid=0
adb shell 'cat /proc/version'
```

配 KernelSU Next 管理器 APK 使用。

# 全能下载器 · OmniDL

> **Omnipresent Media Acquisition Engine** — 泛在媒体获取引擎

全平台智能媒体下载工具，覆盖 1000+ 网站的视频/图片下载，支持 Android 原生运行。

---

## 🎯 核心特性

| 特性 | 说明 |
|------|------|
| 🧠 **Intelligent URL Parser** | 基于 yt-dlp 的智能链接解析引擎，自动识别 1000+ 站点 |
| 📱 **Fully Offline** | 纯本地执行，无需服务器，隐私零泄露 |
| 🐍 **Python-on-Android** | Chaquopy 内嵌 Python 3.8 运行时，直接在设备上运行 yt-dlp |
| 📂 **System Integration** | MediaStore API 写入，文件直接出现在系统相册和文件管理器 |
| 📋 **Share Intent** | 从任何 App 分享链接到全能下载器，自动提取 URL |
| 📊 **Live Progress** | 实时下载进度、速度显示 |
| 🔍 **Diagnostic Logger** | 内置运行时日志面板，一键复制排错 |

## 📦 支持平台

| 平台 | 识别 | 下载 | 备注 |
|------|:--:|:--:|------|
| 抖音 / TikTok | ✅ | ✅ | 无需登录 |
| Bilibili | ✅ | ✅ | 登录=原画 |
| 小红书 | ✅ | ✅ | 视频+图文全支持 |
| YouTube | ✅ | ✅ | 无需登录 |
| Instagram | ✅ | ✅ | — |
| 微博 | ✅ | ✅ | — |
| ... | | | 1000+ 站点 |

## 🚀 快速开始

[→ 下载最新 Release](https://github.com/min09577/universal-downloader/releases)

**分享链接使用**：在抖音/B站/小红书等 App 中「分享→复制链接」→ 打开全能下载器 → 自动识别

**粘贴链接**：直接粘贴 URL →「识别」→「下载」

## 🛠️ 本地构建

```bash
cd standalone-android
echo "sdk.dir=$ANDROID_HOME" > local.properties
./gradlew assembleDebug
```

## 🏗️ 技术架构

```
Kotlin UI ── Chaquopy Bridge ── Python Engine (yt-dlp + requests)
     │                                  │
CookieManager ←── WebView OAuth ──→ CookieJar → yt-dlp Extractors
     │                                  │
MediaStore API ←─────────────────── Downloads → /sdcard/Download/
```

## 📝 更新日志

### v1.0.0 — 泛在媒体获取引擎 · 正式版 (2026-06-17)

- 🏛️ **Xiaohongshu Production Pipeline** — 完整视频与图文下载管线。Triple-Pass URL Canonicalizer (normalize→resolve→normalize) 消除移动端参数，经 20+ 真实链接回归测试，成功率 >90%
- 🖼️ **Dual-Mode Content Detector** — 智能区分视频帖/图文帖，__INITIAL_STATE__ 解析 → yt-dlp 或 batch download 分流
- 🔐 **Three-Tier Cookie Injection** — Kotlin WebView → CookieManager → Python CookieJar 三级认证桥接
- 🎨 **Image Batch Downloader** — image_list 原图 URL 提取，按序号批量保存
- 📊 **Precision Diagnostics** — 每个失败点输出精确原因，告别黑盒报错

### v0.9.11 (2026-06-16)
- 🔗 **Mobile URL Normalizer** — 短链接解析后二次清洗，消除移动端参数

### v0.9.10 (2026-06-16)
- 🔄 **Architecture Pivot** — 放弃手写解析器，回归 yt-dlp + CookieManager 路线

### v0.9.1 – v0.9.9 (2026-06-16)
- 🧬 edith API → __INITIAL_STATE__ → yt-dlp Cookies 三次架构重构
- 🎬 B站 Adaptive Quality + 📂 MediaStore System Integration
- 🩺 Real-Time Diagnostic Panel + 一键复制日志

### v0.8.0 (2026-06-16)
- 🚀 Initial Release — Chaquopy + yt-dlp Android 集成

## 📄 License

MIT License

<p align="center">
  <sub>Built with Kotlin · Python · Chaquopy · yt-dlp</sub>
</p>

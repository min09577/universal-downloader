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
| Bilibili | ✅ | ✅ | 建议登录 |
| YouTube | ✅ | ✅ | 无需登录 |
| 小红书 | ⚠️ | ⚠️ | 需内置 WebView 登录 |
| 微博 | ✅ | ✅ | — |
| Instagram | ✅ | ✅ | — |
| Twitter / X | ✅ | ✅ | — |
| 快手 | ✅ | ✅ | — |
| ... | | | 1000+ 站点 |

## 🚀 快速开始

### 方式一：直接安装 APK

[→ 下载最新 Release](https://github.com/min09577/universal-downloader/releases)

### 方式二：分享链接使用

在抖音/B站/小红书等 App 中：
1. 点击「分享」→「复制链接」
2. 打开全能下载器 → 自动识别
3. 点击「下载」

### 方式三：粘贴链接

直接粘贴 URL 到输入框 → 点击「识别」→ 点击「下载」

## 🛠️ 本地构建

```bash
# 需要 Android Studio + Python 3.12+
cd standalone-android
echo "sdk.dir=$ANDROID_HOME" > local.properties
./gradlew assembleDebug
# APK: app/build/outputs/apk/debug/app-debug.apk
```

## 🏗️ 技术架构

```
┌─────────────────────────────────────┐
│            MainActivity.kt          │  ← Kotlin UI Layer
├─────────────────────────────────────┤
│           PythonBridge.kt           │  ← Chaquopy Bridge
├─────────────────────────────────────┤
│         downloader.py               │  ← Python Engine
│  ┌───────┐ ┌──────────┐ ┌───────┐  │
│  │yt-dlp │ │ requests │ │certifi│  │  ← Embedded Python Packages
│  └───────┘ └──────────┘ └───────┘  │
├─────────────────────────────────────┤
│       Chaquopy Python 3.8 Runtime   │  ← Native .so
├─────────────────────────────────────┤
│            Android OS               │
└─────────────────────────────────────┘
```

## 📝 更新日志

### v0.9.1 (2026-06-16)

- 🧠 **Intelligent URL Extraction** — 自动从分享文本中提取纯净 URL
- 🔐 **OAuth WebView Portal** — 内置 WebView 平台登录，自动注入 cookies
- 🔧 **Bilibili Format Optimizer** — 修复 ffmpeg 依赖导致的下载失败
- 📂 **MediaStore Integration** — 文件通过系统 API 写入，相册即时可见
- 🐛 **CookieManager Crash Fix** — 通过 Kotlin 主线程桥接安全获取 cookies
- 🩺 **Runtime Diagnostic Panel** — 底部实时日志窗口，支持一键复制

### v0.8.0 (2026-06-16)

- 🚀 **Initial Release** — Chaquopy + yt-dlp 安卓集成
- ✅ 抖音识别与下载通过
- 🔧 GitHub Actions CI/CD 自动构建

## 📄 License

MIT License — 自由使用、修改、分发。

---

<p align="center">
  <sub>Built with Kotlin · Python · Chaquopy · yt-dlp</sub>
</p>

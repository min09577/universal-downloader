# 📱 真·独立 Android App 构建指南

## 🎯 这是什么

这是一个**完全独立**的 Android App。不需要服务器，不需要电脑中转，所有下载在手机本地完成。

- 🐍 内嵌 Python 运行环境（通过 Chaquopy）
- 🎬 内嵌 yt-dlp 下载引擎（1000+ 网站支持）
- 📱 纯本地运行，零服务器成本
- 🔗 支持从其他 App（微信/QQ/浏览器）分享链接直接下载
- 📋 自动监听粘贴板

---

## 🛠️ 技术架构

```
[Android App]
    ├── Kotlin/Java UI (Material Design 3)
    │   ├── URL 输入 & 粘贴板监听
    │   ├── 下载进度显示
    │   └── 历史记录管理
    │
    ├── Chaquopy (Python 运行时)
    │   └── PythonBridge.kt
    │       ├── analyze_url()
    │       ├── download_video()  ← yt-dlp
    │       ├── download_image()
    │       └── extract_images()
    │
    └── 文件保存到 Download/UniversalDownloader/
```

**APK 大小**: 约 40-50 MB（含 Python + yt-dlp）

---

## 📋 构建环境要求

### Windows
```
1. Android Studio Hedgehog (2023.1+) 或更新版
2. Android SDK 34
3. JDK 17
4. Python 3.11 (必须在 C:\Users\你的用户名\AppData\Local\Programs\Python\Python311\)
```

### Mac
```
1. Android Studio
2. Android SDK 34
3. JDK 17
4. Python 3.11 (brew install python@3.11)
```

---

## 🚀 构建步骤

### 1. 安装 Python 3.11

**必须用 Python 3.11**，Chaquopy 对此版本兼容最好。

- Windows: 从 python.org 下载 3.11.x，安装到默认路径
- Mac: `brew install python@3.11`

### 2. 打开项目

用 Android Studio 打开 `standalone-android/` 目录。

Android Studio 会自动下载 Gradle 和依赖。

### 3. 配置 Python 路径

编辑 `app/build.gradle.kts` 第 24 行：

```kotlin
python {
    // 改成你的 Python 3.11 路径
    buildPython("C:/Users/你的用户名/AppData/Local/Programs/Python/Python311/python.exe")
    // Mac: buildPython("/usr/local/bin/python3.11")
    pip {
        install("yt-dlp>=2024.0")
        install("requests>=2.28")
    }
}
```

### 4. 构建 APK

**方法 A：Android Studio**
- 菜单 Build → Build Bundle(s) / APK(s) → Build APK(s)
- APK 在 `app/build/outputs/apk/debug/app-debug.apk`

**方法 B：命令行**
```bash
# Windows
gradlew.bat assembleDebug

# Mac
./gradlew assembleDebug
```

### 5. 安装到手机

```bash
adb install app/build/outputs/apk/debug/app-debug.apk
```

或直接把 APK 传到手机安装。

---

## 📲 使用方式

### 方式一：App 内粘贴
1. 复制一个链接（B站/抖音/YouTube/小红书等）
2. 打开万能下载器
3. 点「粘贴」按钮自动填入
4. 点「识别」→「下载」

### 方式二：从其他 App 分享
1. 在浏览器/微信/QQ 中打开一个视频页面
2. 点「分享」→选择「万能下载器」
3. 自动识别并提示下载

### 下载的文件在哪里？
```
文件管理器 → Download → UniversalDownloader/
```

---

## 🔧 自定义配置

### 修改 Python 版本

如果想用其他 Python 版本：
1. 安装对应版本的 Python
2. 修改 `app/build.gradle.kts` 中的 `buildPython` 路径
3. 可能需要调整 Chaquopy 版本（见 `https://chaquo.com/chaquopy/`）

### 修改下载上限

编辑 `app/src/main/python/downloader.py`：
```python
"max_filesize": 500 * 1024 * 1024,  # 改成更大的值
```

### 修改画质

```python
"format": "best[height<=1080]",  # 1080p 上限，改成 720/480 等
```

---

## ❓ 常见问题

### Q: 为什么 APK 这么大？
A: Python 运行时 (~15MB) + yt-dlp (~5MB) + 依赖 (~5MB) + Android 库 (~10MB)

### Q: 真的不需要服务器？
A: 对。yt-dlp 直接在手机上运行，解析视频地址、下载视频都在本地完成。和你在电脑上用 yt-dlp 完全一样。

### Q: 某些网站下载失败？
A: 和电脑版 yt-dlp 一样，某些平台可能更新反爬策略导致临时失效。更新 yt-dlp 版本即可修复：
1. 修改 `app/build.gradle.kts` 中 pip install 的版本号
2. 重新构建 APK

### Q: 下载速度慢？
A: 取决于你的 WiFi/4G/5G 网速和视频源服务器。和电脑下载速度一样。

### Q: 支持哪些平台？
A: yt-dlp 支持的 1000+ 网站都支持：
- 🇨🇳 B站、抖音、小红书、微博、快手、知乎、优酷、爱奇艺、腾讯视频
- 🌍 YouTube、Instagram、Twitter/X、Facebook、TikTok、Vimeo
- 以及更多...

---

## ⚠️ 免责声明

本应用仅供个人学习和技术研究使用。请遵守相关法律法规，尊重版权，仅下载你有权下载的内容。

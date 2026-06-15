# 万能下载器 (Universal Downloader)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-blue)](https://www.python.org/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/min09577/universal-downloader/pulls)

🌐 一个强大的全网图片/视频智能下载工具。粘贴任意链接，自动识别并下载。

## ✨ 特性

- 🔍 **智能识别** — 自动判断链接类型（视频/图片/网页），无需手动选择
- 🎬 **视频下载** — 基于 yt-dlp 引擎，支持 1000+ 网站（B站、YouTube、抖音、小红书、微博等）
- 🖼️ **图片提取** — 自动提取网页中所有图片，批量下载
- 📊 **实时进度** — 下载速度、百分比实时显示
- 📱 **PWA 支持** — 可安装到手机桌面，像原生 App 一样使用
- 🤖 **APK 打包** — 支持构建为 Android APK（基于 Capacitor）
- 🌙 **深色主题** — 现代化暗色 UI 设计
- 📋 **历史管理** — 自动记录下载历史，支持一键重下

## 🚀 快速开始

### 环境要求

- Python 3.9+
- pip

### 安装

```bash
# 克隆仓库
git clone https://github.com/min09577/universal-downloader.git
cd universal-downloader

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 运行

```bash
python app.py
```

打开浏览器访问 `http://127.0.0.1:5000`

### 安装 ffmpeg（可选，推荐）

部分视频格式需要 ffmpeg 进行合并处理：

- **Windows**: 下载 [ffmpeg](https://ffmpeg.org/download.html) 并添加到 PATH
- **Mac**: `brew install ffmpeg`
- **Linux**: `sudo apt install ffmpeg`

## 📱 手机端使用

### 方式一：PWA（推荐）

1. 确保手机和电脑在同一局域网
2. 启动服务：`python app.py --host 0.0.0.0`
3. 手机浏览器访问 `http://你的电脑IP:5000`
4. Chrome 会自动提示「添加到主屏幕」

### 方式二：构建 APK

参见 [BUILD_APK.md](BUILD_APK.md)

## 🏗️ 项目结构

```
universal-downloader/
├── app.py                 # Flask 后端（含 API + HTML 模板）
├── requirements.txt       # Python 依赖
├── static/
│   ├── css/
│   │   └── style.css      # UI 样式
│   ├── js/
│   │   └── app.js         # 前端逻辑
│   ├── manifest.json      # PWA 清单
│   └── sw.js              # Service Worker
├── android/               # Capacitor Android 项目
├── downloads/             # 下载文件目录
├── LICENSE
└── README.md
```

## 🔌 API 接口

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/analyze` | POST | 分析 URL，识别类型 |
| `/api/download` | POST | 开始下载任务 |
| `/api/task/<id>` | GET | 查询下载进度 |
| `/api/history` | GET | 获取下载历史 |
| `/api/files` | GET | 列出已下载文件 |
| `/api/stats` | GET | 获取统计信息 |

## 🤝 贡献

欢迎提交 PR 和 Issue！请确保代码风格一致。

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

## ⚠️ 免责声明

本工具仅供个人学习和技术研究使用。请遵守相关法律法规，尊重版权，不要下载未经授权的内容。

## 🙏 致谢

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - 强大的视频下载引擎
- [Flask](https://flask.palletsprojects.com/) - Web 框架
- [Capacitor](https://capacitorjs.com/) - 跨平台应用框架

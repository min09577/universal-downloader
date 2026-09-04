# <p align="center">全能下载器 · OmniDL</p>
<p align="center"><strong>泛在媒体获取引擎 | 粘贴任意链接 · 自动识别 · 1000+ 站点图片/视频下载 | Android 本地运行 · 纯离线 · 零服务器 | Kotlin · Python · yt-dlp</strong></p>
<p align="center">
    <a href="https://github.com/min09577/universal-downloader/releases/latest">
        <img alt="Latest Release" src="https://img.shields.io/github/v/release/min09577/universal-downloader?style=flat&color=blue">
    </a>
    <a href="https://github.com/min09577/universal-downloader/actions/workflows/build-apk.yml">
        <img alt="Build Status" src="https://github.com/min09577/universal-downloader/actions/workflows/build-apk.yml/badge.svg?branch=main">
    </a>
    <a href="https://github.com/min09577/universal-downloader/blob/main/LICENSE">
        <img alt="License" src="https://img.shields.io/badge/License-AGPL%203.0-green.svg">
    </a>
    <img alt="API" src="https://img.shields.io/badge/API-26%2B-brightgreen">
    <img alt="yt-dlp" src="https://img.shields.io/badge/yt--dlp-1000%2B%20sites-orange">
</p>

> ### 👤 维护者近况 / Maintainer's Corner
> 当你发现本仓库没有更新版本或修复 Bug 时，维护者大概率正在 **旅行、跑外卖、打游戏、写小说**，
> 或是在 **美 / 韩 / 日 股市与外汇市场** 间辗转腾挪，亦或是在领取失业金——生活的剧本从不单一。
>
> 但请放心：**每一枚被提交的 Bug，都会被逐一排查、逐一修复。**
>
> - 📱 **测试设备**：三星 Galaxy S 系列旗舰 + Z Fold 系列（港版系统）
> - 🚀 **规划中**：后续有望纳入 OPPO / vivo / 小米 真机覆盖
> - 🐉 **鸿蒙现状**：暂未持有鸿蒙真机，鸿蒙端 Bug 短期内较难定位修复；如有鸿蒙设备的朋友，欢迎自行下载源码尝试修复

---

## ☕ 随缘赞助 (Sponsor)

这个项目是利用业余时间"用爱发电"写出来的，能帮到大家我非常开心。不过随着项目的不断完善，跑测试消耗的 API Tokens 确实超出了我的预期，加上长时间的调试，也搭进去了不少休息时间（笑）。

如果这个项目恰好为你解决了问题，或者帮你省下了一些折腾的时间，欢迎随缘投喂。你的打赏将全部用于"回血"高昂的 API 账单，这也是让我能毫无顾忌持续更新它的最大动力。

当然，完全自愿，千万别有任何压力。只要你觉得好用，点个 **Star** 同样是对我极大的鼓励！

> **Tip:** 为了避免大家承担高昂的转账手续费，建议通过 **BNB Smart Chain (BEP-20)** 网络进行转账。感谢支持！

<p align="center">
    <img src="docs/images/sponsor_qr.png" alt="Sponsor QR (Binance · BEP-20)" width="360">
</p>

<p align="center"><i>币安收款二维码 · Binance Wallet QR（USDT · BNB Smart Chain / BEP-20）</i></p>

---

## ✨ 为什么选择全能下载器 / Why OmniDL

| 特性 | 说明 |
|------|------|
| 🧠 **智能链接解析** | 基于 yt-dlp 抽取引擎，自动识别 1000+ 站点，粘贴即下 |
| 🎥 **B站 4K 下载** | 4K 限免视频自动获取完整 4K 流（3840×2160），大会员账号全站 4K 直下 |
| 🔊 **B站有声拼装** | 内置 FFmpegKit（FFmpeg 6.0）端内 `-c copy` 无损拼装双轨，系统级 MediaMuxer 兜底，PTS 重建防绿屏 |
| 📱 **Fully Offline** | 纯本地执行，无服务器中转，隐私零泄露 |
| 🐍 **Python-on-Android** | Chaquopy 内嵌 Python 运行时，yt-dlp 直接在设备上跑 |
| 📕 **小红书深度适配** | 2026 前端全面适配：图文/视频双管线、`xsec_token`、短链 `.cn` 域名、EF4~EF7 码率选优 |
| 🖼️ **图文批量下载** | 多图笔记按序号批量保存，直取 WB_DFT 高清档 |
| 🎬 **视频直连下载** | 解析 `masterUrl` 按 `videoBitrate` 选最优流，不依赖第三方适配进度 |
| 🔐 **三级 Cookie 桥** | WebView 登录 → CookieManager → Python CookieJar，登录即原画 |
| 📲 **分享即下** | 任意 App「分享→复制链接」→ 打开即自动识别提取 |
| 📊 **Live Progress** | 实时下载进度、速度显示 |
| 📂 **System Integration** | MediaStore 写入，文件直达系统相册与文件管理器 |
| 🔍 **Diagnostic Logger** | 内置运行时日志面板，一键复制排障 |
| 🧪 **PC 测试台** | `tests/xhs_harness.py` 秒级回归真实管线，改码不必重装 APK |
| 🚫 **零广告** | 无横幅、无推广、无追踪，纯粹下载体验 |
| 📦 **一键安装** | [Release 页面](https://github.com/min09577/universal-downloader/releases/latest) 直接下载 APK |

---

## 📖 简介

全能下载器（OmniDL）是一个**纯本地**的全网媒体下载 Android 客户端：Kotlin UI + Chaquopy 内嵌 Python 运行时，在设备上直接运行 yt-dlp 与自研解析管线，覆盖 1000+ 站点的视频/图片下载。不经过任何服务器，无账号体系，无埋点。

当前版本已实现：**B站 4K 下载**（限免视频完整 4K / 大会员全站 4K）、**B站视频有声**（FFmpegKit 端内无损拼装）、**小红书 2026 管线**（图文/视频双管线全面适配）、实时进度、系统相册直达——完整能力矩阵见下方特性表与[版本迭代记录](#-版本迭代记录--version-history)。

> **⚠️ 声明：** 本软件及源码仅供学习交流使用，严禁用于商业用途。与各平台官方无关，请尊重内容创作者权益。

## 🆕 ai.1.0.21 — B站 4K 下载

> ### 🎬 4K 限免视频，完整 4K 直下
> B 站将部分 4K 视频标记为「4K 限免」，对全部登录用户开放 4K 流。
> 本版本新增 B 站专用 4K 路径：登录后自动请求 4K 流（`qn=120` + `fourk`），
> 严格校验服务端实际下发的流（`id==120` 筛选），拿到即下，拿不到自动降级
> yt-dlp 管线取账号内最高画质——**所见即所得，绝不虚标**。
>
> ### 🔬 真机实测
> 影视飓风 4K 年度样片（218 秒）：视频轨 328.1MB + 音频轨 5.1MB →
> FFmpegKit 合并 349.6MB，ffprobe 确认 **h264 · 3840×2160 · 12.6Mbps · 完整时长含 AAC 音轨**。
>
> ### 🛠️ 附带修复
> - `[bili4k]` 全链路日志打点，降级原因一目了然
> - 流下载 2 次退避重试，瞬态网络抖动不再静默降级
> - 产物检测改模板匹配，历史残留文件不再误报「下载失败」
>
> 📌 **画质与账号关系**：非限免 4K 需大会员账号（B 站服务端按账号权限下发流），
> 登录大会员后全站 4K 自动解锁——详见上方「B站画质下载说明」。

## 🆕 ai.1.0.14~1.0.20 — B站音频引擎与拼装链路攻坚

> ### 🔊 B站视频有声正式落地
> B站 DASH 双流分下（视频 H.264/avc1 限定 + 音频 m4a），
> **内置 FFmpegKit（FFmpeg 6.0）**端内 `-c copy` 无损拼装，分片 fMP4 格式通吃；
> 系统级 MediaMuxer 自动降级兜底，任何环境都有声音。
>
> ### 🖥️ 播放体验护航
> `-fflags +genpts -avoid_negative_ts make_zero` PTS 重建，
> 修复 B 帧密集流时间戳缺失引发的绿屏；合并产物经 MediaStore 直达系统 Download/相册；
> 修复拼装输出与输入同名冲突、轨道选择时序、引擎装载链路等一系列深水区问题。
>
> ### 🔬 诊断体系
> `OmniDL-Merge` 会话日志捕获（含 ffmpeg 原始错误尾部），排障效率倍增。

## 🆕 ai.1.0.5~1.0.8 — 品牌塑造与发布体系

> ### 🧭 关于中心与更新通道
> 新增设置式「关于」常驻入口（仓库主页直连 / 版本信息 / 检查更新）；
> **检查更新双通道**：`api.github.com` 受限环境自动切换 `releases/latest` 重定向，
> 国内网络可达性大幅提升。
>
> 🔏 **固定签名发布线**：独立 keystore 全版本签名，永久支持覆盖安装。

## 🆕 v1.0.4 — 小红书 2026 管线重构

> ### 🧬 站点改版全面适配，图文视频双双回归
> 小红书前端重构导致旧管线全面失效，本版本逐项击破：
> 页面内联数据混入 `new Map()` JS 构造 → 新增括号配平解析器；
> 字段全面 camelCase 化（`imageList`/`urlDefault`/`infoList`）→ 新旧双格式兼容；
> 笔记详情多包一层 `.note` → 统一解包。
>
> ### 🔗 短链新域名 + 视频直连
> 分享短链迁移至 **`xhslink.cn`**（旧 `.com` 同样支持）；
> 视频不再依赖 yt-dlp 适配进度——直连 `masterUrl`，遍历 `EF4~EF7` 清晰度分组按码率选最优；
> 图片直取 **WB_DFT 高清档**（比预览图大 3~4 倍）。
>
> ### 🧪 附赠：PC 测试台
> `tests/xhs_harness.py` 直接加载 App 内真实 Python 管线，`probe / download / regress`
> 三个命令秒级回归，把「改码→CI→装 APK→手测」的分钟级循环压到秒级。

## 🎬 B站画质下载说明 / Bilibili Quality Guide

<details open>
<summary><b>🇨🇳 中文 — 画质与账号权限对照表</b></summary>

| 视频类型 | 未登录 | 普通账号登录 | 大会员登录 |
|---|---|---|---|
| **4K 限免视频**（标题带「4K限免」标） | 480P | **✅ 真 4K（3840×2160）** | ✅ 真 4K |
| **4K 专属视频**（无限免标） | 480P | 1080P（B站服务端限制，任何客户端无法绕过） | **✅ 真 4K** |
| 1080P 高码率 / 1080P60 | 480P | ✅ **自动顶格** | ✅ |
| HDR / 杜比视界 | — | — | ✅ |

**原理（说人话）**：B 站服务器按登录账号的会员身份决定下发哪些流。本 App 的策略是「**服务端给什么就下什么，永远挑最高档**」——

- **限免 4K**：B 站官方将此类视频的 4K 流对全部登录用户开放，本 App 自动获取完整 4K 流（含音轨），真机实测 349MB / 218 秒完整时长
- **非限免 4K**：4K 流地址仅对大会员账号下发。**登录大会员账号后，全站 4K/杜比 自动解锁下载，无需任何额外操作**
- 未登录 / 普通账号：自动获取该账号权限内的最高画质（1080P 高码率 / 1080P60），绝不虚标

> ⚠️ **非会员下载非限免 4K 无法通过任何客户端技术实现**——B 站服务端按账号权限裁剪流地址，请知悉。如需全站 4K，开通大会员后直接登录即可。

</details>

<details>
<summary><b>🇺🇸 English — Quality & Account Matrix</b></summary>

| Video Type | Anonymous | Free Account | Premium (大会员) |
|---|---|---|---|
| **4K Limited-Free** (「4K限免」badge) | 480P | **✅ True 4K (3840×2160)** | ✅ True 4K |
| **4K Exclusive** (no badge) | 480P | 1080P (server-side limit, no client can bypass) | **✅ True 4K** |
| 1080P High-Bitrate / 60fps | 480P | ✅ **Auto-max** | ✅ |
| HDR / Dolby Vision | — | — | ✅ |

**How it works**: Bilibili's server decides which streams to serve based on your account's membership. OmniDL always downloads **the highest quality the server actually serves** — for Limited-Free 4K videos that means true 4K with audio (verified on-device: 349MB, full duration); for 4K-exclusive videos, a Premium account unlocks full-site 4K downloads automatically after login. No technical trick can bypass the server-side permission model for non-premium accounts.

</details>

## 💡 使用贴士 / Pro Tips

| 场景 | 建议 |
|------|------|
| 📋 **粘贴链接** | 支持带中文口令的整段分享文本，自动提取纯净 URL |
| 📲 **分享即下** | 在抖音/B站/小红书点「分享」，选择全能下载器，自动识别 |
| 🔐 **B站原画** | 先在 App 内「B站登录」完成 WebView 登录，再下载即原画；**大会员账号登录后全站 4K 自动解锁**（见上方画质说明） |
| 📕 **小红书图文** | 多图笔记批量保存，历史记录点击可回看原图 |
| 📋 **排障辅助** | 日志面板 → 一键复制 → 提交 issue 时附上，事半功倍 |
| 🧪 **开发者** | `python tests/xhs_harness.py regress` 跑回归，`cookies_xhs.txt` 放登录态（已 gitignore） |

## 💬 反馈与贡献 / Feedback & Contribution

🐛 发现 Bug？💡 有好想法？欢迎通过 GitHub Issues 提交：

<p align="center">
    <a href="https://github.com/min09577/universal-downloader/issues">
        <img alt="GitHub Issues" src="https://img.shields.io/github/issues/min09577/universal-downloader?style=flat&color=red&label=%F0%9F%90%9B%20Bug%20%2F%20Feature">
    </a>
</p>

> 提交时请携带**应用日志**（主界面日志面板 → 复制），越详细修复越快。

## 📋 版本迭代记录 / Version History

> 持续高频迭代：2026-09-02 复工以来 3 天内发布 **17 个版本**，从画质管线到引擎架构完成了一次全面跃迁。

**序章 · 项目奠基（2026-06）**

| 版本 | 亮点 |
|---|---|
| v0.8.0 | 🚀 首发版本 — Chaquopy + yt-dlp Android 端内集成，1000+ 站点解析引擎上线 |
| v0.9.1~0.9.11 | 🏗️ 三次管线架构演进：edith API → `__INITIAL_STATE__` → yt-dlp + Cookie 桥 |
| v1.0.0~1.0.3 | 📕 小红书生产管线成型 — Triple-Pass URL 规范化 + 图文批量下载 + 三策略降级 + `xsec_token` |

**第一阶段 · 复工与品牌重塑（2026-09-02）**

| 版本 | 亮点 |
|---|---|
| v1.0.4（ai.1.0.4） | 🧬 **2026 管线重构** — 应对小红书年度级前端改版：`new Map()` 括号配平解析器、全量字段 camelCase 双格式兼容、`.note` 结构解包、`xsec_token` 全链路贯通、`xhslink.cn` 新短域接入、`EF4~EF7` 清晰度分组码率选优直连；同步交付 **PC 秒级测试台**（`tests/xhs_harness.py`），将「改码→CI→装机→手测」的分钟级循环压缩至秒级 |
| ai.1.0.5~1.0.7 | 🧭 **信息架构重构** — 新增 ⚙ 关于中心（仓库主页直连 / 版本信息 / 更新通道），设置式常驻入口，版本号规范呈现 |
| ai.1.0.8 | 🌐 **检查更新双通道** — `api.github.com` 受限环境自动切换 `releases/latest` 重定向通道，国内网络可达性大幅提升 |
| 签名体系 | 🔏 **固定签名发布线** — 独立 keystore 全版本签名，自 ai.1.0.4-b62 起永久支持覆盖安装 |

**第二阶段 · B站音频引擎攻坚（2026-09-03）**

| 版本 | 亮点 |
|---|---|
| ai.1.0.9 | 🔊 **双轨架构奠基** — B站 DASH 双流分下 + Kotlin↔Python 进度回调贯通 |
| ai.1.0.10 | 🎯 **格式链修正** — 无 ffmpeg 环境纯视频流策略（规避无合并器中断） |
| ai.1.0.11 | ⚙️ **系统级拼装** — 端内 MediaMuxer 无损 remux 双轨，无需外部依赖 |
| ai.1.0.12 | 🧬 **编码适配** — 视频轨锁定 H.264（avc1），规避 MediaMuxer 对 AV1/HEVC 的兼容缺陷 |
| ai.1.0.13 | 🔧 **轨道时序硬化** — selectTrack 前置 + 4MB 大帧缓冲 |
| ai.1.0.14 | 🚀 **FFmpegKit 引擎内置** — FFmpeg 6.0 端内无损 `-c copy` 拼装，分片 fMP4 格式通吃，**B站视频有声正式落地** |

**第三阶段 · 拼装链路全面强化（2026-09-03）**

| 版本 | 亮点 |
|---|---|
| ai.1.0.15~1.0.17 | 🔬 **诊断体系** — 引擎装载链路修复 + `OmniDL-Merge` 会话日志捕获（含 ffmpeg 原始错误尾部） |
| ai.1.0.18 | 🧯 **同名冲突** — 修复拼装输出与输入流同名导致的 ffmpeg 原地编辑拒绝 |
| ai.1.0.19 | 📂 **落盘直达** — 合并产物 MediaStore 补落盘，文件直达系统 Download/相册 |
| ai.1.0.20 | 🖥️ **PTS 重建** — `-fflags +genpts -avoid_negative_ts make_zero` 修复 B 帧密集流时间戳缺失引发的绿屏 |

**第四阶段 · 4K 高画质管线（2026-09-04）**

| 版本 | 亮点 |
|---|---|
| **ai.1.0.21** | 🎬 **B站 4K 引擎** — 全新 B站专用高画质管线：登录态自动请求 4K 源（`qn=120` + `fourk`），严格校验服务端实际下发流（`id==120` 逐条筛验），**4K 限免视频完整 4K 直下**（真机实测：349.6MB · 3840×2160 · 12.6Mbps · 完整时长含 AAC 音轨）；未获 4K 自动降级 yt-dlp 管线取账号内顶格画质，**所见即所得，永不虚标**；附带 `[bili4k]` 全链路可观测、流下载退避重试、产物模板匹配检测；gRPC 高画质桥接层架构预留 |
| — | 📌 画质与账号权限的完整对照见上方 [B站画质下载说明](#-b站画质下载说明--bilibili-quality-guide) |

[⬇️ 最新 Release](https://github.com/min09577/universal-downloader/releases/latest) — **APK 下载点这里 / Download APK here**

---

## 🛠️ 构建说明 / Build Instructions

### 环境要求 / Prerequisites

- **JDK 17+**
- **Android SDK** with **compileSdk 34**
- **Python 3.8+**（Chaquopy 构建期需要，`PYTHON_PATH` 环境变量指向其可执行文件）
- Android Studio (推荐 / Recommended)

### 构建命令 / Build Commands

```bash
cd standalone-android
echo "sdk.dir=$ANDROID_HOME" > local.properties
export PYTHON_PATH=$(which python3)   # Windows: set PYTHON_PATH=path\to\python.exe
./gradlew assembleDebug
```

构建产物位于 `standalone-android/app/build/outputs/apk/` 目录。

> 💡 推送至 `main` 分支会自动触发 GitHub Actions 构建，并在 Release 页发布 APK。

---

## ⚠️ 免责声明 / Disclaimer

<details>
<summary>🇨🇳 中文</summary>

1. 本软件为**非官方**媒体下载工具，与各内容平台官方无任何关联。
2. 本软件及源码**仅供学习交流使用，严禁用于商业用途**。
3. 请尊重内容创作者权益，下载内容请勿用于商业传播。
4. 使用本软件所产生的一切后果由使用者自行承担。
5. 本软件不保证功能的完整性和稳定性。

</details>

<details>
<summary>🇯🇵 日本語</summary>

1. 本ソフトウェアは**非公式**のメディアダウンロードツールであり、各プラットフォーム公式とは一切関係がありません。
2. 本ソフトウェアおよびソースコードは**学習・交流のみを目的としており、商業利用は厳禁**です。
3. コンテンツ制作者の権利を尊重し、ダウンロードした内容を商用配布しないでください。
4. 本ソフトウェアの使用により生じた一切の結果は、使用者自身が責任を負います。
5. 本ソフトウェアは機能の完全性と安定性を保証するものではありません。

</details>

<details>
<summary>🇰🇷 한국어</summary>

1. 본 소프트웨어는 **비공식** 미디어 다운로드 도구이며, 각 플랫폼 공식과는 아무런 관련이 없습니다.
2. 본 소프트웨어 및 소스코드는 **학습 및 교류 목적으로만 사용되며, 상업적 사용은 엄격히 금지**됩니다.
3. 콘텐츠 제작자의 권리를 존중하며, 다운로드한 내용을 상업적으로 배포하지 마십시오.
4. 본 소프트웨어 사용으로 발생한 모든 결과는 사용자가 책임집니다.
5. 본 소프트웨어는 기능의 완전성과 안정성을 보장하지 않습니다.

</details>

<details>
<summary>🇺🇸 English</summary>

1. This software is an **unofficial** media downloader and is not affiliated with any content platform.
2. This software and source code are **for learning and communication purposes only. Commercial use is strictly prohibited**.
3. Please respect content creators' rights; do not redistribute downloaded content commercially.
4. All consequences arising from the use of this software are borne by the user.
5. This software does not guarantee the completeness and stability of its features.

</details>

---

<p align="center">
    <sub>Original Author & Maintainer: <a href="https://github.com/min09577">min09577</a> | License: AGPL v3.0</sub>
</p>

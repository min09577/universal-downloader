# 📱 构建 Android APK

将万能下载器打包为 Android APK，安装到手机上使用。

---

## 🏗️ 方案概述

APK 基于 **Capacitor** 将 Web 前端包装为原生 Android 应用。工作模式：

```
[手机 APK] -- HTTP --> [PC 上的 Flask 后端] -- yt-dlp --> [下载视频/图片]
          <-- 文件回传 <--
```

> 手机和电脑需要在**同一局域网**下，或后端部署到云服务器。

---

## 📋 前置要求

### 必需
- [Node.js 18+](https://nodejs.org/)
- [Android Studio](https://developer.android.com/studio) (含 Android SDK)
- Java JDK 17+

### 环境变量

```bash
# Windows
set ANDROID_HOME=C:\Users\你的用户名\AppData\Local\Android\Sdk
set JAVA_HOME=C:\Program Files\Android\Android Studio\jbr

# Mac/Linux
export ANDROID_HOME=$HOME/Android/Sdk
export JAVA_HOME=/Applications/Android\ Studio.app/Contents/jbr/Contents/Home
```

### 验证环境
```bash
node --version   # >= 18
java --version   # >= 17
```

---

## 🚀 构建步骤

### 1. 安装 Node 依赖

```bash
cd android
npm install
```

### 2. 构建 Web 前端

```bash
node build-mobile.js
# 输出: android/dist/
```

### 3. 初始化 Capacitor Android 项目

```bash
npx cap init "万能下载器" "com.min0777.universaldownloader" --web-dir=dist
npx cap add android
```

### 4. 同步 Web 文件到 Android 项目

```bash
npx cap sync
```

### 5. 配置 Android 签名

创建 `android/keystore.properties`:
```properties
storeFile=../release.keystore
storePassword=你的密码
keyAlias=upload
keyPassword=你的密码
```

生成签名密钥（仅首次）:
```bash
keytool -genkey -v -keystore android/release.keystore -alias upload -keyalg RSA -keysize 2048 -validity 10000
```

### 6. 构建 APK

**Debug 版本（测试用）:**
```bash
cd android
./gradlew assembleDebug
# APK 在: android/app/build/outputs/apk/debug/app-debug.apk
```

**Release 版本（正式发布）:**
```bash
cd android
./gradlew assembleRelease
# APK 在: android/app/build/outputs/apk/release/app-release.apk
```

或者直接用 Android Studio 打开 `android/` 目录，点 Build → Build APK。

---

## 📲 使用方式

### 手机端

1. 安装 APK 到手机
2. 打开 App，顶部会显示服务器连接状态
3. 输入电脑的 IP 地址 + 端口（如 `http://192.168.1.100:5000`）
4. 电脑上启动 Flask 后端：`python app.py --host 0.0.0.0`
5. 粘贴链接即可下载

### 获取电脑 IP

- **Windows**: `ipconfig` 查看 IPv4 地址
- **Mac/Linux**: `ifconfig` 或 `ip addr`
- 确保防火墙允许 5000 端口

---

## 🎨 自定义

### 修改包名
编辑 `capacitor.config.ts` 中的 `appId`:
```ts
appId: 'com.yourcompany.yourapp',
```

### 修改应用名
```ts
appName: '你的应用名',
```

### 修改图标
替换 `android/app/src/main/res/` 下的图标文件，或用 Android Studio 的 Image Asset 工具生成。

---

## 🔧 故障排除

### gradlew 权限问题
```bash
chmod +x android/gradlew
```

### Android SDK 找不到
在 `android/local.properties` 中指定:
```
sdk.dir=C\:\\Users\\你的用户名\\AppData\\Local\\Android\\Sdk
```

### 构建失败 "SDK location not found"
创建 `android/local.properties`:
```
sdk.dir=/Users/你的用户名/Library/Android/sdk
```

### 应用闪退
- 检查手机和电脑是否在同一网络
- 确认防火墙未阻止 5000 端口
- 确认后端已启动且用 `--host 0.0.0.0`

---

## 📦 一键构建脚本

创建 `build-apk.sh` (Mac/Linux) 或 `build-apk.bat` (Windows):

**build-apk.bat (Windows):**
```bat
@echo off
cd android
call npm install
node build-mobile.js
call npx cap sync
cd android
call gradlew assembleDebug
echo APK 构建完成: android\app\build\outputs\apk\debug\app-debug.apk
pause
```

---

## ⚠️ 注意事项

1. APK 仅包含前端 UI，下载功能需要连接后端服务器
2. 首次安装需允许「安装未知来源应用」
3. Debug APK 不能上架 Google Play，需用 Release 版本
4. 如要发布，建议将后端部署到云服务器并配置 HTTPS

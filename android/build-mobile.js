/**
 * 万能下载器 - APK 构建脚本
 * 
 * 用法: node build-mobile.js
 * 
 * 此脚本将 Web 前端文件打包为 Capacitor 可用的格式
 * 构建后的文件放在 android/dist 目录
 */

const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname);
const STATIC_DIR = path.join(ROOT, '..', 'static');
const DIST_DIR = path.join(ROOT, 'dist');

// 确保目标目录存在
if (!fs.existsSync(DIST_DIR)) {
    fs.mkdirSync(DIST_DIR, { recursive: true });
}

// 复制 static 目录到 dist
function copyDir(src, dest) {
    if (!fs.existsSync(dest)) {
        fs.mkdirSync(dest, { recursive: true });
    }
    const entries = fs.readdirSync(src, { withFileTypes: true });
    for (const entry of entries) {
        const srcPath = path.join(src, entry.name);
        const destPath = path.join(dest, entry.name);
        if (entry.isDirectory()) {
            copyDir(srcPath, destPath);
        } else {
            fs.copyFileSync(srcPath, destPath);
        }
    }
}

console.log('[构建] 复制静态文件...');
copyDir(STATIC_DIR, path.join(DIST_DIR, 'static'));

// 复制配置文件
console.log('[构建] 复制移动端配置...');
fs.copyFileSync(
    path.join(ROOT, 'config.js'),
    path.join(DIST_DIR, 'static', 'js', 'config.js')
);

// 生成移动端优化的 index.html
console.log('[构建] 生成 index.html...');

// 读取原始 CSS 和 JS 引用
const indexHtml = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
    <title>万能下载器</title>
    <meta name="description" content="粘贴任意链接，自动识别并下载全网图片/视频">
    <meta name="theme-color" content="#4f6ef7">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="apple-mobile-web-app-title" content="万能下载器">
    <link rel="manifest" href="/static/manifest.json">
    <link rel="icon" type="image/png" sizes="192x192" href="/static/icons/icon-192.png">
    <link rel="apple-touch-icon" href="/static/icons/icon-192.png">
    <link rel="stylesheet" href="static/css/style.css">
    <style>
        /* 移动端额外样式 */
        .server-config-bar {
            background: var(--bg-card);
            border-bottom: 1px solid var(--border);
            padding: 8px 16px;
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 12px;
        }
        .server-config-bar input {
            flex: 1;
            padding: 6px 10px;
            background: var(--bg-input);
            border: 1px solid var(--border);
            border-radius: 6px;
            color: var(--text);
            font-size: 12px;
        }
        .server-config-bar button {
            padding: 6px 12px;
            background: var(--accent);
            color: white;
            border: none;
            border-radius: 6px;
            font-size: 12px;
            cursor: pointer;
        }
        .server-status {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #f87171;
            flex-shrink: 0;
        }
        .server-status.online {
            background: #34d399;
        }
    </style>
</head>
<body>
    <div class="app">
        <!-- 服务器配置栏（移动端专属） -->
        <div class="server-config-bar">
            <div class="server-status" id="serverStatus"></div>
            <input type="text" id="serverUrl" placeholder="服务器地址 http://192.168.x.x:5000" />
            <button onclick="saveServerUrl()">连接</button>
        </div>

        <!-- 头部 -->
        <header class="header">
            <h1>万能下载器</h1>
            <p class="subtitle">粘贴任意链接，自动识别并下载图片/视频</p>
        </header>

        <!-- 输入区 -->
        <div class="input-area">
            <div class="url-input-wrapper">
                <input
                    type="text"
                    id="urlInput"
                    placeholder="粘贴视频链接、帖子链接、图片链接..."
                    autocomplete="off"
                />
                <button id="analyzeBtn" class="btn-primary">
                    识别
                </button>
                <button id="downloadBtn" class="btn-download" disabled>
                    下载
                </button>
            </div>
            <div class="quick-tips">
                <span>支持: B站·抖音·YouTube·小红书·微博·Instagram 等 1000+</span>
            </div>
        </div>

        <!-- 分析结果 -->
        <div id="analyzeResult" class="result-panel hidden">
            <div class="result-header">
                <span id="resultType" class="type-badge"></span>
                <span id="resultPlatform" class="platform-badge"></span>
                <span id="resultTitle" class="result-title"></span>
            </div>
            <div id="imagePreview" class="image-preview hidden"></div>
        </div>

        <!-- 下载进度 -->
        <div id="progressPanel" class="progress-panel hidden">
            <div class="progress-bar-wrapper">
                <div id="progressBar" class="progress-bar"></div>
            </div>
            <div class="progress-info">
                <span id="progressText">准备中...</span>
                <span id="progressPercent">0%</span>
            </div>
            <div id="speedInfo" class="speed-info"></div>
        </div>

        <!-- 下载结果 -->
        <div id="resultPanel" class="result-panel hidden">
            <div class="result-success">
                <span>下载完成!</span>
            </div>
            <div id="resultFiles" class="result-files"></div>
        </div>

        <!-- 标签页 -->
        <div class="tabs">
            <button class="tab active" data-tab="history">下载历史</button>
            <button class="tab" data-tab="files">本地文件</button>
            <button class="tab" data-tab="stats">统计</button>
        </div>

        <!-- 历史记录 -->
        <div id="historyTab" class="tab-content">
            <div class="history-actions">
                <button id="clearHistoryBtn" class="btn-danger btn-small">清空记录</button>
            </div>
            <div id="historyList" class="history-list">
                <div class="empty-state">暂无下载记录，快去下载吧~</div>
            </div>
        </div>

        <!-- 文件列表 -->
        <div id="filesTab" class="tab-content hidden">
            <div id="filesList" class="files-list">
                <div class="empty-state">暂无下载文件</div>
            </div>
        </div>

        <!-- 统计 -->
        <div id="statsTab" class="tab-content hidden">
            <div id="statsContent" class="stats-grid"></div>
        </div>
    </div>

    <script src="static/js/config.js"></script>
    <script src="static/js/app-mobile.js"></script>
    <script>
        // 初始化服务器地址
        (function() {
            const savedUrl = localStorage.getItem('ud_server_url');
            if (savedUrl) {
                document.getElementById('serverUrl').value = savedUrl;
                APP_CONFIG.serverUrl = savedUrl;
            }
            checkServerStatus();
        })();

        function saveServerUrl() {
            const url = document.getElementById('serverUrl').value.trim();
            if (url) {
                localStorage.setItem('ud_server_url', url);
                APP_CONFIG.serverUrl = url;
                checkServerStatus();
            }
        }

        function checkServerStatus() {
            const statusEl = document.getElementById('serverStatus');
            fetch(APP_CONFIG.serverUrl + '/api/stats')
                .then(r => r.ok ? statusEl.classList.add('online') : statusEl.classList.remove('online'))
                .catch(() => statusEl.classList.remove('online'));
        }
    </script>
</body>
</html>`;

fs.writeFileSync(path.join(DIST_DIR, 'index.html'), indexHtml, 'utf-8');
console.log('[构建] 完成! 输出目录: ' + DIST_DIR);
console.log('[下一步] 运行: npm run cap:sync && npm run cap:open');

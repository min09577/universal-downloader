/**
 * 万能下载器 - 移动端交互逻辑
 * 通过 APP_CONFIG.serverUrl 连接后端
 */

function api(path, options = {}) {
    const baseUrl = (window.APP_CONFIG && APP_CONFIG.serverUrl) || 'http://localhost:5000';
    const url = baseUrl + path;
    return fetch(url, {
        headers: { 'Content-Type': 'application/json' },
        ...options,
    });
}

// ===== DOM 元素 =====
const urlInput = document.getElementById('urlInput');
const analyzeBtn = document.getElementById('analyzeBtn');
const downloadBtn = document.getElementById('downloadBtn');
const analyzeResult = document.getElementById('analyzeResult');
const resultType = document.getElementById('resultType');
const resultPlatform = document.getElementById('resultPlatform');
const resultTitle = document.getElementById('resultTitle');
const imagePreview = document.getElementById('imagePreview');
const progressPanel = document.getElementById('progressPanel');
const progressBar = document.getElementById('progressBar');
const progressText = document.getElementById('progressText');
const progressPercent = document.getElementById('progressPercent');
const speedInfo = document.getElementById('speedInfo');
const resultPanel = document.getElementById('resultPanel');
const resultFiles = document.getElementById('resultFiles');
const historyList = document.getElementById('historyList');
const filesListEl = document.getElementById('filesList');
const statsContent = document.getElementById('statsContent');
const clearHistoryBtn = document.getElementById('clearHistoryBtn');

let currentTaskId = null;
let pollTimer = null;
let currentUrl = '';
let currentType = '';

// ===== 事件监听 =====
analyzeBtn.addEventListener('click', analyzeUrl);
downloadBtn.addEventListener('click', startDownload);
clearHistoryBtn.addEventListener('click', clearHistory);
urlInput.addEventListener('keydown', (e) => { if (e.key === 'Enter') analyzeUrl(); });

// 粘贴自动触发
urlInput.addEventListener('paste', () => {
    setTimeout(() => {
        if (urlInput.value.trim() && urlInput.value.includes('http')) analyzeUrl();
    }, 100);
});

// 标签页
document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.add('hidden'));
        tab.classList.add('active');
        const n = tab.dataset.tab;
        document.getElementById(n + 'Tab').classList.remove('hidden');
        if (n === 'history') loadHistory();
        else if (n === 'files') loadFiles();
        else if (n === 'stats') loadStats();
    });
});

// ===== 核心功能 =====

async function analyzeUrl() {
    const url = urlInput.value.trim();
    if (!url) { showToast('请粘贴链接'); return; }
    resetUI();
    currentUrl = url;
    analyzeBtn.disabled = true;
    analyzeBtn.textContent = '识别中...';

    try {
        const resp = await api('/api/analyze', {
            method: 'POST',
            body: JSON.stringify({ url }),
        });
        const data = await resp.json();
        if (data.error) { showError(data.error); return; }

        currentType = data.detected_type;
        analyzeResult.classList.remove('hidden');
        const typeMap = { video: '视频', image: '图片', page: '网页' };
        resultType.textContent = typeMap[data.detected_type] || data.detected_type;
        resultType.className = 'type-badge ' + data.detected_type;
        resultPlatform.textContent = data.platform;
        resultTitle.textContent = data.title || url;

        if (data.images && data.images.length > 0) {
            imagePreview.classList.remove('hidden');
            imagePreview.innerHTML = '<h4>找到 ' + (data.total_images || data.images.length) + ' 张图片:</h4>' +
                '<div class="image-grid">' +
                data.images.map(img => '<img src="' + img.url + '" alt="' + img.filename + '" onerror="this.style.display=\'none\'" />').join('') +
                '</div>';
        }

        downloadBtn.disabled = false;
        downloadBtn.textContent = '开始下载';
    } catch (e) {
        showError('网络错误: ' + e.message);
    } finally {
        analyzeBtn.disabled = false;
        analyzeBtn.textContent = '识别';
    }
}

async function startDownload() {
    if (!currentUrl) return;
    downloadBtn.disabled = true;
    downloadBtn.textContent = '下载中...';
    resultPanel.classList.add('hidden');
    progressPanel.classList.remove('hidden');
    progressBar.style.width = '0%';
    progressText.textContent = '准备中...';
    progressPercent.textContent = '0%';
    speedInfo.textContent = '';

    try {
        const resp = await api('/api/download', {
            method: 'POST',
            body: JSON.stringify({ url: currentUrl, options: {} }),
        });
        const data = await resp.json();
        if (data.error) { showError(data.error); return; }
        currentTaskId = data.task_id;
        pollTimer = setInterval(pollProgress, 500);
    } catch (e) {
        showError('启动失败: ' + e.message);
    }
}

async function pollProgress() {
    if (!currentTaskId) return;
    try {
        const resp = await api('/api/task/' + currentTaskId);
        const data = await resp.json();
        progressBar.style.width = (data.progress || 0) + '%';
        progressPercent.textContent = (data.progress || 0).toFixed(1) + '%';
        progressText.textContent = data.message || '处理中...';
        if (data.speed_str) speedInfo.textContent = '速度: ' + data.speed_str;

        if (data.status === 'completed') {
            clearInterval(pollTimer);
            downloadBtn.disabled = true;
            downloadBtn.textContent = '下载完成';
            showResult(data.result);
            loadHistory();
        } else if (data.status === 'error') {
            clearInterval(pollTimer);
            downloadBtn.disabled = false;
            downloadBtn.textContent = '重试';
            showError(data.message);
        }
    } catch (e) { console.error('轮询失败:', e); }
}

function showResult(result) {
    resultPanel.classList.remove('hidden');
    if (result.files) {
        resultFiles.innerHTML = result.files.slice(0, 20).map(f =>
            '<div class="file-item"><span class="file-icon">🖼️</span>' +
            '<span class="file-name">' + f.filename + '</span>' +
            '<span class="file-size">' + f.size_kb + ' KB</span>' +
            '<a class="file-action" href="' + APP_CONFIG.serverUrl + '/downloads/' + f.filename + '" download>下载</a></div>'
        ).join('');
    } else if (result.filename) {
        resultFiles.innerHTML =
            '<div class="file-item"><span class="file-icon">🎬</span>' +
            '<span class="file-name">' + result.filename + '</span>' +
            '<span class="file-size">' + result.size_mb + ' MB</span>' +
            '<a class="file-action" href="' + APP_CONFIG.serverUrl + '/downloads/' + result.filename + '" download>下载</a></div>';
    }
}

// ===== 历史记录 =====
async function loadHistory() {
    try {
        const resp = await api('/api/history');
        const data = await resp.json();
        if (!data.length) { historyList.innerHTML = '<div class="empty-state">暂无记录</div>'; return; }

        historyList.innerHTML = data.map(item =>
            '<div class="history-item" onclick="reDownload(\'' + esc(item.url) + '\')">' +
            '<span class="h-type">' + (item.type === 'video' ? '🎬' : '🖼️') + '</span>' +
            '<div class="h-info"><div class="h-title">' + esc(item.title || item.url) + '</div>' +
            '<div class="h-meta">' + (item.platform || '') + ' · ' + (item.size_mb || item.count + '张') + ' · ' + fmtTime(item.time) + '</div></div>' +
            '<button class="h-action" onclick="event.stopPropagation();reDownload(\'' + esc(item.url) + '\')">重下</button></div>'
        ).join('');
    } catch (e) { historyList.innerHTML = '<div class="empty-state">加载失败</div>'; }
}

async function clearHistory() {
    if (!confirm('清空所有记录和文件?')) return;
    try {
        await api('/api/history', { method: 'DELETE' });
        historyList.innerHTML = '<div class="empty-state">已清空</div>';
        filesListEl.innerHTML = '<div class="empty-state">已清空</div>';
    } catch (e) { alert('清空失败'); }
}

function reDownload(url) {
    urlInput.value = url;
    currentUrl = url;
    analyzeUrl().then(() => setTimeout(startDownload, 500));
}

async function loadFiles() {
    try {
        const resp = await api('/api/files');
        const data = await resp.json();
        if (!data.length) { filesListEl.innerHTML = '<div class="empty-state">暂无文件</div>'; return; }
        filesListEl.innerHTML = data.map(f =>
            '<div class="file-item"><span class="file-icon">📄</span>' +
            '<span class="file-name">' + f.filename + '</span>' +
            '<span class="file-size">' + f.size_mb + ' MB</span>' +
            '<a class="file-action" href="' + APP_CONFIG.serverUrl + '/downloads/' + f.filename + '" download>下载</a></div>'
        ).join('');
    } catch (e) { filesListEl.innerHTML = '<div class="empty-state">加载失败</div>'; }
}

async function loadStats() {
    try {
        const resp = await api('/api/stats');
        const data = await resp.json();
        statsContent.innerHTML =
            '<div class="stat-card"><div class="stat-value">' + data.total_downloads + '</div><div class="stat-label">总下载</div></div>' +
            '<div class="stat-card"><div class="stat-value">' + data.video_count + '</div><div class="stat-label">视频</div></div>' +
            '<div class="stat-card"><div class="stat-value">' + data.image_count + '</div><div class="stat-label">图片</div></div>' +
            '<div class="stat-card"><div class="stat-value">' + data.disk_size_mb + ' MB</div><div class="stat-label">磁盘</div></div>';
    } catch (e) { statsContent.innerHTML = '<div class="empty-state">加载失败</div>'; }
}

function resetUI() {
    analyzeResult.classList.add('hidden');
    imagePreview.classList.add('hidden');
    imagePreview.innerHTML = '';
    progressPanel.classList.add('hidden');
    resultPanel.classList.add('hidden');
    resultFiles.innerHTML = '';
    progressBar.style.width = '0%';
    if (pollTimer) clearInterval(pollTimer);
    currentTaskId = null;
}

function showError(msg) {
    const el = document.querySelector('.error-message');
    if (el) el.remove();
    const d = document.createElement('div');
    d.className = 'error-message';
    d.textContent = '❌ ' + msg;
    analyzeResult.after(d);
    setTimeout(() => d.remove(), 8000);
}

function showToast(msg) {
    const t = document.createElement('div');
    t.style.cssText = 'position:fixed;top:20px;left:50%;transform:translateX(-50%);background:var(--bg-card);color:var(--text);padding:12px 24px;border-radius:8px;border:1px solid var(--border);z-index:9999;font-size:14px;';
    t.textContent = msg;
    document.body.appendChild(t);
    setTimeout(() => t.remove(), 2500);
}

function esc(s) { return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }

function fmtTime(iso) {
    if (!iso) return '';
    const d = new Date(iso);
    const diff = Date.now() - d;
    if (diff < 60000) return '刚刚';
    if (diff < 3600000) return Math.floor(diff/60000) + '分钟前';
    if (diff < 86400000) return Math.floor(diff/3600000) + '小时前';
    return d.toLocaleDateString('zh-CN');
}

loadHistory();

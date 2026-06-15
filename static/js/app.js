/**
 * 万能下载器 - 前端交互逻辑
 */

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
const openFolderBtn = document.getElementById('openFolderBtn');
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
openFolderBtn.addEventListener('click', () => alert('文件保存在项目的 downloads 文件夹中'));

// 回车键触发分析
urlInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') analyzeUrl();
});

// 粘贴事件自动触发分析
urlInput.addEventListener('paste', () => {
    setTimeout(() => {
        const url = urlInput.value.trim();
        if (url && url.includes('http')) {
            analyzeUrl();
        }
    }, 100);
});

// 标签页切换
document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.add('hidden'));
        tab.classList.add('active');
        const tabName = tab.dataset.tab;
        document.getElementById(tabName + 'Tab').classList.remove('hidden');
        if (tabName === 'history') loadHistory();
        else if (tabName === 'files') loadFiles();
        else if (tabName === 'stats') loadStats();
    });
});

// ===== 核心功能 =====

async function analyzeUrl() {
    const url = urlInput.value.trim();
    if (!url) {
        showToast('请先粘贴一个链接');
        return;
    }

    // 重置界面
    resetUI();
    currentUrl = url;

    analyzeBtn.disabled = true;
    analyzeBtn.innerHTML = '<span class="spinner"></span> 识别中...';

    try {
        const resp = await fetch('/api/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url }),
        });
        const data = await resp.json();

        if (data.error) {
            showError(data.error);
            return;
        }

        // 显示分析结果
        currentType = data.detected_type;
        analyzeResult.classList.remove('hidden');
        resultType.textContent = data.detected_type === 'video' ? '🎬 视频' :
            data.detected_type === 'image' ? '🖼️ 图片' : '📄 网页';
        resultType.className = 'type-badge ' + data.detected_type;
        resultPlatform.textContent = data.platform;
        resultTitle.textContent = data.title || url;

        // 图片预览
        if (data.images && data.images.length > 0) {
            imagePreview.classList.remove('hidden');
            imagePreview.innerHTML = `
                <h4>找到 ${data.total_images || data.images.length} 张图片:</h4>
                <div class="image-grid">
                    ${data.images.map(img => `
                        <img src="${img.url}" alt="${img.filename}" 
                             onerror="this.style.display='none'" 
                             title="${img.filename}" />
                    `).join('')}
                </div>
            `;
        }

        downloadBtn.disabled = false;
        downloadBtn.innerHTML = currentType === 'image'
            ? '<span class="icon">⬇️</span> 下载图片 (' + (data.total_images || data.images?.length || '?') + '张)'
            : '<span class="icon">⬇️</span> 开始下载';

        // 视频类型自动填入标题
        if (currentType === 'video') {
            resultTitle.textContent = data.platform + ' 视频';
        }

    } catch (e) {
        showError('网络错误: ' + e.message);
    } finally {
        analyzeBtn.disabled = false;
        analyzeBtn.innerHTML = '<span class="icon">🔍</span> 识别';
    }
}

async function startDownload() {
    if (!currentUrl) return;

    downloadBtn.disabled = true;
    downloadBtn.innerHTML = '<span class="spinner"></span> 下载中...';
    resultPanel.classList.add('hidden');
    progressPanel.classList.remove('hidden');
    progressBar.style.width = '0%';
    progressText.textContent = '准备中...';
    progressPercent.textContent = '0%';
    speedInfo.textContent = '';

    try {
        const resp = await fetch('/api/download', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: currentUrl, options: {} }),
        });
        const data = await resp.json();

        if (data.error) {
            showError(data.error);
            return;
        }

        currentTaskId = data.task_id;
        // 轮询进度
        pollTimer = setInterval(pollProgress, 500);

    } catch (e) {
        showError('启动下载失败: ' + e.message);
    }
}

async function pollProgress() {
    if (!currentTaskId) return;

    try {
        const resp = await fetch(`/api/task/${currentTaskId}`);
        const data = await resp.json();

        // 更新进度条
        progressBar.style.width = (data.progress || 0) + '%';
        progressPercent.textContent = (data.progress || 0).toFixed(1) + '%';
        progressText.textContent = data.message || '处理中...';

        if (data.speed_str) {
            speedInfo.textContent = '速度: ' + data.speed_str;
        }

        // 检查完成状态
        if (data.status === 'completed') {
            clearInterval(pollTimer);
            downloadBtn.disabled = true;
            downloadBtn.innerHTML = '<span class="icon">✅</span> 下载完成';
            showResult(data.result);
            loadHistory();
        } else if (data.status === 'error') {
            clearInterval(pollTimer);
            downloadBtn.disabled = false;
            downloadBtn.innerHTML = '<span class="icon">⬇️</span> 重试下载';
            showError(data.message);
        }

    } catch (e) {
        console.error('轮询失败:', e);
    }
}

function showResult(result) {
    resultPanel.classList.remove('hidden');

    if (result.files) {
        // 多文件（图片）
        resultFiles.innerHTML = result.files.slice(0, 20).map(f => `
            <div class="file-item">
                <span class="file-icon">🖼️</span>
                <span class="file-name">${f.filename}</span>
                <span class="file-size">${f.size_kb} KB</span>
                <a class="file-action" href="/downloads/${f.filename}" download>下载</a>
            </div>
        `).join('');
        if (result.files.length > 20) {
            resultFiles.innerHTML += `<div class="empty-state" style="padding:10px">还有 ${result.files.length - 20} 个文件...</div>`;
        }
    } else if (result.filename) {
        // 单文件（视频）
        resultFiles.innerHTML = `
            <div class="file-item">
                <span class="file-icon">🎬</span>
                <span class="file-name">${result.filename}</span>
                <span class="file-size">${result.size_mb} MB</span>
                <a class="file-action" href="/downloads/${result.filename}" download>下载</a>
            </div>
        `;
    }
}

// ===== 历史记录 =====

async function loadHistory() {
    try {
        const resp = await fetch('/api/history');
        const data = await resp.json();

        if (!data.length) {
            historyList.innerHTML = '<div class="empty-state">暂无下载记录，快去下载吧~</div>';
            return;
        }

        historyList.innerHTML = data.map(item => `
            <div class="history-item" onclick="reDownload('${escapeHtml(item.url)}')">
                <span class="h-type">${item.type === 'video' ? '🎬' : '🖼️'}</span>
                <div class="h-info">
                    <div class="h-title">${escapeHtml(item.title || item.url)}</div>
                    <div class="h-meta">
                        ${item.platform || ''} · ${item.size_mb || item.count + '张'} · ${formatTime(item.time)}
                    </div>
                </div>
                <button class="h-action" onclick="event.stopPropagation(); reDownload('${escapeHtml(item.url)}')">重新下载</button>
            </div>
        `).join('');
    } catch (e) {
        historyList.innerHTML = '<div class="empty-state">加载失败</div>';
    }
}

async function clearHistory() {
    if (!confirm('确定清空所有下载记录和文件?')) return;
    try {
        await fetch('/api/history', { method: 'DELETE' });
        historyList.innerHTML = '<div class="empty-state">已清空</div>';
        filesListEl.innerHTML = '<div class="empty-state">已清空</div>';
    } catch (e) {
        alert('清空失败');
    }
}

function reDownload(url) {
    urlInput.value = url;
    currentUrl = url;
    analyzeUrl().then(() => {
        setTimeout(startDownload, 500);
    });
}

// ===== 文件列表 =====

async function loadFiles() {
    try {
        const resp = await fetch('/api/files');
        const data = await resp.json();

        if (!data.length) {
            filesListEl.innerHTML = '<div class="empty-state">暂无下载文件</div>';
            return;
        }

        filesListEl.innerHTML = data.map(f => `
            <div class="file-item">
                <span class="file-icon">📄</span>
                <span class="file-name">${f.filename}</span>
                <span class="file-size">${f.size_mb} MB</span>
                <a class="file-action" href="/downloads/${f.filename}" download>下载</a>
            </div>
        `).join('');
    } catch (e) {
        filesListEl.innerHTML = '<div class="empty-state">加载失败</div>';
    }
}

// ===== 统计 =====

async function loadStats() {
    try {
        const resp = await fetch('/api/stats');
        const data = await resp.json();

        statsContent.innerHTML = `
            <div class="stat-card">
                <div class="stat-value">${data.total_downloads}</div>
                <div class="stat-label">总下载次数</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${data.video_count}</div>
                <div class="stat-label">视频数量</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${data.image_count}</div>
                <div class="stat-label">图片数量</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${data.disk_size_mb} MB</div>
                <div class="stat-label">磁盘占用</div>
            </div>
        `;
    } catch (e) {
        statsContent.innerHTML = '<div class="empty-state">加载失败</div>';
    }
}

// ===== 工具函数 =====

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
    const existing = document.querySelector('.error-message');
    if (existing) existing.remove();
    const errDiv = document.createElement('div');
    errDiv.className = 'error-message';
    errDiv.textContent = '❌ ' + msg;
    analyzeResult.after(errDiv);
    setTimeout(() => errDiv.remove(), 8000);
}

function showToast(msg) {
    const toast = document.createElement('div');
    toast.style.cssText = `
        position: fixed; top: 20px; left: 50%; transform: translateX(-50%);
        background: var(--bg-card); color: var(--text); padding: 12px 24px;
        border-radius: 8px; border: 1px solid var(--border); z-index: 9999;
        font-size: 14px; box-shadow: 0 4px 16px rgba(0,0,0,0.4);
    `;
    toast.textContent = msg;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 2500);
}

function escapeHtml(str) {
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;').replace(/'/g, '&#039;');
}

function formatTime(isoString) {
    if (!isoString) return '';
    try {
        const d = new Date(isoString);
        const now = new Date();
        const diff = now - d;
        if (diff < 60000) return '刚刚';
        if (diff < 3600000) return Math.floor(diff / 60000) + '分钟前';
        if (diff < 86400000) return Math.floor(diff / 3600000) + '小时前';
        return d.toLocaleDateString('zh-CN');
    } catch (e) {
        return '';
    }
}

// ===== 初始加载 =====
loadHistory();

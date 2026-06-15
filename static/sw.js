/**
 * 万能下载器 - Service Worker
 * 提供 PWA 离线缓存支持
 */

const CACHE_NAME = 'universal-downloader-v1';
const ASSETS_TO_CACHE = [
    '/',
    '/static/css/style.css',
    '/static/js/app.js',
    '/static/manifest.json',
];

// 安装：预缓存核心资源
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            console.log('[SW] 预缓存中...');
            return cache.addAll(ASSETS_TO_CACHE).catch((err) => {
                console.warn('[SW] 部分资源预缓存失败:', err);
            });
        })
    );
    // 立即激活
    self.skipWaiting();
});

// 激活：清理旧缓存
self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((keys) => {
            return Promise.all(
                keys.filter((key) => key !== CACHE_NAME)
                    .map((key) => caches.delete(key))
            );
        })
    );
    self.clients.claim();
});

// 拦截请求：网络优先，回退到缓存
self.addEventListener('fetch', (event) => {
    // 跳过 API 请求（不缓存）
    if (event.request.url.includes('/api/') ||
        event.request.url.includes('/downloads/')) {
        return;
    }

    event.respondWith(
        fetch(event.request)
            .then((response) => {
                // 缓存成功的 GET 请求
                if (event.request.method === 'GET' && response.status === 200) {
                    const cloned = response.clone();
                    caches.open(CACHE_NAME).then((cache) => {
                        cache.put(event.request, cloned);
                    });
                }
                return response;
            })
            .catch(() => {
                // 网络失败时使用缓存
                return caches.match(event.request);
            })
    );
});

// 推送通知
self.addEventListener('push', (event) => {
    const options = {
        body: event.data ? event.data.text() : '下载完成！',
        icon: '/static/icons/icon-192.png',
        badge: '/static/icons/icon-72.png',
        vibrate: [200, 100, 200],
    };
    event.waitUntil(
        self.registration.showNotification('万能下载器', options)
    );
});

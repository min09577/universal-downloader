/**
 * 万能下载器 - 移动端配置文件
 * 用于 Capacitor/APK 打包
 */

window.APP_CONFIG = {
    // 服务器地址 - 修改为你的服务器 IP 或域名
    // 本地开发: http://192.168.x.x:5000
    // 云端部署: https://your-domain.com
    serverUrl: localStorage.getItem('ud_server_url') || 'http://localhost:5000',
    appName: '万能下载器',
    version: '1.0.0',
};

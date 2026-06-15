import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.min0777.universaldownloader',
  appName: '万能下载器',
  webDir: 'dist',
  server: {
    // 允许 HTTP 明文请求（用于连接本地服务器）
    cleartext: true,
    androidScheme: 'https',
  },
  android: {
    allowMixedContent: true,
    buildOptions: {
      keystorePath: '',
      keystorePassword: '',
      keystoreAlias: '',
      keystoreAliasPassword: '',
    },
  },
  plugins: {
    Clipboard: {
      // 监听剪贴板变化，自动检测 URL
    },
    Share: {
      // 接收其他 App 分享的链接
    },
  },
};

export default config;

package com.min0777.universaldownloader

import android.annotation.SuppressLint
import android.os.Handler
import android.os.Looper
import android.webkit.CookieManager
import android.webkit.JavascriptInterface
import android.webkit.WebResourceRequest
import android.webkit.WebResourceResponse
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import java.io.ByteArrayInputStream
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicReference

/**
 * 抖音 share 页 WebView 渲染式解析（服务端 API 全被 Argus 拦，纯 Python 直链作废）。
 *
 * 原理：主线程创建隐藏 WebView 加载 share 页 → 字节 jsvmp 风控在真渲染环境放行 →
 * 三路捕获 video_id（v0xx 格式）：
 *   ① shouldInterceptRequest：aweme/v1/play 路径 query 里的 video_id=
 *      与 douyinvod 媒体 URL path 里的 v0xx 片段
 *   ② aweme/v1/web/aweme/detail JSON 响应里的 "uri":"v0xx"（注：argus 签名接口
 *      可能 4xx，捕获失败不阻塞其余两路）
 *   ③ evaluateJavascript 轮询 window._ROUTER_DATA 里的 playAddr / video slug
 * 拿到 video_id 后交 Python 走 aweme/v1/play 网关 302 直链（无需再回 WebView）。
 *
 * 线程约束：resolve() 禁止在主线程调用（内部阻塞等待，主线程调用会 ANR，
 * fail-fast 抛 IllegalStateException）；Python 侧经 Chaquopy 调用时运行在
 * Python 后台线程，内部 Handler(Looper.getMainLooper()) 投递 +
 * CountDownLatch 同步等待。超时兜底 25s（含页面加载+风控判定+XHR 时窗）。
 */
object DouyinWebViewResolver {

    private const val TAG = "DyResolver"
    private const val TIMEOUT_SECONDS = 25L

    private val mainHandler = Handler(Looper.getMainLooper())

    /** JS 桥：页面侧脚本无法注入时兜底（当前主要靠拦截/轮询，保留通道） */
    private class Bridge {
        @JavascriptInterface
        fun postVideoId(vid: String) {
            resultRef.compareAndSet(null, vid)
            latchRef.get()?.countDown()
        }
    }

    private val resultRef = AtomicReference<String?>(null)
    private val latchRef = AtomicReference<CountDownLatch?>(null)
    private val done = AtomicBoolean(false)
    private val destroyed = AtomicBoolean(false)

    /** 当前活跃的 WebView（resolve 期间挂主线程 Handler 的轮询引用它，cleanup 时一并回收） */
    @Volatile
    private var activeWebView: WebView? = null

    /**
     * 解析抖音分享链接/长链 → video_id（v0xx）。失败返回 null。
     * 调用线程不限（内部投递主线程）；阻塞至拿到结果或超时。
     */
    fun resolve(url: String): String? {
        if (Looper.myLooper() == Looper.getMainLooper()) {
            throw IllegalStateException("resolve() must not be called on main thread (would block UI)")
        }
        resultRef.set(null)
        done.set(false)
        destroyed.set(false)
        val latch = CountDownLatch(1)
        latchRef.set(latch)

        mainHandler.post {
            var webView: WebView? = null
            try {
                webView = createWebView()
                activeWebView = webView
                attachAndLoad(webView, url)
            } catch (t: Throwable) {
                android.util.Log.w(TAG, "webview setup failed: ${t.message}")
                latch.countDown()
            }
        }

        val ok = latch.await(TIMEOUT_SECONDS, TimeUnit.SECONDS)
        val vid = resultRef.get()
        android.util.Log.d(TAG, "resolve done=$ok vid=${vid?.take(24)}")
        // WebView 延迟销毁：latch 已放行，主线程异步回收，避免卡调用线程
        return if (vid != null && vid.startsWith("v0")) vid else null
    }

    @SuppressLint("SetJavaScriptEnabled")
    private fun createWebView(): WebView {
        val app = MyApp.instanceOrNull() ?: throw IllegalStateException("app not init")
        val wv = WebView(app)
        wv.layoutParams = android.view.ViewGroup.LayoutParams(0, 0)
        wv.alpha = 0f
        wv.visibility = android.view.View.INVISIBLE
        // 把 WebView 挂到 Activity ContentView 上才可渲染（0x0 + INVISIBLE 不影响 UI）
        (MainActivity.foregroundActivity?.window?.decorView as? android.view.ViewGroup)
            ?.addView(wv)
        wv.settings.apply {
            javaScriptEnabled = true
            domStorageEnabled = true
            userAgentString = "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Mobile Safari/537.36"
            cacheMode = WebSettings.LOAD_DEFAULT
            mixedContentMode = WebSettings.MIXED_CONTENT_ALWAYS_ALLOW
            blockNetworkImage = true   // 只求 JS 运行环境，图片全挡省流量
        }
        CookieManager.getInstance().setAcceptCookie(true)
        wv.addJavascriptInterface(Bridge(), "UDBridge")
        return wv
    }

    @SuppressLint("SetJavaScriptEnabled")
    private fun attachAndLoad(wv: WebView, url: String) {
        val main = Handler(Looper.getMainLooper())
        wv.webViewClient = object : WebViewClient() {
            override fun shouldInterceptRequest(
                view: WebView, request: WebResourceRequest
            ): WebResourceResponse? {
                val u = request.url
                val s = u.toString()
                if (!done.get()) {
                    // ① 拦截 aweme/v1/play 请求 query 里的 video_id（页面自动发起的播放网关调用）
                    if (s.contains("aweme/v1/play")) {
                        u.getQueryParameter("video_id")?.let { hit(it) }
                    }
                    // ② 仅 douyinvod 媒体 URL path 里含 v0xx 片段。
                    // 不纳入 douyinpic：其 path 同样含 v0 开头的封面/图片资源 id，
                    // first-hit-wins 下封面会抢先污染结果（play 校验失败 → yt-dlp 又被 Argus 拦 → 全链路失败）
                    if (s.contains("douyinvod.com")) {
                        VID_IN_PATH.findAll(s).firstOrNull()?.let { hit(it.value) }
                    }
                    // ③ detail 接口 query 带 aweme_id（说明页面在拉详情，配合 JS 轮询读响应）
                    if (s.contains("/aweme/v1/web/aweme/detail")) {
                        mainHandler.post { pollRouterData(view) }
                    }
                }
                return null
            }
        }
        wv.loadUrl(url)
        // 轮询兜底：页面若未自动触发播放请求，定时从 JS 环境抽 video_id。
        // cleanup() 会 removeCallbacks 取消 pending 轮询——防止 jsvmp 拖住主线程时，
        // 轮询对已 destroy 的 WebView 调 evaluateJavascript 抛 IllegalStateException 崩溃
        var tries = 0
        val poll = object : Runnable {
            override fun run() {
                if (done.get() || destroyed.get() || tries++ > 8) return
                pollRouterData(wv)
                mainHandler.postDelayed(this, 2500)
            }
        }
        mainHandler.postDelayed(poll, 3000)
    }

    private fun pollRouterData(wv: WebView) {
        if (done.get() || destroyed.get()) return
        try {
            wv.evaluateJavascript(
                "(function(){try{return (window._ROUTER_DATA&&JSON.stringify(window._ROUTER_DATA))||''}catch(e){return ''}})()",
            ) { json ->
                if (!done.get() && !json.isNullOrBlank() && json.length > 4) {
                    VID_IN_JSON.findAll(json).firstOrNull()?.let { hit(it.value) }
                }
            }
        } catch (t: Throwable) {
            // WebView 已销毁/非主线程等场景：轮询是兜底路径，吞掉即可
            android.util.Log.d(TAG, "poll skipped: ${t.message}")
        }
    }

    private fun hit(vid: String) {
        if (done.compareAndSet(false, true)) {
            resultRef.set(vid)
            latchRef.get()?.countDown()
        }
    }

    /** v0 开头的字节视频 id（uri/video_id 同构，全长度 30±） */
    private val VID_IN_PATH = Regex("/(v0[0-9a-zA-Z]{18,42})/")
    private val VID_IN_JSON = Regex("\\\\?\"(?:uri|video_id|vid)\\\\?\":\\\\?\"(v0[0-9a-zA-Z]{18,42})")

    /** resolve 完成后由调用方在合适时机触发 WebView 回收（避免泄漏） */
    fun cleanup() {
        destroyed.set(true)
        mainHandler.post {
            // 先摘掉引用并取消 pending 轮询，再销毁——次序不可反
            val wv = activeWebView
            activeWebView = null
            if (wv != null) {
                mainHandler.removeCallbacksAndMessages(null)
            }
            wv?.let {
                try {
                    it.stopLoading()
                    it.destroy()
                } catch (t: Throwable) {
                    android.util.Log.w(TAG, "webview destroy: ${t.message}")
                }
                (it.parent as? android.view.ViewGroup)?.removeView(it)
            }
        }
    }
}

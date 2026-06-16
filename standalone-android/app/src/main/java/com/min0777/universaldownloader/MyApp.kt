package com.min0777.universaldownloader

import android.app.Application
import android.os.Handler
import android.os.Looper
import android.webkit.CookieManager
import android.webkit.WebView
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit

class MyApp : Application() {
    companion object {
        lateinit var instance: MyApp
            private set

        /** 安全获取 cookies——在主线程执行 */
        @JvmStatic
        fun getCookiesSafe(domain: String): String {
            if (!::instance.isInitialized) return ""
            val latch = CountDownLatch(1)
            var result = ""
            Handler(Looper.getMainLooper()).post {
                try {
                    val cm = CookieManager.getInstance()
                    result = cm.getCookie("https://$domain") ?: ""
                } catch (_: Exception) { }
                latch.countDown()
            }
            try { latch.await(2, TimeUnit.SECONDS) } catch (_: Exception) { }
            return result
        }
    }

    override fun onCreate() {
        super.onCreate()
        instance = this
        // 初始化 WebView 引擎，激活 CookieManager
        try {
            WebView(this).destroy()
        } catch (_: Exception) { }
    }
}

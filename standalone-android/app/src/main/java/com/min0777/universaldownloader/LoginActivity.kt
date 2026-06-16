package com.min0777.universaldownloader

import android.annotation.SuppressLint
import android.os.Bundle
import android.view.View
import android.webkit.CookieManager
import android.webkit.WebChromeClient
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.ProgressBar
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity

class LoginActivity : AppCompatActivity() {

    private lateinit var webView: WebView
    private lateinit var progressBar: ProgressBar
    private lateinit var tvTitle: TextView
    private lateinit var btnDone: View

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_login)

        val platform = intent.getStringExtra("platform") ?: "bilibili"
        val loginUrl = getLoginUrl(platform)
        val title = getPlatformTitle(platform)

        webView = findViewById(R.id.webView)
        progressBar = findViewById(R.id.progressBar)
        tvTitle = findViewById(R.id.tvLoginTitle)
        btnDone = findViewById(R.id.btnLoginDone)

        tvTitle.text = title

        setupWebView(platform)
        webView.loadUrl(loginUrl)

        btnDone.setOnClickListener {
            val cookies = CookieManager.getInstance().getCookie(loginUrl) ?: ""
            if (cookies.isNotEmpty()) {
                Toast.makeText(this, "登录成功！Cookies 已保存", Toast.LENGTH_SHORT).show()
            }
            finish()
        }
    }

    @SuppressLint("SetJavaScriptEnabled")
    private fun setupWebView(platform: String) {
        CookieManager.getInstance().apply {
            setAcceptCookie(true)
            setAcceptThirdPartyCookies(webView, true)
        }

        webView.apply {
            settings.javaScriptEnabled = true
            settings.domStorageEnabled = true
            settings.userAgentString = getPlatformUA(platform)
            webViewClient = object : WebViewClient() {
                override fun onPageFinished(view: WebView, url: String) {
                    progressBar.visibility = View.GONE
                }
            }
            webChromeClient = object : WebChromeClient() {
                override fun onProgressChanged(view: WebView, newProgress: Int) {
                    progressBar.progress = newProgress
                }
            }
        }
    }

    private fun getLoginUrl(platform: String): String = when (platform) {
        "bilibili" -> "https://passport.bilibili.com/login"
        "xiaohongshu" -> "https://www.xiaohongshu.com/login"
        "douyin" -> "https://www.douyin.com"
        "weibo" -> "https://weibo.com/login.php"
        "kuaishou" -> "https://www.kuaishou.com"
        else -> "https://www.bilibili.com"
    }

    private fun getPlatformUA(platform: String): String = when (platform) {
        // 小红书用桌面UA，避免跳转App推广页
        "xiaohongshu" -> "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
        else -> "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Mobile Safari/537.36"
    }

    private fun getPlatformTitle(platform: String): String = when (platform) {
        "bilibili" -> "登录 B站"
        "xiaohongshu" -> "登录 小红书"
        "douyin" -> "登录 抖音"
        "weibo" -> "登录 微博"
        "kuaishou" -> "登录 快手"
        else -> "平台登录"
    }

    override fun onBackPressed() {
        if (webView.canGoBack()) {
            webView.goBack()
        } else {
            super.onBackPressed()
        }
    }
}

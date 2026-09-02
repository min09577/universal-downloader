package com.min0777.universaldownloader

import android.content.Intent
import android.net.Uri
import android.os.Build
import android.view.LayoutInflater
import android.view.View
import android.widget.TextView
import androidx.appcompat.app.AlertDialog
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

/**
 * 关于弹窗 + 检查更新
 * 仓库主页: https://github.com/min09577/universal-downloader
 * 最新版: https://github.com/min09577/universal-downloader/releases/latest
 */
object AboutBox {

    const val REPO_URL = "https://github.com/min09577/universal-downloader"
    const val LATEST_URL = "$REPO_URL/releases/latest"
    const val API_URL = "https://api.github.com/repos/min09577/universal-downloader/releases/latest"
    const val AUTHOR = "min09577"

    /** 开屏/关于 弹窗 */
    fun show(activity: MainActivity, isStartup: Boolean) {
        val view = LayoutInflater.from(activity).inflate(R.layout.dialog_about, null)
        val tvTag = view.findViewById<TextView>(R.id.tvAboutTag)
        tvTag.text = if (isStartup)
            "开源免费 · 喜欢请去 GitHub 点个 Star ⭐"
        else
            "本应用完全免费，请勿在任何付费渠道购买。"

        AlertDialog.Builder(activity)
            .setView(view)
            .setPositiveButton("去 GitHub ⭐") { _, _ -> open(activity, REPO_URL) }
            .setNeutralButton("检查更新") { _, _ -> checkUpdate(activity) }
            .setNegativeButton("关闭", null)
            .show()
    }

    /** 打开链接 */
    fun open(activity: MainActivity, url: String) {
        try {
            activity.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
        } catch (_: Exception) { }
    }

    /** 检查更新：比对 GitHub 最新 release 与本地 versionName */
    fun checkUpdate(activity: MainActivity) {
        val local = try {
            activity.packageManager.getPackageInfo(activity.packageName, 0).versionName ?: ""
        } catch (e: Exception) { "" }

        Thread {
            val latest = fetchLatest()
            activity.runOnUiThread {
                if (latest == null) {
                    android.widget.Toast.makeText(activity,
                        "无法连接 GitHub（网络受限，请稍后再试）", android.widget.Toast.LENGTH_LONG).show()
                    return@runOnUiThread
                }
                if (isNewer(latest, local)) {
                    AlertDialog.Builder(activity)
                        .setTitle("发现新版本 $latest")
                        .setMessage("当前版本 $local\n\n是否前往 Release 页面下载？")
                        .setPositiveButton("前往下载") { _, _ -> open(activity, LATEST_URL) }
                        .setNegativeButton("下次再说", null)
                        .show()
                } else {
                    android.widget.Toast.makeText(activity, "已是最新版本 ($local)", android.widget.Toast.LENGTH_SHORT).show()
                }
            }
        }.start()
    }

    /**
     * 获取最新版本号，双通道回退:
     *   1. api.github.com（国内常被限流/拦截）
     *   2. github.com releases/latest 302 跳转（最终 URL 含 tag 名，通常可达）
     * 全部失败返回 null。
     */
    private fun fetchLatest(): String? {
        // 通道1: REST API
        try {
            val conn = URL(API_URL).openConnection() as HttpURLConnection
            conn.connectTimeout = 8000
            conn.readTimeout = 8000
            conn.setRequestProperty("User-Agent", "OmniDL-App")
            val code = conn.responseCode
            android.util.Log.d(TAG, "api.github.com -> $code")
            if (code == 200) {
                val json = JSONObject(conn.inputStream.bufferedReader().readText())
                val tag = json.optString("tag_name", "")
                if (tag.isNotEmpty()) return tag
            }
        } catch (e: Exception) {
            android.util.Log.d(TAG, "api channel failed: ${e.message}")
        }
        // 通道2: releases/latest 重定向
        try {
            val conn = URL(LATEST_URL).openConnection() as HttpURLConnection
            conn.connectTimeout = 8000
            conn.readTimeout = 8000
            conn.instanceFollowRedirects = true
            conn.setRequestProperty("User-Agent", "Mozilla/5.0 (Linux; Android 14)")
            val code = conn.responseCode
            val finalUrl = conn.url.toString()
            android.util.Log.d(TAG, "github.com -> $code, final=$finalUrl")
            if (code in 200..399) {
                Regex("releases/tag/([^/?#]+)").find(finalUrl)?.groupValues?.get(1)?.let { return it }
            }
        } catch (e: Exception) {
            android.util.Log.d(TAG, "web channel failed: ${e.message}")
        }
        return null
    }

    private const val TAG = "OmniDL-Update"

    /** 语义化比较: ai.1.0.5 vs ai.1.0.4 → true。解析首个 ai. 前缀后的三段数字 */
    fun isNewer(remote: String, local: String): Boolean {
        fun nums(s: String): List<Int> =
            Regex("(\\d+)\\.(\\d+)\\.(\\d+)").find(s)?.destructured?.let { (a, b, c) -> listOf(a.toInt(), b.toInt(), c.toInt()) } ?: listOf(0, 0, 0)
        val r = nums(remote); val l = nums(local)
        return r[0] > l[0] || (r[0] == l[0] && r[1] > l[1]) ||
               (r[0] == l[0] && r[1] == l[1] && r[2] > l[2])
    }
}

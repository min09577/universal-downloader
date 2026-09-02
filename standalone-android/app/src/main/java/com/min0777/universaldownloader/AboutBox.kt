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

        // Release tag 形如 ai.1.0.4；本地 versionName 同格式
        Thread {
            var latest = ""
            var body = ""
            try {
                val conn = URL(API_URL).openConnection() as HttpURLConnection
                conn.connectTimeout = 8000
                conn.readTimeout = 8000
                conn.setRequestProperty("User-Agent", "OmniDL/$local")
                if (conn.responseCode == 200) {
                    val json = JSONObject(conn.inputStream.bufferedReader().readText())
                    latest = json.optString("tag_name", "")
                    body = json.optString("body", "").take(300)
                }
            } catch (_: Exception) { }

            activity.runOnUiThread {
                if (latest.isEmpty()) {
                    android.widget.Toast.makeText(activity, "网络异常，检查失败", Toast_SHORT).show()
                    return@runOnUiThread
                }
                if (isNewer(latest, local)) {
                    AlertDialog.Builder(activity)
                        .setTitle("发现新版本 $latest")
                        .setMessage("当前版本 $local\n\n$body")
                        .setPositiveButton("前往下载") { _, _ -> open(activity, LATEST_URL) }
                        .setNegativeButton("下次再说", null)
                        .show()
                } else {
                    android.widget.Toast.makeText(activity, "已是最新版本 ($local)", Toast_SHORT).show()
                }
            }
        }.start()
    }

    private val Toast_SHORT get() = android.widget.Toast.LENGTH_SHORT

    /** 语义化比较: ai.1.0.5 vs ai.1.0.4 → true。解析首个 ai. 前缀后的三段数字 */
    fun isNewer(remote: String, local: String): Boolean {
        fun nums(s: String): List<Int> =
            Regex("(\\d+)\\.(\\d+)\\.(\\d+)").find(s)?.destructured?.let { (a, b, c) -> listOf(a.toInt(), b.toInt(), c.toInt()) } ?: listOf(0, 0, 0)
        val r = nums(remote); val l = nums(local)
        return r[0] > l[0] || (r[0] == l[0] && r[1] > l[1]) ||
               (r[0] == l[0] && r[1] == l[1] && r[2] > l[2])
    }
}

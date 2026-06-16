package com.min0777.universaldownloader

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.os.Bundle
import android.view.View
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import com.min0777.universaldownloader.databinding.ActivityMainBinding
import com.min0777.universaldownloader.ui.DownloadAdapter
import com.min0777.universaldownloader.ui.HistoryItem
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.text.SimpleDateFormat
import java.util.*

class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
    private lateinit var adapter: DownloadAdapter
    private val historyItems = mutableListOf<HistoryItem>()
    private var isDownloading = false
    private val logLines = mutableListOf<String>()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)
        setupUI()
        loadHistory()
        addLog("=== 万能下载器启动 ===")
        handleSharedIntent()
    }

    // ========== 日志系统 ==========

    private fun addLog(msg: String) {
        val ts = SimpleDateFormat("HH:mm:ss", Locale.getDefault()).format(Date())
        val line = "[$ts] $msg"
        logLines.add(line)
        if (logLines.size > 200) logLines.removeAt(0)
        runOnUiThread {
            binding.tvLog.text = logLines.joinToString("\n")
            binding.scrollLog.post {
                binding.scrollLog.fullScroll(View.FOCUS_DOWN)
            }
        }
    }

    private fun copyLog() {
        val text = logLines.joinToString("\n")
        val clipboard = getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
        clipboard.setPrimaryClip(ClipData.newPlainText("log", text))
        Toast.makeText(this, "日志已复制 (${logLines.size} 行)", Toast.LENGTH_SHORT).show()
    }

    // ========== URL 提取 ==========

    /**
     * 从分享文本中提取纯净 URL
     * 抖音分享格式: "1.28 xxx 复制打开抖音极速版 https://v.douyin.com/xxx"
     * 小红书格式: "xxx http://xhslink.com/xxx 复制此链接..."
     */
    private fun extractUrl(text: String): String {
        // 方式1: 正则匹配 http/https URL
        val urlRegex = Regex("""https?://[^\s\u4e00-\u9fff]+""")
        val matches = urlRegex.findAll(text).toList()
        if (matches.isNotEmpty()) {
            // 取最长的匹配（通常是最完整的URL）
            val best = matches.maxByOrNull { it.value.length }!!
            addLog("URL提取: ${best.value}")
            return best.value.trimEnd('.', ',', ';', '!', '?', ')', ']', '}', '"', '\'')
        }

        // 方式2: 找 http 开头的子串
        val httpIdx = text.indexOf("http")
        if (httpIdx >= 0) {
            val sub = text.substring(httpIdx)
            val endIdx = sub.indexOf(' ').let { if (it < 0) sub.length else it }
            val raw = sub.substring(0, endIdx).trimEnd('.', ',', ';', '"')
            addLog("URL提取(fallback): $raw")
            return raw
        }

        addLog("URL提取失败，原文: $text")
        return text.trim()
    }

    // ========== UI 设置 ==========

    private fun setupUI() {
        adapter = DownloadAdapter(historyItems) { item ->
            binding.etUrl.setText(item.url)
            analyzeUrl(item.url)
        }
        binding.rvHistory.layoutManager = LinearLayoutManager(this)
        binding.rvHistory.adapter = adapter

        binding.btnAnalyze.setOnClickListener {
            val raw = binding.etUrl.text.toString().trim()
            if (raw.isNotEmpty()) {
                val url = extractUrl(raw)
                binding.etUrl.setText(url)
                analyzeUrl(url)
            }
        }

        binding.btnDownload.setOnClickListener {
            val raw = binding.etUrl.text.toString().trim()
            if (raw.isNotEmpty()) {
                val url = extractUrl(raw)
                binding.etUrl.setText(url)
                startDownload(url)
            }
        }

        binding.btnClearHistory.setOnClickListener {
            historyItems.clear()
            adapter.notifyDataSetChanged()
            saveHistory()
            binding.tvEmptyHistory.visibility = View.VISIBLE
        }

        binding.btnPaste.setOnClickListener {
            val clipboard = getSystemService(CLIPBOARD_SERVICE) as ClipboardManager
            val clip = clipboard.primaryClip
            if (clip != null && clip.itemCount > 0) {
                val text = clip.getItemAt(0).text?.toString() ?: ""
                val url = extractUrl(text)
                binding.etUrl.setText(url)
                analyzeUrl(url)
            }
        }

        binding.btnCopyLog.setOnClickListener { copyLog() }
        binding.btnClearLog.setOnClickListener {
            logLines.clear()
            binding.tvLog.text = "日志已清空"
        }
    }

    private fun handleSharedIntent() {
        if (intent?.action == android.content.Intent.ACTION_SEND) {
            intent.getStringExtra(android.content.Intent.EXTRA_TEXT)?.let { text ->
                addLog("收到分享: ${text.take(100)}...")
                val url = extractUrl(text)
                binding.etUrl.setText(url)
                analyzeUrl(url)
            }
        }
    }

    // ========== 核心功能 ==========

    private fun analyzeUrl(url: String) {
        if (isDownloading) return
        binding.progressBar.visibility = View.VISIBLE
        binding.layoutProgress.visibility = View.VISIBLE
        binding.tvProgress.text = "解析中..."
        binding.layoutResult.visibility = View.GONE

        addLog("---")
        addLog("开始分析: $url")

        lifecycleScope.launch {
            try {
                val result = withContext(Dispatchers.IO) {
                    // 先检测平台
                    val detect = PythonBridge.detectPlatform(url)
                    addLog("平台检测: platform=${detect.optString("platform")}, is_image=${detect.optBoolean("is_image")}")
                    // 再分析 URL
                    PythonBridge.analyzeUrl(url)
                }

                hideProgress()
                addLog("分析结果: success=${result.getBoolean("success")}, ${result.optString("error", "")}")

                if (result.getBoolean("success")) {
                    binding.tvResultTitle.text = result.optString("title", "未知")
                    binding.tvResultPlatform.text = "上传者: ${result.optString("uploader", "")}"
                    binding.layoutResult.visibility = View.VISIBLE
                    binding.btnDownload.isEnabled = true
                    binding.btnDownload.text = "下载视频"
                    addLog("✓ 识别成功: ${result.optString("title", "")}")
                } else if (result.optBoolean("is_image", false)) {
                    binding.tvResultTitle.text = "图片文件"
                    binding.tvResultPlatform.text = "直链图片"
                    binding.layoutResult.visibility = View.VISIBLE
                    binding.btnDownload.isEnabled = true
                    binding.btnDownload.text = "下载图片"
                    addLog("✓ 识别为图片直链")
                } else {
                    val errMsg = result.optString("error", "未知错误")
                    addLog("✗ 分析失败: $errMsg")
                    Toast.makeText(this@MainActivity, "识别失败，尝试提取网页图片...", Toast.LENGTH_SHORT).show()
                    tryExtractImages(url)
                }
            } catch (e: Exception) {
                hideProgress()
                addLog("✗ 分析异常: ${e.message}")
                addLog("堆栈: ${e.stackTraceToString().take(300)}")
                Toast.makeText(this@MainActivity, "异常: ${e.message}", Toast.LENGTH_LONG).show()
                tryExtractImages(url)
            }
        }
    }

    private fun tryExtractImages(url: String) {
        addLog("尝试提取网页图片...")
        lifecycleScope.launch {
            try {
                val result = withContext(Dispatchers.IO) {
                    PythonBridge.extractImages(url)
                }
                addLog("图片提取结果: success=${result.getBoolean("success")}, error=${result.optString("error", "")}")
                if (result.getBoolean("success")) {
                    val images = result.getJSONArray("images")
                    val total = result.getInt("total")
                    if (total > 0) {
                        binding.tvResultTitle.text = "找到 $total 张图片"
                        binding.tvResultPlatform.text = "网页图片提取"
                        binding.layoutResult.visibility = View.VISIBLE
                        binding.btnDownload.isEnabled = true
                        binding.btnDownload.text = "下载图片"
                        addLog("✓ 找到 $total 张图片")
                    } else {
                        addLog("✗ 未找到图片")
                        Toast.makeText(this@MainActivity, "页面中未找到图片", Toast.LENGTH_SHORT).show()
                    }
                } else {
                    val errMsg = result.optString("error", "未知错误")
                    addLog("✗ 图片提取失败: $errMsg")
                    Toast.makeText(this@MainActivity, "无法识别: $errMsg", Toast.LENGTH_LONG).show()
                }
            } catch (e: Exception) {
                addLog("✗ 图片提取异常: ${e.message}")
                Toast.makeText(this@MainActivity, "解析失败: ${e.message}", Toast.LENGTH_LONG).show()
            }
        }
    }

    private fun startDownload(url: String) {
        if (isDownloading) return
        isDownloading = true
        binding.progressBar.visibility = View.VISIBLE
        binding.layoutProgress.visibility = View.VISIBLE
        binding.tvProgress.text = "准备下载..."
        binding.tvSpeed.text = ""
        binding.btnDownload.isEnabled = false

        addLog("---")
        addLog("开始下载: $url")

        lifecycleScope.launch {
            try {
                val detect = withContext(Dispatchers.IO) { PythonBridge.detectPlatform(url) }
                addLog("下载类型: is_image=${detect.optBoolean("is_image")}")

                val result = withContext(Dispatchers.IO) {
                    if (detect.optBoolean("is_image", false))
                        PythonBridge.downloadImage(url)
                    else
                        PythonBridge.downloadVideo(url) { pct, speed ->
                            runOnUiThread {
                                binding.progressBar.progress = pct
                                binding.tvProgress.text = "$pct%"
                                binding.tvSpeed.text = speed
                            }
                        }
                }

                hideProgress()
                if (result.getBoolean("success")) {
                    val filename = result.getString("filename")
                    val sizeMb = result.getDouble("size_mb")
                    addLog("✓ 下载完成: $filename (${"%.1f".format(sizeMb)} MB)")
                    Toast.makeText(this@MainActivity, "完成! $filename (${"%.1f".format(sizeMb)} MB)", Toast.LENGTH_LONG).show()
                    addHistory(url, filename, sizeMb)
                } else {
                    addLog("✗ 下载失败: ${result.optString("error")}")
                    Toast.makeText(this@MainActivity, "失败: ${result.optString("error")}", Toast.LENGTH_LONG).show()
                }
            } catch (e: Exception) {
                hideProgress()
                addLog("✗ 下载异常: ${e.message}")
                Toast.makeText(this@MainActivity, "错误: ${e.message}", Toast.LENGTH_LONG).show()
            } finally {
                isDownloading = false
                binding.btnDownload.isEnabled = true
                binding.btnDownload.text = "下载"
            }
        }
    }

    private fun addHistory(url: String, filename: String, sizeMb: Double) {
        val item = HistoryItem(url = url, title = filename,
            size = "${"%.1f".format(sizeMb)} MB", time = System.currentTimeMillis())
        historyItems.add(0, item)
        if (historyItems.size > 100) historyItems.removeAt(historyItems.size - 1)
        adapter.notifyItemInserted(0)
        binding.tvEmptyHistory.visibility = View.GONE
        saveHistory()
    }

    private fun hideProgress() {
        binding.progressBar.visibility = View.GONE
        binding.layoutProgress.visibility = View.GONE
    }

    private fun saveHistory() {
        val json = org.json.JSONArray()
        historyItems.forEach { item ->
            val obj = JSONObject().apply {
                put("url", item.url); put("title", item.title)
                put("size", item.size); put("time", item.time)
            }
            json.put(obj)
        }
        getSharedPreferences("history", MODE_PRIVATE).edit().putString("items", json.toString()).apply()
    }

    private fun loadHistory() {
        val jsonStr = getSharedPreferences("history", MODE_PRIVATE).getString("items", "[]") ?: "[]"
        try {
            val json = org.json.JSONArray(jsonStr)
            for (i in 0 until json.length()) {
                val obj = json.getJSONObject(i)
                historyItems.add(HistoryItem(
                    obj.getString("url"), obj.getString("title"),
                    obj.getString("size"), obj.getLong("time")))
            }
            adapter.notifyDataSetChanged()
            binding.tvEmptyHistory.visibility = if (historyItems.isEmpty()) View.VISIBLE else View.GONE
        } catch (_: Exception) {}
    }
}

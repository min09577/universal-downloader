package com.min0777.universaldownloader

import android.content.ClipData
import android.content.ClipboardManager
import android.content.ContentValues
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Environment
import android.provider.MediaStore
import android.view.View
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.FileProvider
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import com.min0777.universaldownloader.databinding.ActivityMainBinding
import com.min0777.universaldownloader.ui.DownloadAdapter
import com.min0777.universaldownloader.ui.HistoryItem
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.io.File
import java.io.FileInputStream
import java.text.SimpleDateFormat
import java.util.*

class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
    private lateinit var adapter: DownloadAdapter
    private val historyItems = mutableListOf<HistoryItem>()
    private var isDownloading = false
    private val logLines = mutableListOf<String>()
    private var lastFilePath: String? = null
    private var lastDownloadUrl: String? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)
        setupUI()
        loadHistory()
        // 出处静默核验（不影响功能）
        SignatureMark.verify()
        // 动态版本号（ai.x.y.z 自带语义，不加 v 前缀）
        val verName = packageManager.getPackageInfo(packageName, 0).versionName ?: ""
        binding.tvVersion.text = verName
        // 作者徽章：点击直达仓库
        binding.tvAuthor.setOnClickListener { AboutBox.open(this, AboutBox.REPO_URL) }
        // ⚙ 关于入口（设置式）：仓库地址 / 检查更新 / 作者信息
        binding.btnSettings.setOnClickListener { AboutBox.show(this, isStartup = false) }
        addLog("=== 全能下载器 ${binding.tvVersion.text} 启动 ===")
        handleSharedIntent()
        // 开屏弹窗：展示仓库地址与作者，带「去 GitHub」「检查更新」入口
        binding.root.post {
            if (!isFinishing && !isDestroyed) AboutBox.show(this, isStartup = true)
        }
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
            // 点击历史项：如果有路径则打开文件，否则重新分析
            if (item.path != null && item.path.isNotEmpty()) {
                openFile(item.path)
            } else {
                binding.etUrl.setText(item.url)
                analyzeUrl(item.url)
            }
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
            // 如果刚下载完，按钮是"打开文件"
            if (binding.btnDownload.text == "📂 打开文件") {
                lastFilePath?.let { openFile(it) }
                return@setOnClickListener
            }
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

        // 平台登录按钮
        binding.btnLoginBilibili.setOnClickListener { openLogin("bilibili") }
        binding.btnLoginXhs.setOnClickListener { openLogin("xiaohongshu") }
        binding.btnLoginDouyin.setOnClickListener { openLogin("douyin") }
    }

    private fun openLogin(platform: String) {
        addLog("打开登录页: $platform")
        val intent = Intent(this, LoginActivity::class.java)
        intent.putExtra("platform", platform)
        startActivity(intent)
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
                    val imgCount = result.optInt("images_count", 0)
                    if (imgCount > 0) {
                        binding.tvResultTitle.text = result.optString("title", "小红书图文")
                        binding.tvResultPlatform.text = "小红书图文 · 共 ${imgCount} 张图片"
                        binding.btnDownload.text = "下载图片 (${imgCount}张)"
                    } else if (result.getBoolean("success") && result.optInt("formats_count", 0) > 0) {
                        binding.tvResultTitle.text = result.optString("title", "未知")
                        binding.tvResultPlatform.text = "上传者: ${result.optString("uploader", "")}"
                        binding.btnDownload.text = "下载视频"
                    } else {
                        binding.tvResultTitle.text = result.optString("title", "未知")
                        binding.tvResultPlatform.text = "上传者: ${result.optString("uploader", "")}"
                        binding.btnDownload.text = "下载视频"
                    }
                    binding.layoutResult.visibility = View.VISIBLE
                    binding.btnDownload.isEnabled = true
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

                    // 多图任务: files 数组逐个落盘; 单文件: path 直落
                    val tempFiles = mutableListOf<String>()
                    result.optJSONArray("files")?.let { arr ->
                        for (i in 0 until arr.length()) tempFiles.add(arr.getString(i))
                    }
                    if (tempFiles.isEmpty()) {
                        result.optString("path", "").takeIf { it.isNotEmpty() }?.let { tempFiles.add(it) }
                    }

                    val savedPath = withContext(Dispatchers.IO) {
                        // B站双轨: needs_remux → FFmpegKit 无损拼装（fMP4通吃）, MediaMuxer 兜底
                        if (result.optBoolean("needs_remux", false) && tempFiles.size >= 2) {
                            val baseName = filename.substringBeforeLast(" (").ifEmpty { "UD_bili" }
                            // 输出名必须与输入不同名(ffmpeg不能原地编辑): 加 _merged 后缀
                            val outPath = File(File(tempFiles[0]).parent, "${baseName}_merged.mp4").absolutePath
                            val merged = MediaMerger.remux(tempFiles[0], tempFiles[1], outPath) { pct, msg ->
                                runOnUiThread {
                                    binding.progressBar.progress = pct
                                    binding.tvProgress.text = "$pct%"
                                    binding.tvSpeed.text = msg
                                }
                            }
                            if (merged != null) {
                                addLog("✓ 音视频拼装完成: ${File(merged).name} (${File(merged).length()/1024/1024}MB)")
                                tempFiles.forEach { f -> runCatching { File(f).delete() } }
                                merged  // 合并产物直接作为唯一文件走 MediaStore 落盘
                            } else {
                                addLog("⚠ 拼装失败, 保留分离的视频文件")
                                null
                            }
                        } else null
                    } ?: withContext(Dispatchers.IO) {
                        if (tempFiles.size <= 1) {
                            tempFiles.firstOrNull()?.let { saveToMediaStore(it, filename) } ?: ""
                        } else {
                            // 多图: 每个临时文件按 "<显示名>_N.<真实扩展名>" 落盘
                            val firstPath = tempFiles.firstOrNull()?.let { saveToMediaStore(it, multiName(filename, 1)) } ?: ""
                            tempFiles.drop(1).forEachIndexed { idx, f ->
                                saveToMediaStore(f, multiName(filename, idx + 2))
                            }
                            firstPath
                        }
                    }

                    lastFilePath = savedPath
                    lastDownloadUrl = url
                    addLog("✓ 下载完成: $filename (${String.format("%.1f", sizeMb)} MB, ${tempFiles.size}个文件)")
                    addLog("   已保存到: $savedPath")
                    binding.tvResultTitle.text = "✅ $filename"
                    binding.tvResultPlatform.text = "${String.format("%.1f", sizeMb)} MB | 已保存"
                    binding.layoutResult.visibility = View.VISIBLE
                    binding.btnDownload.isEnabled = true
                    binding.btnDownload.text = "📂 打开文件"
                    addHistory(url, filename, savedPath, sizeMb)
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

    private fun addHistory(url: String, filename: String, filepath: String, sizeMb: Double) {
        val item = HistoryItem(url = url, title = filename, path = filepath,
            size = "${"%.1f".format(sizeMb)} MB", time = System.currentTimeMillis())
        historyItems.add(0, item)
        if (historyItems.size > 100) historyItems.removeAt(historyItems.size - 1)
        adapter.notifyItemInserted(0)
        binding.tvEmptyHistory.visibility = View.GONE
        saveHistory()
    }

    private fun openFile(path: String) {
        try {
            val file = File(path)
            if (!file.exists()) {
                Toast.makeText(this, "文件不存在: $path", Toast.LENGTH_LONG).show()
                addLog("文件不存在: $path")
                return
            }
            val uri = FileProvider.getUriForFile(this, "${packageName}.fileprovider", file)
            val mime = when {
                path.endsWith(".mp4") || path.endsWith(".mkv") || path.endsWith(".webm") -> "video/*"
                path.endsWith(".jpg") || path.endsWith(".jpeg") -> "image/jpeg"
                path.endsWith(".png") -> "image/png"
                path.endsWith(".gif") -> "image/gif"
                path.endsWith(".webp") -> "image/webp"
                else -> "*/*"
            }
            val intent = Intent(Intent.ACTION_VIEW).apply {
                setDataAndType(uri, mime)
                addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            }
            startActivity(Intent.createChooser(intent, "打开文件"))
        } catch (e: Exception) {
            addLog("打开文件失败: ${e.message}")
            Toast.makeText(this, "无法打开: ${e.message}", Toast.LENGTH_SHORT).show()
        }
    }

    private fun hideProgress() {
        binding.progressBar.visibility = View.GONE
        binding.layoutProgress.visibility = View.GONE
    }

    /**
     * 从显示名 "xxx (3张图)" 剥离统计后缀并拼出第 n 个文件名 "xxx_3.jpg"
     * (扩展名由 saveToMediaStore 按临时文件真实类型决定)
     */
    private fun multiName(displayName: String, n: Int): String {
        val base = displayName.replace(Regex("\\s*\\(\\d+张图\\)$"), "")
        return "${base}_$n"
    }

    /**
     * 通过 MediaStore 保存文件到系统 Downloads 目录（相册可见）
     */
    private fun saveToMediaStore(tempPath: String, displayName: String): String {
        val tempFile = File(tempPath)
        if (!tempFile.exists()) return tempPath

        try {
            // 真实扩展名优先取临时文件自身（Python 端按图片类型命名），显示名兜底
            val realExt = tempFile.extension.lowercase()
            val nameWithType = if (realExt.isNotEmpty()) "$displayName.$realExt" else displayName
            val mimeType = when {
                nameWithType.endsWith(".mp4") || nameWithType.endsWith(".mkv") || nameWithType.endsWith(".webm") -> "video/mp4"
                nameWithType.endsWith(".jpg") || nameWithType.endsWith(".jpeg") -> "image/jpeg"
                nameWithType.endsWith(".png") -> "image/png"
                nameWithType.endsWith(".gif") -> "image/gif"
                nameWithType.endsWith(".webp") -> "image/webp"
                else -> "application/octet-stream"
            }

            val values = ContentValues().apply {
                put(MediaStore.Downloads.DISPLAY_NAME, nameWithType)
                put(MediaStore.Downloads.MIME_TYPE, mimeType)
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                    put(MediaStore.Downloads.RELATIVE_PATH, Environment.DIRECTORY_DOWNLOADS)
                    put(MediaStore.Downloads.IS_PENDING, 1)
                }
            }

            val uri = contentResolver.insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, values)
                ?: return tempPath

            contentResolver.openOutputStream(uri)?.use { out ->
                FileInputStream(tempFile).use { inp -> inp.copyTo(out) }
            }

            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                values.clear()
                values.put(MediaStore.Downloads.IS_PENDING, 0)
                contentResolver.update(uri, values, null, null)
            }

            // 删除临时文件
            tempFile.delete()

            return "/sdcard/Download/$nameWithType"
        } catch (e: Exception) {
            addLog("MediaStore 保存失败: ${e.message}, 使用原始路径")
            return tempPath
        }
    }

    private fun saveHistory() {
        val json = org.json.JSONArray()
        historyItems.forEach { item ->
            val obj = JSONObject().apply {
                put("url", item.url); put("title", item.title)
                put("size", item.size); put("time", item.time)
                put("path", item.path)
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
                    obj.getString("size"), obj.getLong("time"),
                    obj.optString("path", "")))
            }
            adapter.notifyDataSetChanged()
            binding.tvEmptyHistory.visibility = if (historyItems.isEmpty()) View.VISIBLE else View.GONE
        } catch (_: Exception) {}
    }
}

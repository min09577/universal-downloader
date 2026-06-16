package com.min0777.universaldownloader

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

class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
    private lateinit var adapter: DownloadAdapter
    private val historyItems = mutableListOf<HistoryItem>()
    private var isDownloading = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)
        setupUI()
        loadHistory()
        handleSharedIntent()
    }

    private fun setupUI() {
        adapter = DownloadAdapter(historyItems) { item ->
            binding.etUrl.setText(item.url)
            analyzeUrl(item.url)
        }
        binding.rvHistory.layoutManager = LinearLayoutManager(this)
        binding.rvHistory.adapter = adapter

        binding.btnAnalyze.setOnClickListener {
            val url = binding.etUrl.text.toString().trim()
            if (url.isNotEmpty()) analyzeUrl(url)
        }

        binding.btnDownload.setOnClickListener {
            val url = binding.etUrl.text.toString().trim()
            if (url.isNotEmpty()) startDownload(url)
        }

        binding.btnClearHistory.setOnClickListener {
            historyItems.clear()
            adapter.notifyDataSetChanged()
            saveHistory()
            binding.tvEmptyHistory.visibility = View.VISIBLE
        }

        binding.btnPaste.setOnClickListener {
            val clipboard = getSystemService(CLIPBOARD_SERVICE) as android.content.ClipboardManager
            val clip = clipboard.primaryClip
            if (clip != null && clip.itemCount > 0) {
                val text = clip.getItemAt(0).text?.toString() ?: ""
                if (text.contains("http")) {
                    binding.etUrl.setText(text)
                    analyzeUrl(text)
                } else {
                    binding.etUrl.setText(text)
                }
            }
        }
    }

    private fun handleSharedIntent() {
        if (intent?.action == android.content.Intent.ACTION_SEND) {
            intent.getStringExtra(android.content.Intent.EXTRA_TEXT)?.let { text ->
                if (text.contains("http")) {
                    binding.etUrl.setText(text)
                    analyzeUrl(text)
                }
            }
        }
    }

    private fun analyzeUrl(url: String) {
        if (isDownloading) return
        binding.progressBar.visibility = View.VISIBLE
        binding.layoutProgress.visibility = View.VISIBLE
        binding.tvProgress.text = "解析中..."

        lifecycleScope.launch {
            try {
                val result = withContext(Dispatchers.IO) {
                    PythonBridge.analyzeUrl(url)
                }

                hideProgress()

                if (result.getBoolean("success")) {
                    // yt-dlp 成功识别
                    binding.tvResultTitle.text = result.optString("title", "未知")
                    binding.tvResultPlatform.text = "平台: ${result.optString("uploader", "")}"
                    binding.layoutResult.visibility = View.VISIBLE
                    binding.btnDownload.isEnabled = true
                    binding.btnDownload.text = "下载视频"
                } else if (result.optBoolean("is_image", false)) {
                    // 是图片直链
                    binding.tvResultTitle.text = "图片文件"
                    binding.tvResultPlatform.text = "直链图片"
                    binding.layoutResult.visibility = View.VISIBLE
                    binding.btnDownload.isEnabled = true
                    binding.btnDownload.text = "下载图片"
                } else {
                    // yt-dlp 无法识别，显示具体错误并尝试作为网页提取图片
                    val errMsg = result.optString("error", "未知错误")
                    Toast.makeText(this@MainActivity, "yt-dlp: $errMsg", Toast.LENGTH_LONG).show()
                    tryExtractImages(url)
                }
            } catch (e: Exception) {
                hideProgress()
                Toast.makeText(this@MainActivity, "解析异常: ${e.message}", Toast.LENGTH_LONG).show()
                tryExtractImages(url)
            }
        }
    }

    private fun tryExtractImages(url: String) {
        lifecycleScope.launch {
            try {
                val result = withContext(Dispatchers.IO) {
                    PythonBridge.extractImages(url)
                }
                if (result.getBoolean("success")) {
                    val images = result.getJSONArray("images")
                    val total = result.getInt("total")
                    if (total > 0) {
                        binding.tvResultTitle.text = "找到 $total 张图片"
                        binding.tvResultPlatform.text = "网页图片提取"
                        binding.layoutResult.visibility = View.VISIBLE
                        binding.btnDownload.isEnabled = true
                        binding.btnDownload.text = "下载图片"
                    } else {
                        Toast.makeText(this@MainActivity, "页面中未找到图片", Toast.LENGTH_SHORT).show()
                    }
                } else {
                    val errMsg = result.optString("error", "未知错误")
                    Toast.makeText(this@MainActivity, "无法识别该链接: $errMsg", Toast.LENGTH_LONG).show()
                }
            } catch (e: Exception) {
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

        lifecycleScope.launch {
            try {
                val detect = withContext(Dispatchers.IO) { PythonBridge.detectPlatform(url) }
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
                    Toast.makeText(this@MainActivity, "完成! $filename (${"%.1f".format(sizeMb)} MB)", Toast.LENGTH_LONG).show()
                    addHistory(url, filename, sizeMb)
                } else {
                    Toast.makeText(this@MainActivity, "失败: ${result.optString("error")}", Toast.LENGTH_LONG).show()
                }
            } catch (e: Exception) {
                hideProgress()
                Toast.makeText(this@MainActivity, "错误: ${e.message}", Toast.LENGTH_LONG).show()
            } finally {
                isDownloading = false
                binding.btnDownload.isEnabled = true
                binding.btnDownload.text = "下载"
            }
        }
    }

    private fun addHistory(url: String, filename: String, sizeMb: Double) {
        val item = HistoryItem(url = url, title = filename, size = "${"%.1f".format(sizeMb)} MB", time = System.currentTimeMillis())
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
                historyItems.add(HistoryItem(obj.getString("url"), obj.getString("title"), obj.getString("size"), obj.getLong("time")))
            }
            adapter.notifyDataSetChanged()
            binding.tvEmptyHistory.visibility = if (historyItems.isEmpty()) View.VISIBLE else View.GONE
        } catch (_: Exception) {}
    }
}

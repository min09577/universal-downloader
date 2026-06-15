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
import java.io.File

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

        // 接收其他 App 分享的链接
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

        // 粘贴板监听
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
            val sharedText = intent.getStringExtra(android.content.Intent.EXTRA_TEXT)
            if (sharedText != null && sharedText.contains("http")) {
                binding.etUrl.setText(sharedText)
                analyzeUrl(sharedText)
            }
        }
    }

    private fun analyzeUrl(url: String) {
        if (isDownloading) return

        showLoading("正在解析链接...")
        lifecycleScope.launch {
            try {
                val result = withContext(Dispatchers.IO) {
                    PythonBridge.analyzeUrl(url)
                }

                hideLoading()

                if (result.getBoolean("success")) {
                    val title = result.optString("title", "未知")
                    val platform = PythonBridge.detectPlatform(url)

                    binding.tvResultTitle.text = title
                    binding.tvResultPlatform.text = "平台: $platform"
                    binding.layoutResult.visibility = View.VISIBLE
                    binding.btnDownload.isEnabled = true
                    binding.btnDownload.text = "⬇ 下载视频"
                } else if (result.optBoolean("is_image", false)) {
                    binding.tvResultTitle.text = "图片文件"
                    binding.tvResultPlatform.text = "直链图片"
                    binding.layoutResult.visibility = View.VISIBLE
                    binding.btnDownload.isEnabled = true
                    binding.btnDownload.text = "⬇ 下载图片"
                } else {
                    Toast.makeText(this@MainActivity, "无法识别该链接", Toast.LENGTH_SHORT).show()
                }
            } catch (e: Exception) {
                hideLoading()
                // yt-dlp 失败就尝试提取图片
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
                    binding.tvResultTitle.text = "找到 $total 张图片"
                    binding.tvResultPlatform.text = "网页图片提取"
                    binding.layoutResult.visibility = View.VISIBLE
                    binding.btnDownload.isEnabled = true
                    binding.btnDownload.text = "⬇ 下载 ($total 张)"
                } else {
                    Toast.makeText(this@MainActivity, "解析失败: ${result.optString("error")}", Toast.LENGTH_LONG).show()
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
        binding.btnDownload.isEnabled = false

        lifecycleScope.launch {
            try {
                // 先检测是否为图片直链
                val detectResult = withContext(Dispatchers.IO) {
                    PythonBridge.detectPlatform(url)
                }

                val result: JSONObject
                if (detectResult.optBoolean("is_image", false)) {
                    result = withContext(Dispatchers.IO) {
                        PythonBridge.downloadImage(url)
                    }
                } else {
                    // 视频下载带进度回调
                    result = withContext(Dispatchers.IO) {
                        PythonBridge.downloadVideo(url) { percent, speed ->
                            runOnUiThread {
                                binding.progressBar.progress = percent
                                binding.tvProgress.text = "下载中... $percent%"
                                binding.tvSpeed.text = speed
                            }
                        }
                    }
                }

                hideLoading()

                if (result.getBoolean("success")) {
                    val filename = result.getString("filename")
                    val sizeMb = result.getDouble("size_mb")
                    Toast.makeText(
                        this@MainActivity,
                        "下载完成! $filename (${"%.1f".format(sizeMb)} MB)",
                        Toast.LENGTH_LONG
                    ).show()

                    // 添加到历史
                    addHistory(url, filename, sizeMb)
                } else {
                    Toast.makeText(
                        this@MainActivity,
                        "下载失败: ${result.optString("error")}",
                        Toast.LENGTH_LONG
                    ).show()
                }
            } catch (e: Exception) {
                hideLoading()
                Toast.makeText(this@MainActivity, "下载失败: ${e.message}", Toast.LENGTH_LONG).show()
            } finally {
                isDownloading = false
                binding.btnDownload.isEnabled = true
                binding.btnDownload.text = "⬇ 下载"
            }
        }
    }

    private fun addHistory(url: String, filename: String, sizeMb: Double) {
        val item = HistoryItem(
            url = url,
            title = filename,
            size = "${"%.1f".format(sizeMb)} MB",
            time = System.currentTimeMillis()
        )
        historyItems.add(0, item)
        if (historyItems.size > 100) historyItems.removeAt(historyItems.size - 1)
        adapter.notifyItemInserted(0)
        binding.tvEmptyHistory.visibility = View.GONE
        saveHistory()
    }

    private fun showLoading(msg: String) {
        binding.progressBar.visibility = View.VISIBLE
        binding.layoutProgress.visibility = View.VISIBLE
        binding.tvProgress.text = msg
        binding.tvSpeed.text = ""
    }

    private fun hideLoading() {
        binding.progressBar.visibility = View.GONE
        binding.layoutProgress.visibility = View.GONE
    }

    private fun saveHistory() {
        val prefs = getSharedPreferences("history", MODE_PRIVATE)
        val json = org.json.JSONArray()
        historyItems.forEach { item ->
            val obj = JSONObject()
            obj.put("url", item.url)
            obj.put("title", item.title)
            obj.put("size", item.size)
            obj.put("time", item.time)
            json.put(obj)
        }
        prefs.edit().putString("items", json.toString()).apply()
    }

    private fun loadHistory() {
        val prefs = getSharedPreferences("history", MODE_PRIVATE)
        val jsonStr = prefs.getString("items", "[]") ?: "[]"
        try {
            val json = org.json.JSONArray(jsonStr)
            for (i in 0 until json.length()) {
                val obj = json.getJSONObject(i)
                historyItems.add(
                    HistoryItem(
                        url = obj.getString("url"),
                        title = obj.getString("title"),
                        size = obj.getString("size"),
                        time = obj.getLong("time")
                    )
                )
            }
            adapter.notifyDataSetChanged()
            binding.tvEmptyHistory.visibility = if (historyItems.isEmpty()) View.VISIBLE else View.GONE
        } catch (e: Exception) {
            binding.tvEmptyHistory.visibility = View.VISIBLE
        }
    }
}

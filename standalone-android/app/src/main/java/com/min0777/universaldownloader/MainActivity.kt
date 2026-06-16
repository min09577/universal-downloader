package com.min0777.universaldownloader

import android.os.Bundle
import android.view.View
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.min0777.universaldownloader.databinding.ActivityMainBinding

class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        setupUI()
    }

    private fun setupUI() {
        binding.btnAnalyze.setOnClickListener {
            val url = binding.etUrl.text.toString().trim()
            if (url.isNotEmpty()) {
                binding.tvResultTitle.text = "链接: $url"
                binding.tvResultPlatform.text = "平台: 待识别"
                binding.layoutResult.visibility = View.VISIBLE
                Toast.makeText(this, "链接已识别", Toast.LENGTH_SHORT).show()
            }
        }

        binding.btnDownload.setOnClickListener {
            Toast.makeText(this, "下载功能开发中...", Toast.LENGTH_SHORT).show()
        }

        binding.btnClearHistory.setOnClickListener {
            binding.tvEmptyHistory.visibility = View.VISIBLE
        }

        binding.btnPaste.setOnClickListener {
            val clipboard = getSystemService(CLIPBOARD_SERVICE) as android.content.ClipboardManager
            val clip = clipboard.primaryClip
            if (clip != null && clip.itemCount > 0) {
                val text = clip.getItemAt(0).text?.toString() ?: ""
                binding.etUrl.setText(text)
            }
        }
    }
}

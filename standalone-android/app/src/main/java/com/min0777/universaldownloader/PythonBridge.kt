package com.min0777.universaldownloader

import android.content.Context
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform
import org.json.JSONObject

/**
 * Python 桥接层
 * 通过 Chaquopy 调用 downloader.py 中的函数
 */
object PythonBridge {

    private var initialized = false

    fun init(context: Context) {
        if (!initialized) {
            if (!Python.isStarted()) {
                Python.start(AndroidPlatform(context))
            }
            initialized = true
        }
    }

    private fun getModule() = Python.getInstance().getModule("downloader")

    /**
     * 分析 URL 获取视频信息
     */
    fun analyzeUrl(url: String): JSONObject {
        init(MyApp.instance)
        val result = getModule().callAttr("analyze_url", url).toString()
        return JSONObject(result)
    }

    /**
     * 下载视频
     */
    fun downloadVideo(url: String, onProgress: ((Int, String) -> Unit)? = null): JSONObject {
        init(MyApp.instance)
        val result = getModule().callAttr("download_video", url, null).toString()
        return JSONObject(result)
    }

    /**
     * 下载单张图片
     */
    fun downloadImage(url: String): JSONObject {
        init(MyApp.instance)
        val result = getModule().callAttr("download_image", url).toString()
        return JSONObject(result)
    }

    /**
     * 从网页提取图片列表
     */
    fun extractImages(url: String): JSONObject {
        init(MyApp.instance)
        val result = getModule().callAttr("extract_images_from_page", url).toString()
        return JSONObject(result)
    }

    /**
     * 检测平台和 URL 类型
     */
    fun detectPlatform(url: String): JSONObject {
        init(MyApp.instance)
        val result = getModule().callAttr("detect_platform", url).toString()
        return JSONObject(result)
    }
}

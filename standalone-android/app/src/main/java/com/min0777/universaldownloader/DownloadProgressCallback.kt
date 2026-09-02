package com.min0777.universaldownloader

/**
 * Python → Kotlin 下载进度回调接口（函数式接口，Chaquopy 可直接以 Python callable 调用）
 * pct: 0-100 百分比；speed: 速度描述文本（可为空串）
 * 注意: 调用发生在 Python 后台线程，实现侧需自行切 UI 线程
 */
interface DownloadProgressCallback {
    fun onProgress(pct: Int, speed: String)
}

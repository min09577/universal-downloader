package com.min0777.universaldownloader.bili

/**
 * B站 gRPC 拉流结果：仅保留下载所需字段。
 */
data class BiliStreamResult(
    val quality: Int,
    val format: String,
    val durationMs: Long,
    val videoUrls: List<String>,
    val audioUrls: List<String>,
    val videoCodecs: List<String>,
    val videoBandwidths: List<Long>,
    val videoSizes: List<Long>,
    val needVip: Boolean,
    val errCode: Int,
) {
    val isUsable: Boolean get() = videoUrls.isNotEmpty() && !needVip && errCode == 0
}

/**
 * 从 gRPC 响应提取视频/音频直链，清理试看与 vip 限制标记。
 * targetQn > 0 时仅接受该清晰度的流（避免低清流被当作目标画质返回）。
 */
fun bilibili.playershared.VodInfo.toStreamResult(targetQn: Int = 0): BiliStreamResult {
    val videos = mutableListOf<String>()
    val codecs = mutableListOf<String>()
    val bandwidths = mutableListOf<Long>()
    val sizes = mutableListOf<Long>()
    for (stream in streamListList) {
        val info = stream.streamInfo
        // need_vip / 限制条件：清理掉不可用的流
        if (info.needVip || info.needLogin || info.errCode != 0) continue
        if (targetQn > 0 && info.quality.toInt() != targetQn) continue
        val dash = stream.dashVideo
        if (dash == null) continue
        if (dash.baseUrl.isBlank()) continue
        videos.add(dash.baseUrl)
        codecs.add(dash.codecid.toString())
        bandwidths.add(dash.bandwidth.toLong())
        sizes.add(dash.size)
    }
    val audios = dashAudioList
        .filter { it.baseUrl.isNotBlank() }
        .map { it.baseUrl }
    return BiliStreamResult(
        quality = quality.toInt(),
        format = format,
        durationMs = timelength.toLong(),
        videoUrls = videos,
        audioUrls = audios,
        videoCodecs = codecs,
        videoBandwidths = bandwidths,
        videoSizes = sizes,
        // 仅当一条可用流都没拿到、且响应里存在 VIP 限制流时才判 needVip
        //（免费+VIP 混合响应里 VIP 流不应抹掉已拿到的免费流）
        needVip = videos.isEmpty() && streamListList.any { it.streamInfo.needVip },
        errCode = if (streamListList.isEmpty()) 1 else 0,
    )
}

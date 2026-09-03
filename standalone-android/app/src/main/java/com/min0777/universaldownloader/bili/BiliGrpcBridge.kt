package com.min0777.universaldownloader.bili

import com.google.gson.Gson
import io.grpc.Status
import io.grpc.StatusRuntimeException

/**
 * Python downloader.py 与 Kotlin gRPC 栈之间的桥。
 * 拉流结果以 Gson JSON 返回，字段见 get4kStreams。
 *
 * TODO(BROKEN): 当前 gRPC 路径休眠，勿启用——Python 侧已改走 web playurl（SESSDATA Cookie）。
 * 本类签名中的 accessKey 参数曾误用 WebView SESSDATA 填充；按 chairman 拍板方案，
 * metadata.proto 的 access_key 应留空，鉴权改走 authorization:ident Cookie 头，
 * 且需真实 App access_key 或抓包确认后才能启用。启用前必须重做鉴权，勿直接回退 downloader.py。
 */
object BiliGrpcBridge {

    private val gson = Gson()

    @JvmStatic
    fun get4kStreams(
        aid: Long,
        cid: Long,
        qn: Int,
        accessKey: String,
        buvid: String,
    ): String {
        return try {
            val app = com.min0777.universaldownloader.MyApp.instanceOrNull()
                ?: return errorJson("app 未初始化")
            BiliGrpcClient(context = app, accessKey = accessKey).use { client ->
                val vod = kotlinx.coroutines.runBlocking {
                    client.playViewUnite(aid = aid, cid = cid, qn = qn)
                }
                val result = vod.toStreamResult(targetQn = qn)
                val payload: Map<String, Any> = linkedMapOf(
                    "success" to result.isUsable,
                    "quality" to result.quality,
                    "format" to result.format,
                    "duration_ms" to result.durationMs,
                    "video_urls" to result.videoUrls,
                    "audio_urls" to result.audioUrls,
                    "video_codecs" to result.videoCodecs,
                    "video_bandwidths" to result.videoBandwidths,
                    "video_sizes" to result.videoSizes,
                    "need_vip" to result.needVip,
                    "error" to (if (result.isUsable) "" else "流不可用(need_vip=${result.needVip})"),
                    "buvid" to buvid,
                )
                gson.toJson(payload)
            }
        } catch (e: StatusRuntimeException) {
            errorJson("gRPC ${e.status.code}: ${e.status.description ?: ""}")
        } catch (e: Exception) {
            errorJson("gRPC 拉流失败: ${e.message ?: e.javaClass.simpleName}")
        }
    }

    private fun errorJson(msg: String): String =
        Gson().toJson(linkedMapOf("success" to false, "error" to msg))
}

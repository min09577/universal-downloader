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
        sessdata: String,
        buvid: String,
    ): String {
        return try {
            val app = com.min0777.universaldownloader.MyApp.instanceOrNull()
                ?: return errorJson("app 未初始化")
            // 休眠路径：SESSDATA/buvid3 以 cookie 头携带（metadata.access_key 留空）
            val cookieHeader = buildString {
                if (sessdata.isNotBlank()) append("SESSDATA=").append(sessdata)
                if (buvid.isNotBlank()) {
                    if (isNotEmpty()) append("; ")
                    append("buvid3=").append(buvid)
                }
            }
            BiliGrpcClient(context = app, accessKey = "", cookieHeader = cookieHeader).use { client ->
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

    /**
     * gRPC 试看机制真机实验：以匿名身份（access_key 留空 + identify_v1 + cookie）
     * 请求 qn=120/fnval=4048/download=0，回传 quality、每条 stream 的
     * quality/need_vip/base_url 有无、qn_trial_info 全文，验证漫游 X 机制能否复刻。
     */
    @JvmStatic
    fun testTrial(aid: Long, cid: Long): String {
        val tag = "BiliGrpcTest"
        fun log(msg: String) { android.util.Log.i(tag, msg) }
        return try {
            val app = com.min0777.universaldownloader.MyApp.instanceOrNull()
                ?: return errorJson("app 未初始化").also { log(it) }
            val buvid = BiliMetadataFactory.buvid(app)
            val cookieHeader = "buvid3=$buvid"
            log("testTrial begin aid=$aid cid=$cid buvid=$buvid auth=identify_v1+'' cookie=$cookieHeader")
            // 匿名实验：access_key 真正留空串（绝不把 cookie 串塞进 access_key）；
            // authorization 头由 Interceptor 注入 "identify_v1 " + ""；buvid3 同时走 cookie 头与 metadata.buvid 字段
            BiliGrpcClient(context = app, accessKey = "", cookieHeader = cookieHeader).use { client ->
                val reply = kotlinx.coroutines.runBlocking {
                    // 直接走 stub 层拿完整 Reply（含 qn_trial_info），不复用 playViewUnite（只回 vod_info）
                    val req = bilibili.app.playerunite.v1.PlayViewUniteReq.newBuilder()
                        .setVod(
                            bilibili.playershared.VideoVod.newBuilder()
                                .setAid(aid)
                                .setCid(cid)
                                .setQn(120L)
                                .setFnval(4048)
                                .setDownload(0)
                                .setForceHost(2)
                                .setFourk(true)
                                .build()
                        )
                        .setSpmid("0")
                        .setFromSpmid("0")
                        .build()
                    val stub = bilibili.app.playerunite.v1.PlayerGrpcKt.PlayerCoroutineStub(client.rawChannel)
                        .withInterceptors(BiliMetadataInterceptor(app, "", cookieHeader))
                    stub.playViewUnite(req)
                }
                val vod = reply.vodInfo
                val streams = vod.streamListList.map { s ->
                    linkedMapOf(
                        "quality" to s.streamInfo.quality.toInt(),
                        "need_vip" to s.streamInfo.needVip,
                        "need_login" to s.streamInfo.needLogin,
                        "err_code" to s.streamInfo.errCode.toInt(),
                        "has_base_url" to (s.hasDashVideo() && s.dashVideo.baseUrl.isNotBlank()),
                        "base_url_len" to (if (s.hasDashVideo()) s.dashVideo.baseUrl.length else 0),
                        "format" to s.streamInfo.format,
                        "new_description" to s.streamInfo.newDescription,
                    )
                }
                val trial = reply.qnTrialInfo
                val payload: Map<String, Any> = linkedMapOf(
                    "success" to true,
                    "vod_quality" to vod.quality.toInt(),
                    "stream_count" to streams.size,
                    "streams" to streams,
                    "qn120_has_url" to streams.any { it["quality"] == 120 && it["has_base_url"] == true },
                    "qn_trial_info" to linkedMapOf(
                        "trial_able" to trial.trialAble,
                        "remaining_times" to trial.remainingTimes,
                        "start" to trial.start,
                        "time_length" to trial.timeLength,
                        "has_start_toast" to trial.hasStartToast(),
                        "has_end_toast" to trial.hasEndToast(),
                    ),
                )
                val json = gson.toJson(payload)
                log("testTrial result: $json")
                json
            }
        } catch (e: StatusRuntimeException) {
            log("testTrial gRPC error: ${e.status.code} ${e.status.description}")
            errorJson("gRPC ${e.status.code}: ${e.status.description ?: ""}")
        } catch (e: Exception) {
            log("testTrial error: ${e.javaClass.simpleName}: ${e.message}")
            errorJson("gRPC 拉流失败: ${e.message ?: e.javaClass.simpleName}")
        }
    }
}

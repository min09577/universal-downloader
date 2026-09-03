package com.min0777.universaldownloader.bili

import bilibili.app.playerunite.v1.PlayViewUniteReq
import bilibili.playershared.CodeType
import bilibili.playershared.VideoVod
import io.grpc.ManagedChannel
import io.grpc.okhttp.OkHttpChannelBuilder
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/**
 * B站 gRPC 客户端：grpc.biliapi.net:443 TLS，统一播放接口 PlayViewUnite。
 * 依赖 gRPC-Kotlin 协程 stub。
 */
class BiliGrpcClient(
    private val context: android.content.Context?,
    private val accessKey: String,
) : AutoCloseable {

    private val channel: ManagedChannel by lazy {
        OkHttpChannelBuilder.forAddress(HOST, PORT)
            .useTransportSecurity()
            .build()
    }

    private val coroutineStub by lazy {
        bilibili.app.playerunite.v1.PlayerGrpcKt.PlayerCoroutineStub(channel)
            .withInterceptors(BiliMetadataInterceptor(context, accessKey))
    }

    /**
     * 拉取统一播放流信息。
     * qn: 清晰度（120=4K）；fnval: 16=DASH；download=2 为 dash 下载模式。
     */
    suspend fun playViewUnite(
        aid: Long,
        cid: Long,
        qn: Int,
        fnval: Int = 16,
        download: Int = 2,
        fourk: Boolean = true,
        preferCodecType: CodeType = CodeType.NOCODE,
    ): bilibili.playershared.VodInfo = withContext(Dispatchers.IO) {
        val req = PlayViewUniteReq.newBuilder()
            .setVod(
                VideoVod.newBuilder()
                    .setAid(aid)
                    .setCid(cid)
                    .setQn(qn.toLong())
                    .setFnver(0)
                    .setFnval(fnval)
                    .setDownload(download)
                    .setForceHost(2) // 强制 https
                    .setFourk(fourk)
                    .setPreferCodecType(preferCodecType)
                    .build()
            )
            .setSpmid("0")
            .setFromSpmid("0")
            .build()
        coroutineStub.playViewUnite(req).vodInfo
    }

    override fun close() {
        channel.shutdown()
    }

    companion object {
        const val HOST = "grpc.biliapi.net"
        const val PORT = 443
    }
}

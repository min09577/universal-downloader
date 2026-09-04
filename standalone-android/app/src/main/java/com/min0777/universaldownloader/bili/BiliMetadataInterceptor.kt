package com.min0777.universaldownloader.bili

import io.grpc.CallOptions
import io.grpc.Channel
import io.grpc.ClientCall
import io.grpc.ClientInterceptor
import io.grpc.ForwardingClientCall
import io.grpc.ForwardingClientCallListener
import io.grpc.Metadata
import io.grpc.MethodDescriptor

/**
 * gRPC 客户端拦截器：注入 B站要求的四个二进制元数据头 + authorization 鉴权头。
 *
 * authorization 是独立 gRPC ASCII 头（非 proto 字段、非 -bin 头）：
 * 值格式 "identify_v1 " + access_key（匿名实验时 access_key 传空串）。
 * cookieHeader 可选：经 cookie ASCII 头透传 buvid3/SESSDATA（grpc-okhttp 原样发送）。
 */
class BiliMetadataInterceptor(
    private val context: android.content.Context?,
    private val accessKey: String,
    private val cookieHeader: String = "",
) : ClientInterceptor {

    companion object {
        // B站自研头：raw byte 透传（-bin 后缀由 gRPC 处理）
        val METADATA_BIN: Metadata.Key<ByteArray> =
            Metadata.Key.of("x-bili-metadata-bin", Metadata.BINARY_BYTE_MARSHALLER)
        val DEVICE_BIN: Metadata.Key<ByteArray> =
            Metadata.Key.of("x-bili-device-bin", Metadata.BINARY_BYTE_MARSHALLER)
        val LOCALE_BIN: Metadata.Key<ByteArray> =
            Metadata.Key.of("x-bili-locale-bin", Metadata.BINARY_BYTE_MARSHALLER)
        val NETWORK_BIN: Metadata.Key<ByteArray> =
            Metadata.Key.of("x-bili-network-bin", Metadata.BINARY_BYTE_MARSHALLER)

        // 鉴权 ASCII 头："identify_v1 " + access_key
        val AUTHORIZATION: Metadata.Key<String> =
            Metadata.Key.of("authorization", Metadata.ASCII_STRING_MARSHALLER)

        // 可选 cookie 头
        val COOKIE: Metadata.Key<String> =
            Metadata.Key.of("cookie", Metadata.ASCII_STRING_MARSHALLER)
    }

    override fun <ReqT : Any, RespT : Any> interceptCall(
        method: MethodDescriptor<ReqT, RespT>,
        callOptions: CallOptions,
        next: Channel,
    ): ClientCall<ReqT, RespT> {
        val headers = Metadata().apply {
            put(METADATA_BIN, BiliMetadataFactory.buildMetadata(context, accessKey).toByteArray())
            put(DEVICE_BIN, BiliMetadataFactory.buildDevice(context).toByteArray())
            put(LOCALE_BIN, BiliMetadataFactory.buildLocale().toByteArray())
            put(NETWORK_BIN, BiliMetadataFactory.buildNetwork(context).toByteArray())
            put(AUTHORIZATION, "identify_v1 $accessKey")
            if (cookieHeader.isNotBlank()) {
                put(COOKIE, cookieHeader)
            }
        }
        return object : ForwardingClientCall.SimpleForwardingClientCall<ReqT, RespT>(next.newCall(method, callOptions)) {
            override fun start(
                responseListener: Listener<RespT>,
                requestHeaders: Metadata,
            ) {
                requestHeaders.merge(headers)
                super.start(responseListener, requestHeaders)
            }
        }
    }
}

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
 * gRPC 客户端拦截器：为每个请求注入 B站要求的四个二进制元数据头。
 */
class BiliMetadataInterceptor(
    private val context: android.content.Context?,
    private val accessKey: String,
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

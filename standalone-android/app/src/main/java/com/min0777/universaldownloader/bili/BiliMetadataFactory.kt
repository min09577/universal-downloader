package com.min0777.universaldownloader.bili

import android.content.Context
import android.os.Build
import android.provider.Settings
import bilibili.metadata.Metadata
import bilibili.metadata.device.Device
import bilibili.metadata.locale.Locale
import bilibili.metadata.locale.LocaleIds
import bilibili.metadata.network.Network
import bilibili.metadata.network.NetworkType
import bilibili.metadata.network.TFType
import java.util.UUID

/**
 * B站 gRPC 请求元数据工厂：组装 x-bili-metadata-bin / x-bili-device-bin /
 * x-bili-locale-bin / x-bili-network-bin 四个二进制头。
 *
 * fp_local / fts 按官方语义采集（首启生成并持久化于 SharedPreferences），
 * buvid3 优先沿用浏览器 cookie 真实值。
 */
object BiliMetadataFactory {

    // 与官方 android 客户端一致的版本标识
    private const val MOBI_APP = "android"
    private const val PLATFORM = "android"
    private const val BUILD = 7380300
    private const val VERSION_NAME = "7.38.0"
    private const val CHANNEL = "master"

    // buvid3：沿用浏览器 cookie 里的真实值；无登录态时用稳定随机值兜底
    @Volatile
    private var cachedBuvid: String? = null

    /** 从 WebView cookie 存储读取真实 buvid3（登录过 B站主站即有） */
    fun fetchBuvidFromCookies(): String? {
        return try {
            val cookies = com.min0777.universaldownloader.MyApp.getCookiesSafe("bilibili.com")
            cookies.split(";")
                .map { it.trim() }
                .firstOrNull { it.startsWith("buvid3=") }
                ?.substringAfter("buvid3=")
                ?.takeIf { it.isNotBlank() }
        } catch (_: Exception) {
            null
        }
    }

    fun buvid(context: Context? = null): String {
        cachedBuvid?.let { return it }
        val buvid = fetchBuvidFromCookies()
            ?: context?.let { ctx ->
                // 无 cookie 时从设备稳定标识派生，保证同设备稳定
                val androidId = Settings.Secure.getString(ctx.contentResolver, Settings.Secure.ANDROID_ID) ?: "0"
                "XX" + UUID.nameUUIDFromBytes(androidId.toByteArray()).toString().replace("-", "").uppercase()
            }
            ?: "XX" + UUID.randomUUID().toString().replace("-", "").uppercase()
        cachedBuvid = buvid
        return buvid
    }

    /** fp_local：官方语义为首启生成的 32 位十六进制随机指纹，持久化同设备稳定 */
    private const val KEY_FP_LOCAL = "fp_local"

    fun fpLocal(context: Context?): String {
        val ctx = context ?: return UUID.randomUUID().toString().replace("-", "")
        val prefs = ctx.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        prefs.getString(KEY_FP_LOCAL, null)?.let { return it }
        val fp = UUID.randomUUID().toString().replace("-", "")
        prefs.edit().putString(KEY_FP_LOCAL, fp).apply()
        return fp
    }

    /** fp_remote：多数场景与 fp_local 同值即可 */
    fun fpRemote(context: Context?): String = fpLocal(context)

    /** fts：官方语义为首启时间戳，存 SharedPreferences 同设备稳定 */
    private const val PREFS_NAME = "bili_fingerprint"
    private const val KEY_FIRST_LAUNCH_TS = "first_launch_ts"

    fun fts(context: Context?): Long {
        val ctx = context ?: return System.currentTimeMillis()
        val prefs = ctx.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        val saved = prefs.getLong(KEY_FIRST_LAUNCH_TS, -1L)
        if (saved > 0) return saved
        val now = System.currentTimeMillis()
        prefs.edit().putLong(KEY_FIRST_LAUNCH_TS, now).apply()
        return now
    }

    fun buildMetadata(context: Context?, accessKey: String): Metadata =
        Metadata.newBuilder()
            .setAccessKey(accessKey)
            .setMobiApp(MOBI_APP)
            .setDevice(Build.MODEL)
            .setBuild(BUILD)
            .setChannel(CHANNEL)
            .setBuvid(buvid(context))
            .setPlatform(PLATFORM)
            .build()

    fun buildDevice(context: Context?): Device =
        Device.newBuilder()
            .setAppId(1)
            .setBuild(BUILD)
            .setBuvid(buvid(context))
            .setMobiApp(MOBI_APP)
            .setPlatform(PLATFORM)
            .setDevice(Build.MODEL)
            .setChannel(CHANNEL)
            .setBrand(Build.BRAND)
            .setModel(Build.MODEL)
            .setOsver(Build.VERSION.RELEASE)
            .setFpLocal(fpLocal(context))
            .setFpRemote(fpRemote(context))
            .setVersionName(VERSION_NAME)
            .setFp(fpLocal(context))
            .setFts(fts(context))
            .build()

    fun buildLocale(): Locale =
        Locale.newBuilder()
            .setCLocale(
                LocaleIds.newBuilder()
                    .setLanguage("zh")
                    .setScript("Hans")
                    .setRegion("CN")
            )
            .setSLocale(
                LocaleIds.newBuilder()
                    .setLanguage("zh")
                    .setScript("Hans")
                    .setRegion("CN")
            )
            .setTimezone("Asia/Shanghai")
            .build()

    fun buildNetwork(context: Context?): Network =
        Network.newBuilder()
            .setType(detectNetworkType(context))
            .setTf(TFType.TF_UNKNOWN)
            .setOid("")
            .build()

    private fun detectNetworkType(context: Context?): NetworkType {
        if (context == null) return NetworkType.WIFI
        return try {
            val cm = context.getSystemService(Context.CONNECTIVITY_SERVICE) as android.net.ConnectivityManager
            val caps = cm.getNetworkCapabilities(cm.activeNetwork)
            when {
                caps == null -> NetworkType.OFFLINE
                caps.hasTransport(android.net.NetworkCapabilities.TRANSPORT_WIFI) ->
                    NetworkType.WIFI
                caps.hasTransport(android.net.NetworkCapabilities.TRANSPORT_CELLULAR) ->
                    NetworkType.CELLULAR
                caps.hasTransport(android.net.NetworkCapabilities.TRANSPORT_ETHERNET) ->
                    NetworkType.ETHERNET
                else -> NetworkType.OTHERNET
            }
        } catch (_: Exception) {
            NetworkType.WIFI
        }
    }
}

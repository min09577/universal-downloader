package com.min0777.universaldownloader

import javax.crypto.Cipher
import javax.crypto.spec.SecretKeySpec

/**
 * 内部校验模块 — 防篡改 / 出处核验
 *
 * 标记以 AES 加密存储，运行时解密比对；明文不出现在代码与常量池中。
 * 校验失败不影响功能，仅打内部标记（silent sentinel）。
 */
object SignatureMark {

    // 分段密钥（静态分析需跨两处拼合）
    private val K1 = byteArrayOf(0x4D, 0x6F, 0x37, 0x37, 0x35, 0x37, 0x37, 0x21)
    private val K2 = byteArrayOf(0x23, 0x4F, 0x6D, 0x6E, 0x69, 0x44, 0x4C, 0x40)

    // 分段存储的加密标记
    private val S1 = "8f3a1c5e7b9d2f40".toByteArray()
    private val S2 = "a6c8e0d24b6f8913".toByteArray()

    private fun key(): SecretKeySpec {
        val full = ByteArray(16)
        K1.copyInto(full, 0)
        K2.copyInto(full, 8)
        return SecretKeySpec(full, "AES")
    }

    private fun dec(data: ByteArray, ivSeed: Byte): String = try {
        val cipher = Cipher.getInstance("AES/CTR/NoPadding")
        cipher.init(Cipher.DECRYPT_MODE, key(), javax.crypto.spec.IvParameterSpec(ByteArray(16) { ivSeed }))
        String(cipher.doFinal(data), Charsets.UTF_8).trim('\u0000')
    } catch (e: Exception) { "" }

    /** 解出的标记串（仅供内部比对） */
    fun mark(): String = dec(S1, 0x11) + dec(S2, 0x22)

    /** 静默校验：调用侧不感知结果 */
    fun verify(): Boolean = mark().isNotEmpty() && mark().hashCode() == 0x2F4A1C
}

package com.min0777.universaldownloader

import android.media.MediaExtractor
import android.media.MediaMuxer
import com.arthenica.ffmpegkit.FFmpegKit
import com.arthenica.ffmpegkit.FFmpegKitConfig
import com.arthenica.ffmpegkit.ReturnCode
import java.io.File

/**
 * B 站双轨拼装器
 *
 * 主路径: FFmpegKit(-c copy) —— 无损 remux, fMP4/B站分片格式通吃
 * 降级:  MediaMuxer     —— 系统API, 只支持普通MP4; 失败时保底
 *
 * @param onProgress (pct 0-100, 文本) 合并阶段的进度（按输出文件估算不可行, 用时间脉冲上报）
 */
object MediaMerger {

    /**
     * @return 成功返回输出文件路径, 失败 null
     */
    fun remux(videoPath: String, audioPath: String, outPath: String,
              onProgress: ((Int, String) -> Unit)? = null): String? {
        onProgress?.invoke(5, "拼装中...")
        // 1) FFmpegKit 无损合并（fMP4 OK）
        val (ok, sessionLog) = runCatching {
            val session = FFmpegKit.execute(
                "-y -i \"${escape(videoPath)}\" -i \"${escape(audioPath)}\" " +
                "-c copy -movflags +faststart -map 0:v:0 -map 1:a:0 \"${escape(outPath)}\""
            )
            val logs = session.allLogsAsString?.take(1500) ?: ""
            Pair(ReturnCode.isSuccess(session.returnCode), logs)
        }.getOrElse { e ->
            Pair(false, "EXC: ${e.message}")
        }
        android.util.Log.d("OmniDL-Merge", "ffmpeg rc=$ok log=$sessionLog")
        if (ok && File(outPath).length() > 0) {
            onProgress?.invoke(100, "完成")
            return outPath
        }
        onProgress?.invoke(50, "尝试系统拼装...")
        // 2) MediaMuxer 降级
        val fallback = remuxViaMediaMuxer(videoPath, audioPath, outPath)
        if (fallback != null) {
            onProgress?.invoke(100, "完成")
            return fallback
        }
        return null
    }

    private fun escape(p: String) = p.replace("\\", "\\\\").replace("\"", "\\\"")

    private fun remuxViaMediaMuxer(videoPath: String, audioPath: String, outPath: String): String? {
        val videoExtractor = MediaExtractor()
        val audioExtractor = MediaExtractor()
        var muxer: MediaMuxer? = null
        try {
            videoExtractor.setDataSource(videoPath)
            audioExtractor.setDataSource(audioPath)

            var videoTrack = -1
            for (i in 0 until videoExtractor.trackCount) {
                if (videoExtractor.getTrackFormat(i).getString("mime")?.startsWith("video/") == true) {
                    videoTrack = i; break
                }
            }
            var audioTrack = -1
            for (i in 0 until audioExtractor.trackCount) {
                if (audioExtractor.getTrackFormat(i).getString("mime")?.startsWith("audio/") == true) {
                    audioTrack = i; break
                }
            }
            if (videoTrack < 0 || audioTrack < 0) return null

            val vFmt = videoExtractor.getTrackFormat(videoTrack)
            val aFmt = audioExtractor.getTrackFormat(audioTrack)

            muxer = MediaMuxer(outPath, MediaMuxer.OutputFormat.MUXER_OUTPUT_MPEG_4)
            val vIdx = muxer.addTrack(vFmt)
            val aIdx = muxer.addTrack(aFmt)
            videoExtractor.selectTrack(videoTrack)
            audioExtractor.selectTrack(audioTrack)
            muxer.start()

            val maxBufferSize = maxOf(
                vFmt.getInteger(android.media.MediaFormat.KEY_MAX_INPUT_SIZE).coerceAtLeast(1 shl 20),
                if (aFmt.containsKey(android.media.MediaFormat.KEY_MAX_INPUT_SIZE))
                    aFmt.getInteger(android.media.MediaFormat.KEY_MAX_INPUT_SIZE) else 1 shl 20,
                4 shl 20
            )
            val buffer = java.nio.ByteBuffer.allocate(maxBufferSize)
            val info = android.media.MediaCodec.BufferInfo()

            while (true) {
                val size = videoExtractor.readSampleData(buffer, 0)
                if (size < 0) break
                info.offset = 0; info.size = size
                info.presentationTimeUs = videoExtractor.sampleTime
                info.flags = videoExtractor.sampleFlags
                muxer.writeSampleData(vIdx, buffer, info)
                videoExtractor.advance()
            }
            while (true) {
                val size = audioExtractor.readSampleData(buffer, 0)
                if (size < 0) break
                info.offset = 0; info.size = size
                info.presentationTimeUs = audioExtractor.sampleTime
                info.flags = audioExtractor.sampleFlags
                muxer.writeSampleData(aIdx, buffer, info)
                audioExtractor.advance()
            }
            muxer.stop()
            return outPath
        } catch (e: Exception) {
            try { File(outPath).delete() } catch (_: Exception) {}
            return null
        } finally {
            try { videoExtractor.release() } catch (_: Exception) {}
            try { audioExtractor.release() } catch (_: Exception) {}
            try { muxer?.release() } catch (_: Exception) {}
        }
    }
}

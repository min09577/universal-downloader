package com.min0777.universaldownloader

import android.media.MediaExtractor
import android.media.MediaMuxer
import java.io.File

/**
 * 无损 MP4 双轨拼装器（系统 MediaMuxer，无需 ffmpeg）
 *
 * B 站 DASH 的视频流(H.264/AVC in mp4)与音频流(AAC in m4a)都是 MP4 系容器，
 * MediaMuxer 可直接 remux 到同一个 MP4，不转码、无损、速度快（IO 瓶颈级）。
 */
object MediaMerger {

    /**
     * @param videoPath 视频流文件 (mp4, H.264/HEVC)
     * @param audioPath 音频流文件 (m4a, AAC)
     * @param outPath   输出 MP4 路径
     * @return 成功返回输出文件路径，失败返回 null
     */
    fun remux(videoPath: String, audioPath: String, outPath: String): String? {
        val videoExtractor = MediaExtractor()
        val audioExtractor = MediaExtractor()
        var muxer: MediaMuxer? = null
        try {
            videoExtractor.setDataSource(videoPath)
            audioExtractor.setDataSource(audioPath)

            var videoTrack = -1
            for (i in 0 until videoExtractor.trackCount) {
                val fmt = videoExtractor.getTrackFormat(i)
                if (fmt.getString(MediaFormat_KEY_MIME)?.startsWith("video/") == true) {
                    videoTrack = i
                    break
                }
            }
            var audioTrack = -1
            for (i in 0 until audioExtractor.trackCount) {
                val fmt = audioExtractor.getTrackFormat(i)
                if (fmt.getString(MediaFormat_KEY_MIME)?.startsWith("audio/") == true) {
                    audioTrack = i
                    break
                }
            }
            if (videoTrack < 0 || audioTrack < 0) return null

            val vFmt = videoExtractor.getTrackFormat(videoTrack)
            val aFmt = audioExtractor.getTrackFormat(audioTrack)

            muxer = MediaMuxer(outPath, MediaMuxer.OutputFormat.MUXER_OUTPUT_MPEG_4)
            val vIdx = muxer.addTrack(vFmt)
            val aIdx = muxer.addTrack(aFmt)

            // selectTrack 必须在 addTrack 之后、读取样本之前完成
            videoExtractor.selectTrack(videoTrack)
            audioExtractor.selectTrack(audioTrack)
            muxer.start()

            val maxBufferSize = maxOf(
                vFmt.getInteger(android.media.MediaFormat.KEY_MAX_INPUT_SIZE).coerceAtLeast(1 shl 20),
                if (aFmt.containsKey(android.media.MediaFormat.KEY_MAX_INPUT_SIZE))
                    aFmt.getInteger(android.media.MediaFormat.KEY_MAX_INPUT_SIZE) else 1 shl 20,
                4 shl 20  // 1080P 大帧保险: 视频帧可能远超 extractor 上报值
            )
            val buffer = java.nio.ByteBuffer.allocate(maxBufferSize)
            val info = android.media.MediaCodec.BufferInfo()

            // 写视频轨
            while (true) {
                val size = videoExtractor.readSampleData(buffer, 0)
                if (size < 0) break
                info.offset = 0
                info.size = size
                info.presentationTimeUs = videoExtractor.sampleTime
                info.flags = videoExtractor.sampleFlags
                muxer.writeSampleData(vIdx, buffer, info)
                videoExtractor.advance()
            }

            // 写音频轨
            while (true) {
                val size = audioExtractor.readSampleData(buffer, 0)
                if (size < 0) break
                info.offset = 0
                info.size = size
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

    private const val MediaFormat_KEY_MIME = "mime"
}

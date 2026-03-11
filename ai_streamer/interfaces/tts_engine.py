"""
TTS语音合成接口 - 支持Edge TTS和GPT-SoVITS，带口型同步

口型同步原理：
1. 生成音频文件
2. 分析音频音量/波形
3. 播放音频的同时，按时间线发送嘴型开合度给VTube Studio
"""
import asyncio
import edge_tts
import yaml
import wave
import math
import struct
import threading
import time
from pathlib import Path
from typing import Optional, Callable
from pydub import AudioSegment
from loguru import logger


class TTSEngine:
    """TTS引擎 - 带口型同步"""
    
    def __init__(self, config_path: str = "config/api_keys.yaml", vtube_controller=None):
        self.engine_type = "edge"
        self.edge_voice = "zh-CN-XiaoxiaoNeural"
        self.gpt_sovits_url = "http://localhost:9880"
        self.vtube = vtube_controller  # VTube Studio控制器引用
        
        # 加载配置
        if Path(config_path).exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                tts_config = config.get("tts", {})
                self.engine_type = tts_config.get("engine", "edge")
                self.edge_voice = tts_config.get("edge_voice", "zh-CN-XiaoxiaoNeural")
                self.gpt_sovits_url = tts_config.get("gpt_sovits_url", "http://localhost:9880")
        
        # 口型同步设置
        self.lip_sync_enabled = True
        self.lip_sync_thread = None
        self.is_speaking = False
        
        logger.info(f"TTS引擎初始化: {self.engine_type}")
    
    def set_vtube_controller(self, vtube_controller):
        """设置VTube控制器（用于口型同步）"""
        self.vtube = vtube_controller
    
    async def synthesize(self, text: str, output_path: str = "data/logs/tts_output.mp3") -> str:
        """合成语音"""
        if self.engine_type == "edge":
            return await self._edge_tts(text, output_path)
        elif self.engine_type == "gpt_sovits":
            return await self._gpt_sovits(text, output_path)
        else:
            raise ValueError(f"未知的TTS引擎: {self.engine_type}")
    
    async def _edge_tts(self, text: str, output_path: str) -> str:
        """使用Edge TTS"""
        communicate = edge_tts.Communicate(text, self.edge_voice)
        await communicate.save(output_path)
        logger.debug(f"Edge TTS合成完成: {output_path}")
        return output_path
    
    async def _gpt_sovits(self, text: str, output_path: str) -> str:
        """使用GPT-SoVITS"""
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.gpt_sovits_url}/tts",
                json={"text": text, "output_path": output_path}
            ) as resp:
                if resp.status == 200:
                    logger.debug(f"GPT-SoVITS合成完成: {output_path}")
                    return output_path
                else:
                    raise Exception(f"GPT-SoVITS合成失败: {resp.status}")
    
    async def speak(self, text: str, auto_play: bool = True) -> str:
        """
        合成并播放语音，带口型同步
        
        Args:
            text: 要播报的文本
            auto_play: 是否自动播放
        
        Returns:
            音频文件路径
        """
        try:
            # 1. 生成音频
            audio_path = await self.synthesize(text)
            logger.info(f"语音已生成: {audio_path}")
            
            if auto_play and audio_path:
                # 2. 播放并同步口型
                await self._play_with_lip_sync(audio_path)
            
            return audio_path
            
        except Exception as e:
            logger.error(f"TTS失败: {e}")
            return None
    
    async def _play_with_lip_sync(self, audio_path: str):
        """
        播放音频并同步口型
        
        实现方式：
        1. 分析音频波形，提取音量包络
        2. 播放音频的同时，按时间发送嘴型数据
        """
        try:
            # 加载音频
            audio = AudioSegment.from_mp3(audio_path)
            
            # 转换为wav格式（更容易分析）
            wav_path = audio_path.replace(".mp3", ".wav")
            audio.export(wav_path, format="wav")
            
            # 分析音频获取音量包络
            volume_envelope = self._analyze_audio_volume(wav_path)
            
            # 开始播放
            logger.info(f"开始播放，时长: {len(audio)/1000:.1f}秒")
            
            # 在新线程中播放音频
            import simpleaudio as sa
            wave_obj = sa.WaveObject.from_wave_file(wav_path)
            
            self.is_speaking = True
            
            # 播放音频
            play_obj = wave_obj.play()
            
            # 同时运行口型同步
            if self.vtube and self.lip_sync_enabled:
                self._run_lip_sync(volume_envelope, len(audio))
            elif self.vtube:
                # 简单模式：直接开始说话动画
                self.vtube.start_talking()
            
            # 等待播放完成
            play_obj.wait_done()
            self.is_speaking = False
            
            # 停止说话动画
            if self.vtube:
                self.vtube.stop_talking()
            
            # 清理临时文件
            Path(wav_path).unlink(missing_ok=True)
            
        except ImportError:
            logger.warning("缺少音频播放库，使用系统默认播放器")
            await self._play_audio_system(audio_path)
        except Exception as e:
            logger.error(f"播放失败: {e}")
            self.is_speaking = False
    
    def _analyze_audio_volume(self, wav_path: str, sample_rate: int = 30) -> list:
        """
        分析音频音量包络
        
        Args:
            wav_path: WAV文件路径
            sample_rate: 每秒采样点数（控制口型更新频率）
        
        Returns:
            音量值列表 (0.0 - 1.0)
        """
        with wave.open(wav_path, 'rb') as wav_file:
            # 获取音频参数
            n_channels = wav_file.getnchannels()
            sample_width = wav_file.getsampwidth()
            frame_rate = wav_file.getframerate()
            n_frames = wav_file.getnframes()
            
            # 读取所有帧
            frames = wav_file.readframes(n_frames)
            
            # 转换为数值
            if sample_width == 2:
                fmt = f"{len(frames)//2}h"
                samples = struct.unpack(fmt, frames)
            else:
                # 其他位深暂不处理
                return [0.5] * 100
            
            # 计算每帧的音量（RMS）
            samples_per_slice = frame_rate // sample_rate
            volume_envelope = []
            
            for i in range(0, len(samples), samples_per_slice):
                slice_samples = samples[i:i + samples_per_slice]
                if len(slice_samples) == 0:
                    break
                
                # 计算RMS音量
                rms = math.sqrt(sum(s**2 for s in slice_samples) / len(slice_samples))
                
                # 归一化到 0-1 范围
                # 16位音频最大值是32768
                normalized = min(rms / 1000, 1.0)  # 1000是经验阈值
                
                # 映射到嘴型开合度 (0.1 - 1.0)
                mouth_open = 0.1 + normalized * 0.9
                volume_envelope.append(mouth_open)
        
        return volume_envelope
    
    def _run_lip_sync(self, volume_envelope: list, audio_duration_ms: int):
        """
        运行口型同步
        
        Args:
            volume_envelope: 音量包络列表
            audio_duration_ms: 音频时长（毫秒）
        """
        if not self.vtube:
            return
        
        frame_duration = audio_duration_ms / len(volume_envelope) / 1000  # 每帧秒数
        
        def sync_loop():
            start_time = time.time()
            
            for i, mouth_open in enumerate(volume_envelope):
                if not self.is_speaking:
                    break
                
                # 发送嘴型数据到VTube Studio
                self.vtube.set_mouth_open(mouth_open)
                
                # 精确等待到下一帧
                target_time = start_time + (i + 1) * frame_duration
                sleep_time = target_time - time.time()
                if sleep_time > 0:
                    time.sleep(sleep_time)
            
            # 闭嘴
            self.vtube.set_mouth_open(0.0)
        
        # 在新线程中运行
        self.lip_sync_thread = threading.Thread(target=sync_loop)
        self.lip_sync_thread.start()
    
    async def _play_audio_system(self, audio_path: str):
        """使用系统默认播放器播放"""
        import platform
        import subprocess
        import os
        
        system = platform.system()
        
        try:
            if system == "Windows":
                os.startfile(audio_path)
            elif system == "Darwin":
                subprocess.run(["afplay", audio_path], check=False)
            else:
                subprocess.run(["mpg123", audio_path], check=False)
                
        except Exception as e:
            logger.warning(f"播放失败: {e}")
    
    async def speak_with_simple_lip_sync(self, text: str):
        """
        简化版口型同步（不需要分析音频）
        根据文字长度估算说话时间，嘴型随机开合
        """
        audio_path = await self.synthesize(text)
        
        if not audio_path or not self.vtube:
            return audio_path
        
        # 估算说话时间（中文约每秒4个字）
        char_count = len(text)
        speak_duration = char_count / 4.0
        
        # 播放音频
        asyncio.create_task(self._play_audio_system(audio_path))
        
        # 嘴型动画
        self.is_speaking = True
        self.vtube.start_talking()
        
        await asyncio.sleep(speak_duration)
        
        self.is_speaking = False
        self.vtube.stop_talking()
        
        return audio_path


# 测试
if __name__ == "__main__":
    async def test():
        tts = TTSEngine()
        
        # 测试语音合成和口型分析
        print("测试语音合成...")
        audio_path = await tts.synthesize("你好，我是AI虚拟主播，正在测试口型同步功能。")
        
        # 分析音量
        print("分析音频...")
        wav_path = audio_path.replace(".mp3", ".wav")
        from pydub import AudioSegment
        audio = AudioSegment.from_mp3(audio_path)
        audio.export(wav_path, format="wav")
        
        envelope = tts._analyze_audio_volume(wav_path)
        print(f"音量包络点数: {len(envelope)}")
        print(f"前10个值: {envelope[:10]}")
        
        # 清理
        Path(wav_path).unlink(missing_ok=True)
        print("测试完成！")
    
    asyncio.run(test())

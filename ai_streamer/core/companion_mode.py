"""
无人交互内容生成器
当直播间安静时，主动制造内容
"""
import asyncio
import random
from datetime import datetime
from typing import Optional, Callable
from loguru import logger

from core.memory_bridge import get_memory_bridge


class SilentContentGenerator:
    """沉默内容生成器"""
    
    def __init__(self, 
                 tts_callback: Optional[Callable] = None,
                 danmaku_callback: Optional[Callable] = None):
        """
        Args:
            tts_callback: TTS播报回调函数
            danmaku_callback: 发送弹幕回调函数
        """
        self.tts_callback = tts_callback
        self.danmaku_callback = danmaku_callback
        
        self.memory_bridge = get_memory_bridge()
        self.is_running = False
        self.silence_start_time = None
        self.last_interaction_time = datetime.now()
        self.last_content_time = datetime.now()
        
        # 配置
        self.check_interval = 30  # 每30秒检查一次
        self.min_silence_for_content = 60  # 至少沉默1分钟才说话
        self.max_silence_for_forced = 900  # 15分钟必须说点什么
        
    def on_user_interaction(self):
        """用户交互时调用，重置沉默计时"""
        self.last_interaction_time = datetime.now()
        self.silence_start_time = None
        logger.debug("检测到用户交互，重置沉默计时")
    
    def get_silence_duration(self) -> int:
        """获取当前沉默时长（秒）"""
        return int((datetime.now() - self.last_interaction_time).total_seconds())
    
    def should_generate_content(self) -> bool:
        """判断是否该生成内容了"""
        silence = self.get_silence_duration()
        
        # 沉默太短，不说
        if silence < self.min_silence_for_content:
            return False
        
        # 沉默太久，必须说
        if silence >= self.max_silence_for_forced:
            return True
        
        # 中间阶段，随机概率
        # 沉默时间越长，概率越高
        probability = min(0.3, silence / 3000)  # 最多30%概率
        return random.random() < probability
    
    def generate_content(self) -> Optional[str]:
        """生成内容"""
        silence = self.get_silence_duration()
        content = self.memory_bridge.generate_silent_content(silence)
        
        if content:
            self.last_content_time = datetime.now()
            logger.info(f"生成沉默内容: {content[:50]}...")
        
        return content
    
    async def run(self):
        """主循环"""
        logger.info("沉默内容生成器启动")
        self.is_running = True
        
        while self.is_running:
            try:
                # 检查是否该说话了
                if self.should_generate_content():
                    content = self.generate_content()
                    
                    if content:
                        # 通过TTS播报
                        if self.tts_callback:
                            await self.tts_callback(content)
                        
                        # 可选：同时发弹幕
                        if self.danmaku_callback and random.random() < 0.3:
                            await self.danmaku_callback(content)
                
                # 等待下次检查
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"沉默内容生成器错误: {e}")
                await asyncio.sleep(self.check_interval)
        
        logger.info("沉默内容生成器停止")
    
    def stop(self):
        """停止生成器"""
        self.is_running = False


class HourlyAnnouncer:
    """整点播报器"""
    
    def __init__(self, tts_callback: Optional[Callable] = None):
        """
        Args:
            tts_callback: TTS播报回调函数
        """
        self.tts_callback = tts_callback
        self.memory_bridge = get_memory_bridge()
        self.is_running = False
        self.last_announced_hour = -1
    
    async def run(self):
        """主循环"""
        logger.info("整点播报器启动")
        self.is_running = True
        
        while self.is_running:
            try:
                now = datetime.now()
                current_hour = now.hour
                current_minute = now.minute
                
                # 整点且未播报过
                if current_minute == 0 and current_hour != self.last_announced_hour:
                    content = self.memory_bridge.generate_hourly_announcement()
                    
                    logger.info(f"整点播报: {content}")
                    
                    if self.tts_callback:
                        await self.tts_callback(content)
                    
                    self.last_announced_hour = current_hour
                
                # 每分钟检查一次
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error(f"整点播报器错误: {e}")
                await asyncio.sleep(60)
        
        logger.info("整点播报器停止")
    
    def stop(self):
        """停止播报器"""
        self.is_running = False


class CompanionMode:
    """
    赛博陪伴模式
    整合沉默内容生成和整点播报
    """
    
    def __init__(self, 
                 tts_callback: Optional[Callable] = None,
                 danmaku_callback: Optional[Callable] = None):
        """
        Args:
            tts_callback: TTS播报回调
            danmaku_callback: 弹幕发送回调
        """
        self.silent_generator = SilentContentGenerator(
            tts_callback=tts_callback,
            danmaku_callback=danmaku_callback
        )
        self.hourly_announcer = HourlyAnnouncer(
            tts_callback=tts_callback
        )
        
        self.tasks = []
    
    async def start(self):
        """启动陪伴模式"""
        logger.info("启动赛博陪伴模式")
        
        # 创建任务
        self.tasks = [
            asyncio.create_task(self.silent_generator.run()),
            asyncio.create_task(self.hourly_announcer.run()),
        ]
        
        # 等待所有任务（理论上不会结束）
        await asyncio.gather(*self.tasks, return_exceptions=True)
    
    def on_user_interaction(self):
        """用户交互时调用"""
        self.silent_generator.on_user_interaction()
    
    def stop(self):
        """停止陪伴模式"""
        logger.info("停止赛博陪伴模式")
        self.silent_generator.stop()
        self.hourly_announcer.stop()
        
        # 取消任务
        for task in self.tasks:
            if not task.done():
                task.cancel()


# 便捷函数
def create_companion_mode(tts_func=None, danmaku_func=None) -> CompanionMode:
    """创建陪伴模式实例"""
    return CompanionMode(
        tts_callback=tts_func,
        danmaku_callback=danmaku_func
    )

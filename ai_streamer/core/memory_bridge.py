"""
记忆桥接器 - 连接外部memory系统和ai_streamer
让热梗、常识、陪伴话术流入直播间
"""
import os
import random
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from loguru import logger


class MemoryBridge:
    """记忆桥接器"""
    
    def __init__(self, memory_dir: str = "../memory"):
        """
        Args:
            memory_dir: memory系统根目录路径
        """
        self.memory_dir = Path(memory_dir).resolve()
        self.memes_cache = []
        self.events_cache = []
        self.companion_phrases = []
        self.last_refresh = None
        
        self._load_all()
    
    def _load_all(self):
        """加载所有记忆内容"""
        logger.info(f"正在从 {self.memory_dir} 加载记忆...")
        
        # 加载热梗
        self._load_memes()
        
        # 加载热点事件
        self._load_events()
        
        # 加载陪伴话术
        self._load_companion_phrases()
        
        self.last_refresh = datetime.now()
        logger.info(f"记忆加载完成: {len(self.memes_cache)}个梗, {len(self.events_cache)}个事件")
    
    def _load_memes(self):
        """从current-hot.md加载热梗"""
        meme_file = self.memory_dir / "memes" / "current-hot.md"
        
        if not meme_file.exists():
            logger.warning(f"热梗文件不存在: {meme_file}")
            return
        
        try:
            with open(meme_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 解析md文件，提取梗信息
            current_meme = {}
            for line in content.split('\n'):
                # 匹配 ### 梗名
                if line.startswith('### '):
                    if current_meme:
                        self.memes_cache.append(current_meme)
                    current_meme = {
                        'name': line.replace('### ', '').strip(),
                        'source': '',
                        'meaning': '',
                        'usage': ''
                    }
                # 匹配来源
                elif line.startswith('- **来源**:'):
                    current_meme['source'] = line.split(':', 1)[1].strip()
                # 匹配含义
                elif line.startswith('- **含义**:'):
                    current_meme['meaning'] = line.split(':', 1)[1].strip()
                # 匹配用法
                elif line.startswith('- **用法**:'):
                    current_meme['usage'] = line.split(':', 1)[1].strip()
            
            if current_meme:
                self.memes_cache.append(current_meme)
                
        except Exception as e:
            logger.error(f"加载热梗失败: {e}")
    
    def _load_events(self):
        """从world-events.md加载热点事件"""
        events_file = self.memory_dir / "common-sense" / "world-events.md"
        
        if not events_file.exists():
            logger.warning(f"事件文件不存在: {events_file}")
            return
        
        try:
            with open(events_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 简单提取科技圈热点
            in_tech_section = False
            for line in content.split('\n'):
                if '科技' in line and '##' in line:
                    in_tech_section = True
                    continue
                if in_tech_section and line.startswith('- **'):
                    # 提取事件标题
                    event = line.replace('- **', '').split('**')[0]
                    if event:
                        self.events_cache.append(event)
                        
        except Exception as e:
            logger.error(f"加载事件失败: {e}")
    
    def _load_companion_phrases(self):
        """加载陪伴话术"""
        # 内置话术库，也可以从文件读取
        self.companion_phrases = {
            "morning": [
                "新的一天开始了",
                "早餐吃了吗",
                "今天也要加油",
                "早上的空气怎么样",
            ],
            "afternoon": [
                "该休息一下了",
                "午饭吃了什么",
                "下午容易困呢",
                "工作还顺利吗",
            ],
            "evening": [
                "晚饭时间",
                "今天过得怎么样",
                "准备休息了吗",
                "晚上是属于自己的时间",
            ],
            "night": [
                "还在啊",
                "别熬太晚",
                "陪你到困为止",
                "这个点还在的，都是有故事的人",
                "爱你老己",
            ],
            "meme_reactions": [
                "刚学到一个新梗——{meme_name}，{meme_meaning}",
                "你们有没有听说过{meme_name}？{meme_usage}",
                "今天刷到{meme_name}，感觉说的就是我",
            ]
        }
    
    def get_time_period(self) -> str:
        """判断当前时间段"""
        hour = datetime.now().hour
        if 6 <= hour < 12:
            return "morning"
        elif 12 <= hour < 18:
            return "afternoon"
        elif 18 <= hour < 23:
            return "evening"
        else:
            return "night"
    
    def get_random_meme(self) -> Optional[Dict]:
        """获取随机热梗"""
        if not self.memes_cache:
            return None
        return random.choice(self.memes_cache)
    
    def get_random_event(self) -> Optional[str]:
        """获取随机热点事件"""
        if not self.events_cache:
            return None
        return random.choice(self.events_cache)
    
    def get_companion_phrase(self, phrase_type: str = None) -> str:
        """获取陪伴话术"""
        if phrase_type is None:
            phrase_type = self.get_time_period()
        
        if phrase_type in self.companion_phrases:
            phrases = self.companion_phrases[phrase_type]
            return random.choice(phrases)
        
        return "在的"
    
    def generate_hourly_announcement(self) -> str:
        """生成整点播报"""
        hour = datetime.now().hour
        period = self.get_time_period()
        
        # 基础报时
        base = f"{hour}点了"
        
        # 附加陪伴语
        extra = self.get_companion_phrase(period)
        
        # 深夜特殊处理
        if period == "night":
            if hour == 0:
                extra = "新的一天开始了，虽然已经是凌晨"
            elif hour == 3:
                extra = "3点了，直播间最安静的时候"
        
        return f"{base}，{extra}"
    
    def generate_meme_chat(self) -> Optional[str]:
        """生成热梗话题"""
        meme = self.get_random_meme()
        if not meme:
            return None
        
        templates = [
            f"突然想到一个梗——{meme['name']}，{meme.get('meaning', '挺有意思的')}",
            f"今天学了个新说法：{meme['name']}，用来形容{meme.get('usage', '各种情况')}",
            f"有没有人听说过{meme['name']}？{meme.get('source', '最近挺火的')}",
        ]
        
        return random.choice(templates)
    
    def generate_silent_content(self, silence_duration: int = 0) -> Optional[str]:
        """
        生成无人交互时的内容
        
        Args:
            silence_duration: 已经沉默的秒数
            
        Returns:
            要播报的内容，或None表示不说话
        """
        # 沉默时间短，不说太多
        if silence_duration < 300:  # 5分钟内
            if random.random() < 0.1:  # 10%概率碎碎念
                return self.get_companion_phrase()
            return None
        
        # 沉默5-15分钟，说点啥
        elif silence_duration < 900:
            rand = random.random()
            if rand < 0.3:
                return self.get_companion_phrase()
            elif rand < 0.5:
                return self.generate_meme_chat()
            return None
        
        # 沉默超过15分钟，必须说点什么
        else:
            rand = random.random()
            if rand < 0.4:
                return self.generate_meme_chat()
            elif rand < 0.7:
                event = self.get_random_event()
                if event:
                    return f"刚看到个消息——{event}，你们听说了吗？"
            return self.get_companion_phrase()
    
    def refresh(self):
        """刷新记忆（定时调用）"""
        logger.info("刷新记忆...")
        self._load_all()


# 单例模式
_memory_bridge = None

def get_memory_bridge() -> MemoryBridge:
    """获取记忆桥接器单例"""
    global _memory_bridge
    if _memory_bridge is None:
        # 尝试找到memory目录
        possible_paths = [
            "../memory",  # 从ai_streamer目录运行
            "./memory",   # 从根目录运行
            "/root/.openclaw/workspace/memory",  # 绝对路径
        ]
        
        for path in possible_paths:
            if Path(path).exists():
                _memory_bridge = MemoryBridge(path)
                break
        else:
            logger.warning("未找到memory目录，使用空记忆")
            _memory_bridge = MemoryBridge("./memory")  # 会创建空实例
    
    return _memory_bridge


if __name__ == "__main__":
    # 测试
    bridge = get_memory_bridge()
    
    print("\n=== 整点播报测试 ===")
    for hour in [9, 14, 20, 3]:
        bridge.get_time_period = lambda: bridge.get_time_period.__class__(
            (lambda h: "morning" if 6 <= h < 12 else 
             "afternoon" if 12 <= h < 18 else
             "evening" if 18 <= h < 23 else "night")(hour)
        )
    
    print(bridge.generate_hourly_announcement())
    
    print("\n=== 热梗话题测试 ===")
    meme_chat = bridge.generate_meme_chat()
    if meme_chat:
        print(meme_chat)
    
    print("\n=== 沉默内容测试 ===")
    for duration in [0, 300, 900, 1200]:
        content = bridge.generate_silent_content(duration)
        print(f"沉默{duration}秒: {content or '(不说话)'}")

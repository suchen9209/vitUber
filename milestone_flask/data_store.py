"""
直播间里程碑数据存储
完全独立模块，可与现有系统配合使用
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, List, Callable
from dataclasses import dataclass, asdict
from threading import RLock as Lock


@dataclass
class LevelConfig:
    """等级配置"""
    name: str
    icon: str
    required_xp: int
    color: str = "#FFD700"


class MilestoneDataStore:
    """
    里程碑数据存储类
    支持实时事件监听、等级计算、数据持久化
    """
    
    # 等级定义
    LEVELS = {
        1: LevelConfig("初入直播", "🌱", 0, "#90EE90"),
        2: LevelConfig("小透明", "🌿", 100, "#98FB98"),
        3: LevelConfig("话痨新人", "🌸", 300, "#FFB6C1"),
        4: LevelConfig("互动达人", "🌺", 600, "#FF69B4"),
        5: LevelConfig("人气主播", "🌻", 1000, "#FFD700"),
        6: LevelConfig("直播明星", "🌟", 2000, "#FFA500"),
        7: LevelConfig("顶流存在", "👑", 5000, "#FF6347"),
        8: LevelConfig("传奇主播", "🏆", 10000, "#FFD700"),
    }
    
    # 经验值规则
    XP_RULES = {
        "enter": 5,      # 有人入场
        "chat": 10,      # 弹幕互动
        "gift": 50,      # 收到礼物
        "like": 2,       # 点赞
        "share": 20,     # 分享
    }
    
    def __init__(self, data_dir: str = "data"):
        """
        初始化数据存储
        
        Args:
            data_dir: 数据存储目录
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        self.data_file = self.data_dir / "milestone_flask.json"
        self.lock = Lock()  # 线程锁
        
        # 数据
        self._data = {
            "current_level": 1,
            "total_xp": 0,
            "today": {
                "date": datetime.now().strftime("%Y-%m-%d"),
                "enters": 0,
                "chats": 0,
                "gifts": 0,
                "likes": 0,
                "total_xp": 0
            },
            "streak_days": 1,
            "session_start": datetime.now().isoformat(),
            "recent_events": []  # 最近事件记录
        }
        
        # 事件监听器
        self._listeners: List[Callable] = []
        
        # 加载数据
        self._load()
    
    def _load(self):
        """从文件加载数据"""
        if self.data_file.exists():
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    
                # 检查是否新的一天
                saved_date = loaded.get("today", {}).get("date", "")
                today = datetime.now().strftime("%Y-%m-%d")
                
                if saved_date == today:
                    # 同一天，恢复数据
                    self._data["today"] = loaded.get("today", self._data["today"])
                    self._data["streak_days"] = loaded.get("streak_days", 1)
                else:
                    # 新的一天，重置今日数据，增加连续天数
                    self._data["streak_days"] = loaded.get("streak_days", 0) + 1
                    print(f"[Milestone] 新的一天！连续直播 {self._data['streak_days']} 天")
                
                self._data["current_level"] = loaded.get("current_level", 1)
                self._data["total_xp"] = loaded.get("total_xp", 0)
                
            except Exception as e:
                print(f"[Milestone] 加载数据失败: {e}，使用默认数据")
    
    def _save(self):
        """保存数据到文件"""
        try:
            with self.lock:
                with open(self.data_file, 'w', encoding='utf-8') as f:
                    json.dump(self._data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[Milestone] 保存数据失败: {e}")
    
    def add_event(self, event_type: str, user: str = "", extra: dict = None) -> dict:
        """
        添加互动事件
        
        Args:
            event_type: 事件类型 (enter/chat/gift/like/share)
            user: 用户名
            extra: 额外信息
            
        Returns:
            事件结果，包含是否升级等信息
        """
        with self.lock:
            xp = self.XP_RULES.get(event_type, 0)
            old_level = self._data["current_level"]
            
            # 更新统计数据
            if event_type == "enter":
                self._data["today"]["enters"] += 1
            elif event_type == "chat":
                self._data["today"]["chats"] += 1
            elif event_type == "gift":
                self._data["today"]["gifts"] += 1
            elif event_type == "like":
                self._data["today"]["likes"] += 1
            
            # 更新经验值
            self._data["today"]["total_xp"] += xp
            self._data["total_xp"] += xp
            
            # 检查升级
            level_up_info = None
            next_level = old_level + 1
            if next_level in self.LEVELS:
                required = self.LEVELS[next_level].required_xp
                if self._data["total_xp"] >= required:
                    self._data["current_level"] = next_level
                    level_up_info = {
                        "old_level": old_level,
                        "new_level": next_level,
                        "name": self.LEVELS[next_level].name,
                        "icon": self.LEVELS[next_level].icon
                    }
            
            # 记录最近事件（保留最近20条）
            event_record = {
                "type": event_type,
                "user": user,
                "xp": xp,
                "time": datetime.now().strftime("%H:%M:%S"),
                "extra": extra or {}
            }
            self._data["recent_events"].insert(0, event_record)
            self._data["recent_events"] = self._data["recent_events"][:20]
            
            # 保存
            self._save()
            
            # 构建结果
            result = {
                "type": event_type,
                "user": user,
                "xp_gained": xp,
                "total_xp": self._data["total_xp"],
                "level_up": level_up_info,
                "current": self.get_status()
            }
            
            # 通知监听器
            for listener in self._listeners:
                try:
                    listener(result)
                except Exception as e:
                    print(f"[Milestone] 监听器错误: {e}")
            
            return result
    
    def get_status(self) -> dict:
        """
        获取当前完整状态
        
        Returns:
            包含等级、进度、统计等信息的字典
        """
        with self.lock:
            level = self._data["current_level"]
            level_info = self.LEVELS.get(level, self.LEVELS[1])
            
            # 计算进度
            next_level = level + 1
            progress = 100
            xp_to_next = 0
            
            if next_level in self.LEVELS:
                current_required = level_info.required_xp
                next_required = self.LEVELS[next_level].required_xp
                xp_in_level = self._data["total_xp"] - current_required
                level_range = next_required - current_required
                progress = min(100, int((xp_in_level / level_range) * 100))
                xp_to_next = next_required - self._data["total_xp"]
            
            # 计算直播时长
            try:
                start = datetime.fromisoformat(self._data["session_start"])
                duration = datetime.now() - start
                hours, remainder = divmod(int(duration.total_seconds()), 3600)
                minutes, _ = divmod(remainder, 60)
                stream_time = f"{hours}小时{minutes}分"
            except:
                stream_time = "未知"
            
            return {
                "current_level": level,
                "level_name": level_info.name,
                "level_icon": level_info.icon,
                "total_xp": self._data["total_xp"],
                "progress_percent": progress,
                "xp_to_next": xp_to_next,
                "today": self._data["today"],
                "streak_days": self._data["streak_days"],
                "stream_time": stream_time,
                "recent_events": self._data["recent_events"][:5]  # 只返回最近5条
            }
    
    def add_listener(self, callback: Callable):
        """
        添加事件监听器
        
        Args:
            callback: 回调函数，接收事件结果字典
        """
        self._listeners.append(callback)
    
    def remove_listener(self, callback: Callable):
        """移除事件监听器"""
        if callback in self._listeners:
            self._listeners.remove(callback)
    
    def reset_today(self):
        """重置今日数据（调试用）"""
        with self.lock:
            self._data["today"] = {
                "date": datetime.now().strftime("%Y-%m-%d"),
                "enters": 0,
                "chats": 0,
                "gifts": 0,
                "likes": 0,
                "total_xp": 0
            }
            self._save()
    
    def reset_all(self):
        """重置所有数据（危险操作！）"""
        with self.lock:
            self._data = {
                "current_level": 1,
                "total_xp": 0,
                "today": {
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "enters": 0,
                    "chats": 0,
                    "gifts": 0,
                    "likes": 0,
                    "total_xp": 0
                },
                "streak_days": 1,
                "session_start": datetime.now().isoformat(),
                "recent_events": []
            }
            self._save()


# 单例模式
data_store = None

def get_data_store() -> MilestoneDataStore:
    """获取全局数据存储实例"""
    global data_store
    if data_store is None:
        data_store = MilestoneDataStore()
    return data_store

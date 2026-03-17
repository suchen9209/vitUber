"""
记忆管理系统 - 处理VIP和普通观众的记忆存储
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from loguru import logger


@dataclass
class UserProfile:
    """用户档案"""
    user_id: str
    username: str
    user_type: str = "regular"  # "vip" 或 "regular"
    join_count: int = 0
    last_seen: str = ""
    facts: List[str] = None  # 提取的事实
    preferences: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.facts is None:
            self.facts = []
        if self.preferences is None:
            self.preferences = {}


class MemoryManager:
    """记忆管理器 - JSON文件存储"""
    
    def __init__(self, data_dir: str = "data/memory"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.vip_file = self.data_dir / "vip.json"
        self.regular_file = self.data_dir / "regular.json"
        
        self.vip_data: Dict[str, dict] = {}
        self.regular_data: Dict[str, dict] = {}
        
        self._load_all()
    
    def _load_all(self):
        """加载所有记忆数据"""
        if self.vip_file.exists():
            with open(self.vip_file, 'r', encoding='utf-8') as f:
                self.vip_data = json.load(f)
        
        if self.regular_file.exists():
            with open(self.regular_file, 'r', encoding='utf-8') as f:
                self.regular_data = json.load(f)
        
        logger.info(f"记忆加载完成: VIP={len(self.vip_data)}, 普通={len(self.regular_data)}")
    
    def _save_vip(self):
        """保存VIP数据"""
        with open(self.vip_file, 'w', encoding='utf-8') as f:
            json.dump(self.vip_data, f, ensure_ascii=False, indent=2)
    
    def _save_regular(self):
        """保存普通用户数据"""
        with open(self.regular_file, 'w', encoding='utf-8') as f:
            json.dump(self.regular_data, f, ensure_ascii=False, indent=2)
    
    def get_user(self, user_id: str, username: str = "") -> UserProfile:
        """获取用户档案，如果不存在则创建"""
        # 先查VIP
        if user_id in self.vip_data:
            data = self.vip_data[user_id]
            return UserProfile(
                user_id=user_id,
                username=data.get("username", username),
                user_type="vip",
                join_count=data.get("join_count", 0),
                last_seen=data.get("last_seen", ""),
                facts=data.get("facts", []),
                preferences=data.get("preferences", {})
            )
        
        # 再查普通用户
        if user_id in self.regular_data:
            data = self.regular_data[user_id]
            return UserProfile(
                user_id=user_id,
                username=data.get("username", username),
                user_type="regular",
                join_count=data.get("join_count", 0),
                last_seen=data.get("last_seen", ""),
                facts=data.get("facts", []),
                preferences=data.get("preferences", {})
            )
        
        # 新建普通用户
        return UserProfile(user_id=user_id, username=username)
    
    def update_user(self, profile: UserProfile):
        """更新用户档案"""
        data = {
            "username": profile.username,
            "join_count": profile.join_count,
            "last_seen": datetime.now().isoformat(),
            "facts": profile.facts,
            "preferences": profile.preferences
        }
        
        if profile.user_type == "vip":
            self.vip_data[profile.user_id] = data
            self._save_vip()
        else:
            self.regular_data[profile.user_id] = data
            self._save_regular()
    
    def add_fact(self, user_id: str, fact: str, username: str = ""):
        """为用户添加事实"""
        profile = self.get_user(user_id, username)
        if fact not in profile.facts:
            profile.facts.append(fact)
            self.update_user(profile)
            logger.info(f"为用户 {profile.username} 添加事实: {fact}")
    
    def promote_to_vip(self, user_id: str, username: str = ""):
        """将用户提升为VIP"""
        if user_id in self.regular_data:
            # 从普通用户迁移到VIP
            data = self.regular_data.pop(user_id)
            data["user_type"] = "vip"
            self.vip_data[user_id] = data
            self._save_vip()
            self._save_regular()
            logger.info(f"用户 {username} 已升级为VIP")
    
    def get_context_for_llm(self, user_id: str, username: str = "") -> str:
        """为LLM生成用户上下文"""
        profile = self.get_user(user_id, username)
        
        context_parts = [f"当前用户: {profile.username} ({profile.user_type})"]
        
        if profile.facts:
            context_parts.append("已知信息:")
            for fact in profile.facts[-5:]:  # 最近5条事实
                context_parts.append(f"  - {fact}")
        
        return "\n".join(context_parts)
    
    def get_vip_list(self) -> List[str]:
        """获取VIP用户列表"""
        return [data.get("username", uid) for uid, data in self.vip_data.items()]

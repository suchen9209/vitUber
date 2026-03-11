"""
聊天模式处理 - 处理观众互动聊天
"""
from typing import Dict, List, Optional
from loguru import logger


class ChatHandler:
    """聊天处理器"""
    
    def __init__(self, live_session):
        self.session = live_session
    
    async def handle_simple_chat(self, user_id: str, username: str, message: str) -> str:
        """
        处理简单聊天(无游戏控制)
        
        Returns:
            AI回复文本
        """
        from core.llm_client import ChatResponse
        
        # 获取用户上下文
        user_context = self.session.memory.get_context_for_llm(user_id, username)
        
        # 调用LLM(但不执行动作)
        response: ChatResponse = self.session.llm.chat(
            message=message,
            user_context=user_context,
            chat_history=self.session.chat_history
        )
        
        # 只保存事实，不执行动作
        for fact in response.facts:
            self.session.memory.add_fact(user_id, fact, username)
        
        return response.text
    
    async def handle_greeting(self, user_id: str, username: str) -> str:
        """处理新观众进入"""
        user = self.session.memory.get_user(user_id, username)
        
        if user.user_type == "vip":
            return f"欢迎回来，{username}！好久不见啦~"
        elif user.join_count > 5:
            return f"欢迎{username}，又是你呢！"
        else:
            return f"欢迎{username}来到直播间！"
    
    def is_command(self, message: str) -> bool:
        """判断是否是游戏控制指令"""
        command_keywords = [
            "帮", "点", "按", "打开", "关闭", "整理", "移动", "点击",
            "帮忙", "帮我", "操作", "控制", "玩"
        ]
        return any(kw in message for kw in command_keywords)

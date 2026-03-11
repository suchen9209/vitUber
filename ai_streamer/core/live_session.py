"""
直播会话管理 - 主循环和状态管理
"""
import asyncio
import json
from datetime import datetime
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, asdict
from loguru import logger

from .memory_manager import MemoryManager
from .llm_client import LLMClient, ChatResponse
from .game_controller import GameController
from .action_executor import ActionExecutor


@dataclass
class SessionState:
    """会话状态"""
    mode: str = "idle"  # idle, chat, game, auto
    current_game: Optional[str] = None
    last_activity: str = ""
    viewer_count: int = 0
    messages_this_session: int = 0


class LiveSession:
    """直播会话管理"""
    
    def __init__(
        self,
        memory_manager: MemoryManager,
        llm_client: LLMClient,
        game_controller: GameController,
        action_executor: ActionExecutor
    ):
        self.memory = memory_manager
        self.llm = llm_client
        self.game = game_controller
        self.executor = action_executor
        
        self.state = SessionState()
        self.running = False
        
        # 回调函数
        self.on_tts: Optional[Callable[[str], None]] = None
        self.on_message: Optional[Callable[[str, str], None]] = None  # (user, message)
        
        # 聊天历史
        self.chat_history: List[Dict] = []
        
        # 速率限制计数器重置任务
        self._counter_task = None
    
    async def start(self):
        """启动会话"""
        self.running = True
        self.state.last_activity = datetime.now().isoformat()
        
        # 启动计数器重置任务
        self._counter_task = asyncio.create_task(self._reset_counter_loop())
        
        logger.info("直播会话已启动")
    
    async def stop(self):
        """停止会话"""
        self.running = False
        
        if self._counter_task:
            self._counter_task.cancel()
        
        logger.info("直播会话已停止")
    
    async def _reset_counter_loop(self):
        """每分钟重置动作计数器"""
        while self.running:
            await asyncio.sleep(60)
            self.executor.reset_counter()
    
    async def handle_danmaku(self, user_id: str, username: str, message: str):
        """
        处理弹幕消息
        
        Args:
            user_id: 用户ID
            username: 用户名
            message: 弹幕内容
        """
        if not self.running:
            return
        
        logger.info(f"[{username}] {message}")
        
        # 更新用户记忆
        user = self.memory.get_user(user_id, username)
        user.join_count += 1
        self.memory.update_user(user)
        
        # 获取用户上下文
        user_context = self.memory.get_context_for_llm(user_id, username)
        
        # 调用LLM处理
        response: ChatResponse = self.llm.chat(
            message=message,
            user_context=user_context,
            chat_history=self.chat_history
        )
        
        # 记录聊天历史
        self.chat_history.append({"role": "user", "content": f"{username}: {message}"})
        self.chat_history.append({"role": "assistant", "content": response.text})
        
        # 限制历史长度
        if len(self.chat_history) > 20:
            self.chat_history = self.chat_history[-20:]
        
        # 保存提取的事实
        for fact in response.facts:
            self.memory.add_fact(user_id, fact, username)
        
        # 执行动作
        action_results = []
        for action in response.actions:
            result = await self.executor.execute(action)
            action_results.append(result)
        
        # TTS播报
        if response.text and self.on_tts:
            self.on_tts(response.text)
        
        # 更新状态
        self.state.messages_this_session += 1
        self.state.last_activity = datetime.now().isoformat()
        
        # 发送消息回调
        if self.on_message:
            self.on_message(username, response.text)
        
        # 记录日志
        self._log_interaction(user_id, username, message, response, action_results)
    
    def _log_interaction(self, user_id: str, username: str, message: str, 
                         response: ChatResponse, action_results: List[Dict]):
        """记录交互日志"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "username": username,
            "message": message,
            "response": response.text,
            "actions": response.actions,
            "facts": response.facts,
            "action_results": action_results
        }
        
        # 写入日志文件
        log_file = f"data/logs/chat_{datetime.now().strftime('%Y-%m-%d')}.jsonl"
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
    
    async def enter_idle_mode(self):
        """进入待机模式"""
        self.state.mode = "idle"
        logger.info("进入待机模式")
    
    async def enter_chat_mode(self):
        """进入聊天模式"""
        self.state.mode = "chat"
        logger.info("进入聊天模式")
    
    async def enter_game_mode(self, game_key: str):
        """进入游戏模式"""
        self.state.mode = "game"
        self.state.current_game = game_key
        
        # 导航到游戏
        await self.game.navigate_to_game(game_key)
        logger.info(f"进入游戏模式: {game_key}")
    
    async def enter_auto_mode(self):
        """进入自动挂机模式"""
        self.state.mode = "auto"
        logger.info("进入自动挂机模式")
    
    async def auto_tick(self):
        """
        自动模式的心跳
        定期调用，用于挂机时的自我解说
        """
        if self.state.mode != "auto":
            return
        
        # 获取游戏画面
        observation = await self.game.get_observation()
        
        # 生成解说(可选)
        # summary = self.llm.generate_observation_summary(...)
        # if self.on_tts:
        #     self.on_tts(summary)
        
        logger.debug("自动模式 tick")
    
    def get_status(self) -> Dict:
        """获取当前状态"""
        return {
            "state": asdict(self.state),
            "executor_stats": self.executor.get_stats(),
            "chat_history_length": len(self.chat_history),
            "memory": {
                "vip_count": len(self.memory.vip_data),
                "regular_count": len(self.memory.regular_data)
            }
        }

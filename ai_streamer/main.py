"""
AI虚拟主播主程序入口

使用方法:
1. 安装依赖: pip install -r requirements.txt
2. 安装Playwright浏览器: playwright install chromium
3. 配置API密钥: 复制 config/api_keys.yaml.example -> config/api_keys.yaml，填入你的Anthropic API Key
4. 运行: python main.py --room 你的房间号 --game 游戏配置名

示例:
    python main.py --room 123456 --game generic_web_game
"""
import asyncio
import argparse
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from loguru import logger

from core.memory_manager import MemoryManager
from core.llm_client import LLMClient
from core.game_controller import GameController
from core.action_executor import ActionExecutor
from core.live_session import LiveSession

from interfaces.bilibili_danmaku import BilibiliDanmaku
from interfaces.tts_engine import TTSEngine
from interfaces.vtube_studio import VTubeStudioController

from tasks.chat_handler import ChatHandler
from tasks.game_automation import GameAutomation
from tasks.command_parser import CommandParser


# 配置日志
logger.remove()
logger.add(
    "data/logs/ai_streamer.log",
    rotation="1 day",
    retention="7 days",
    encoding="utf-8",
    level="INFO"
)
logger.add(sys.stdout, level="INFO")


class AIStreamer:
    """AI虚拟主播主类"""
    
    def __init__(self, room_id: int, game_key: str = None, headless: bool = False):
        self.room_id = room_id
        self.game_key = game_key
        self.headless = headless
        
        # 组件
        self.memory: MemoryManager = None
        self.llm: LLMClient = None
        self.game: GameController = None
        self.executor: ActionExecutor = None
        self.session: LiveSession = None
        self.danmaku: BilibiliDanmaku = None
        self.tts: TTSEngine = None
        self.vtube: VTubeStudioController = None
        self.chat_handler: ChatHandler = None
        self.game_auto: GameAutomation = None
        self.command_parser: CommandParser = None
        
        self.running = False
    
    async def initialize(self):
        """初始化所有组件"""
        logger.info("=" * 50)
        logger.info("AI虚拟主播初始化中...")
        logger.info("=" * 50)
        
        # 1. 记忆系统
        self.memory = MemoryManager()
        logger.info("✓ 记忆系统")
        
        # 2. LLM客户端
        try:
            self.llm = LLMClient()
            logger.info("✓ LLM客户端 (Claude)")
        except ValueError as e:
            logger.error(f"✗ LLM初始化失败: {e}")
            logger.error("请确保已配置Anthropic API密钥!")
            raise
        
        # 3. 游戏控制器
        self.game = GameController()
        await self.game.start(headless=self.headless)
        logger.info("✓ 浏览器控制器")
        
        # 4. 动作执行器
        self.executor = ActionExecutor(self.game)
        logger.info("✓ 安全执行器")
        
        # 5. 直播会话
        self.session = LiveSession(self.memory, self.llm, self.game, self.executor)
        
        # 设置回调
        self.session.on_tts = self._on_tts
        self.session.on_message = self._on_message
        
        await self.session.start()
        logger.info("✓ 直播会话")
        
        # 6. TTS引擎
        self.tts = TTSEngine(vtube_controller=self.vtube)
        logger.info("✓ TTS引擎")
        
        # 7. VTube Studio
        self.vtube = VTubeStudioController()
        logger.info("✓ VTube Studio")
        
        # 8. 弹幕监听器
        self.danmaku = BilibiliDanmaku(
            room_id=self.room_id,
            on_danmaku=self._on_danmaku
        )
        logger.info("✓ 弹幕监听器")
        
        # 9. 任务处理器
        self.chat_handler = ChatHandler(self.session)
        self.game_auto = GameAutomation(self.game, self.llm)
        self.command_parser = CommandParser()
        logger.info("✓ 任务处理器")
        
        # 10. 进入游戏(如果指定了)
        if self.game_key:
            await self.session.enter_game_mode(self.game_key)
            await self.session.enter_auto_mode()
            asyncio.create_task(self.game_auto.start_idle_loop())
        else:
            await self.session.enter_chat_mode()
        
        logger.info("=" * 50)
        logger.info("初始化完成！开始直播...")
        logger.info("=" * 50)
    
    async def _on_danmaku(self, user_id: str, username: str, message: str):
        """弹幕回调"""
        try:
            # 1. 先尝试解析简单指令
            parsed_action = self.command_parser.parse(message)
            
            if parsed_action:
                # 是游戏指令，直接执行
                logger.info(f"[指令] {username}: {message}")
                
                # 执行动作
                result = await self.executor.execute(parsed_action)
                
                # 生成回复
                if result.get("success"):
                    reply = f"好的，{username}，已经帮你{message.replace('帮我', '').replace('请', '')}了！"
                else:
                    reply = f"抱歉{username}，操作没成功，可能是网络问题..."
                
                # TTS播报
                await self.tts.speak(reply)
                
                # VTube表情
                self.vtube.react_to_message(reply)
                
            else:
                # 是普通聊天，交给LLM处理
                await self.session.handle_danmaku(user_id, username, message)
                
                # VTube表情反应
                self.vtube.react_to_message(message)
        
        except Exception as e:
            logger.error(f"处理弹幕时出错: {e}")
    
    def _on_tts(self, text: str):
        """TTS回调"""
        # 异步调用TTS
        asyncio.create_task(self.tts.speak(text))
    
    def _on_message(self, username: str, message: str):
        """消息回调"""
        logger.info(f"[回复] {username}: {message}")
    
    async def run(self):
        """运行主循环"""
        self.running = True
        
        try:
            # 连接弹幕服务器
            await self.danmaku.connect()
        except Exception as e:
            logger.error(f"运行出错: {e}")
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """关闭清理"""
        logger.info("正在关闭...")
        self.running = False
        
        if self.game_auto:
            await self.game_auto.stop()
        
        if self.danmaku:
            await self.danmaku.disconnect()
        
        if self.session:
            await self.session.stop()
        
        if self.game:
            await self.game.close()
        
        logger.info("已关闭")


def main():
    parser = argparse.ArgumentParser(description="AI虚拟主播")
    parser.add_argument("--room", "-r", type=int, required=True, help="B站直播间号")
    parser.add_argument("--game", "-g", type=str, default=None, help="游戏配置名(如 generic_web_game)")
    parser.add_argument("--headless", action="store_true", help="无头模式(不显示浏览器窗口)")
    parser.add_argument("--test", "-t", action="store_true", help="测试模式(不连接弹幕，直接模拟)")
    
    args = parser.parse_args()
    
    async def run_test():
        """测试模式"""
        streamer = AIStreamer(room_id=args.room, game_key=args.game, headless=False)
        await streamer.initialize()
        
        print("\n测试模式 - 输入弹幕内容测试(输入 'quit' 退出):")
        while True:
            try:
                msg = input("弹幕: ")
                if msg.lower() == "quit":
                    break
                await streamer._on_danmaku("test_user", "测试用户", msg)
            except KeyboardInterrupt:
                break
        
        await streamer.shutdown()
    
    if args.test:
        asyncio.run(run_test())
    else:
        streamer = AIStreamer(room_id=args.room, game_key=args.game, headless=args.headless)
        asyncio.run(streamer.initialize())
        asyncio.run(streamer.run())


if __name__ == "__main__":
    main()

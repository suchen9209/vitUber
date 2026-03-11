"""
游戏挂机逻辑 - 自动模式下的游戏行为
"""
import asyncio
import random
from typing import Optional, List
from loguru import logger


class GameAutomation:
    """游戏自动化 - 挂机时的行为"""
    
    def __init__(self, game_controller, llm_client):
        self.game = game_controller
        self.llm = llm_client
        self.running = False
        
        # 挂机行为池
        self.idle_actions = [
            {"action": "scroll", "params": {"direction": "down", "amount": 1}},
            {"action": "scroll", "params": {"direction": "up", "amount": 1}},
            {"action": "screenshot", "params": {}},
        ]
    
    async def start_idle_loop(self):
        """启动挂机循环"""
        self.running = True
        logger.info("游戏挂机循环已启动")
        
        while self.running:
            try:
                # 随机执行挂机动作
                if random.random() < 0.3:  # 30%概率执行动作
                    action = random.choice(self.idle_actions)
                    await self.game.execute_action(action)
                
                # 每隔一段时间截图观察
                if random.random() < 0.1:  # 10%概率截图解说
                    await self._generate_commentary()
                
                # 等待下一次循环
                await asyncio.sleep(random.randint(10, 30))
                
            except Exception as e:
                logger.error(f"挂机循环异常: {e}")
                await asyncio.sleep(5)
    
    async def stop(self):
        """停止挂机循环"""
        self.running = False
        logger.info("游戏挂机循环已停止")
    
    async def _generate_commentary(self):
        """生成游戏解说(可选)"""
        # 获取当前画面
        observation = await self.game.get_observation()
        
        # 可以在这里添加LLM解说
        # 为了节省API调用，暂时用简单的随机语录
        comments = [
            "让我看看当前进度...",
            "游戏运行正常，继续挂机中~",
            "这里有点意思...",
            "耐心等待资源产出中...",
        ]
        
        comment = random.choice(comments)
        logger.info(f"[解说] {comment}")
        return comment
    
    async def perform_auto_task(self, task_name: str) -> bool:
        """
        执行自动化任务
        
        Args:
            task_name: 任务名称 (如 "collect_resources", "daily_checkin")
        """
        tasks = {
            "collect_resources": self._collect_resources,
            "daily_checkin": self._daily_checkin,
            "sort_inventory": self._sort_inventory,
        }
        
        task_func = tasks.get(task_name)
        if task_func:
            return await task_func()
        
        logger.warning(f"未知的自动化任务: {task_name}")
        return False
    
    async def _collect_resources(self) -> bool:
        """收集资源(示例)"""
        logger.info("执行自动收集资源...")
        # 这里可以添加具体的收集逻辑
        return True
    
    async def _daily_checkin(self) -> bool:
        """每日签到(示例)"""
        logger.info("执行每日签到...")
        # 这里可以添加签到逻辑
        return True
    
    async def _sort_inventory(self) -> bool:
        """整理背包"""
        logger.info("自动整理背包...")
        
        # 打开背包
        await self.game.execute_action({"action": "open_inventory"})
        await asyncio.sleep(1)
        
        # 点击整理
        result = await self.game.execute_action({"action": "sort_items"})
        
        # 关闭背包
        await asyncio.sleep(1)
        await self.game.execute_action({"action": "close_inventory"})
        
        return result

"""
自然语言指令解析 - 将观众的话转换为游戏动作
"""
import re
from typing import Dict, List, Optional, Tuple
from loguru import logger


class CommandParser:
    """指令解析器"""
    
    def __init__(self):
        # 指令模式库
        self.patterns = {
            "open_inventory": [
                r"打开背包",
                r"开背包",
                r"看背包",
                r"背包",
                r"inventory",
            ],
            "close_inventory": [
                r"关闭背包",
                r"关背包",
                r"退出背包",
                r"关掉背包",
            ],
            "sort_items": [
                r"整理背包",
                r"排序背包",
                r"整理物品",
                r"排列背包",
                r"sort",
            ],
            "click_menu": [
                r"打开菜单",
                r"点击菜单",
                r"菜单",
                r"menu",
            ],
            "screenshot": [
                r"截图",
                r"拍照",
                r"截个图",
                r"screenshot",
            ],
            "scroll_down": [
                r"向下滚动",
                r"往下翻",
                r"向下翻",
                r"scroll down",
            ],
            "scroll_up": [
                r"向上滚动",
                r"往上翻",
                r"向上翻",
                r"scroll up",
            ],
        }
    
    def parse(self, message: str) -> Optional[Dict]:
        """
        解析消息，提取游戏指令
        
        Returns:
            动作字典或None
        """
        message = message.lower().strip()
        
        for action_name, patterns in self.patterns.items():
            for pattern in patterns:
                if re.search(pattern, message, re.IGNORECASE):
                    return self._action_to_dict(action_name)
        
        return None
    
    def _action_to_dict(self, action_name: str) -> Dict:
        """将动作名转换为动作字典"""
        action_map = {
            "open_inventory": {"action": "open_inventory", "params": {}},
            "close_inventory": {"action": "close_inventory", "params": {}},
            "sort_items": {"action": "sort_items", "params": {}},
            "click_menu": {"action": "click", "params": {"element": "menu_button"}},
            "screenshot": {"action": "screenshot", "params": {}},
            "scroll_down": {"action": "scroll", "params": {"direction": "down", "amount": 3}},
            "scroll_up": {"action": "scroll", "params": {"direction": "up", "amount": 3}},
        }
        
        return action_map.get(action_name, {"action": action_name, "params": {}})
    
    def extract_coordinates(self, message: str) -> Optional[Tuple[int, int]]:
        """
        从消息中提取坐标
        
        Returns:
            (x, y) 或 None
        """
        # 匹配 "100, 200" 或 "(100, 200)" 或 "x=100 y=200"
        patterns = [
            r"(\d+)[,，]\s*(\d+)",
            r"\((\d+)[,，]\s*(\d+)\)",
            r"x[=＝]?(\d+).*?y[=＝]?(\d+)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, message)
            if match:
                return (int(match.group(1)), int(match.group(2)))
        
        return None
    
    def is_game_related(self, message: str) -> bool:
        """判断消息是否与游戏相关"""
        game_keywords = [
            "游戏", "玩", "操作", "点击", "打开", "关闭",
            "背包", "菜单", "物品", "装备", "技能",
            "整理", "排序", "移动", "拖拽", "scroll",
            "inventory", "menu", "item", "click",
        ]
        
        return any(kw in message.lower() for kw in game_keywords)

"""
动作执行器 - 安全层，验证和执行游戏动作
"""
import yaml
from typing import Dict, List, Optional, Any
from pathlib import Path
from enum import Enum
from loguru import logger


class DangerLevel(Enum):
    """危险等级"""
    SAFE = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class ActionExecutor:
    """动作执行器 - 安全验证和执行"""
    
    def __init__(self, game_controller, config_path: str = "config/safety_rules.yaml"):
        self.game_controller = game_controller
        
        # 加载安全规则
        self.safety_rules = self._load_rules(config_path)
        
        # 动作计数器(用于速率限制)
        self.action_count = 0
        self.last_reset = 0  # 需要在外部管理时间
    
    def _load_rules(self, config_path: str) -> Dict:
        """加载安全规则"""
        default_rules = {
            "auto_allow_actions": [
                "click_menu", "open_inventory", "close_inventory",
                "sort_items", "check_status", "move_to", "scroll", "screenshot"
            ],
            "confirm_required_actions": [
                "use_consumable", "sell_item", "discard_item",
                "equip_item", "craft_item"
            ],
            "forbidden_actions": [
                "delete_character", "reset_progress",
                "spend_premium_currency", "confirm_purchase"
            ],
            "limits": {
                "max_actions_per_minute": 30,
                "max_spend_per_session": 0
            }
        }
        
        if Path(config_path).exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                if config and "safety_rules" in config:
                    return config["safety_rules"]
        
        return default_rules
    
    def validate_action(self, action: Dict[str, Any]) -> Tuple[bool, str, DangerLevel]:
        """
        验证动作是否允许执行
        
        Returns:
            (是否允许, 原因, 危险等级)
        """
        action_name = action.get("action", "")
        
        # 检查禁止动作
        forbidden = self.safety_rules.get("forbidden_actions", [])
        if action_name in forbidden:
            return False, f"动作 '{action_name}' 被禁止", DangerLevel.CRITICAL
        
        # 检查需要确认的动作
        confirm_required = self.safety_rules.get("confirm_required_actions", [])
        if action_name in confirm_required:
            return False, f"动作 '{action_name}' 需要确认", DangerLevel.HIGH
        
        # 检查速率限制
        limits = self.safety_rules.get("limits", {})
        max_per_minute = limits.get("max_actions_per_minute", 30)
        
        # 简化的速率检查(实际应该在调用处管理时间窗口)
        if self.action_count >= max_per_minute:
            return False, "动作速率过快，请稍后再试", DangerLevel.MEDIUM
        
        # 检查白名单
        auto_allow = self.safety_rules.get("auto_allow_actions", [])
        if action_name in auto_allow:
            return True, "动作在白名单中", DangerLevel.SAFE
        
        # 未知动作，允许但标记为低风险
        return True, "未知动作，默认允许", DangerLevel.LOW
    
    async def execute(self, action: Dict[str, Any], force: bool = False) -> Dict[str, Any]:
        """
        执行动作(带安全验证)
        
        Args:
            action: 动作定义
            force: 是否跳过验证(危险!)
        
        Returns:
            执行结果
        """
        action_name = action.get("action", "unknown")
        
        # 安全验证
        if not force:
            allowed, reason, danger = self.validate_action(action)
            
            if not allowed and danger == DangerLevel.HIGH:
                # 需要确认 - 返回确认请求
                return {
                    "success": False,
                    "needs_confirmation": True,
                    "action": action,
                    "reason": reason
                }
            
            if not allowed:
                return {
                    "success": False,
                    "error": reason,
                    "danger_level": danger.name
                }
        
        # 执行动作
        try:
            success = await self.game_controller.execute_action(action)
            
            if success:
                self.action_count += 1
                logger.info(f"动作执行成功: {action_name}")
            else:
                logger.warning(f"动作执行失败: {action_name}")
            
            return {
                "success": success,
                "action": action_name,
                "params": action.get("params", {})
            }
            
        except Exception as e:
            logger.error(f"动作执行异常 {action_name}: {e}")
            return {
                "success": False,
                "error": str(e),
                "action": action_name
            }
    
    async def execute_sequence(self, actions: List[Dict[str, Any]], delay: float = 1.0) -> List[Dict[str, Any]]:
        """
        按顺序执行多个动作
        
        Args:
            actions: 动作列表
            delay: 动作间延迟(秒)
        """
        results = []
        
        for action in actions:
            result = await self.execute(action)
            results.append(result)
            
            if not result.get("success"):
                logger.warning(f"序列中断: 动作 {action.get('action')} 失败")
                break
            
            if delay > 0:
                import asyncio
                await asyncio.sleep(delay)
        
        return results
    
    def reset_counter(self):
        """重置动作计数器(每分钟调用一次)"""
        self.action_count = 0
    
    def get_stats(self) -> Dict[str, Any]:
        """获取执行统计"""
        limits = self.safety_rules.get("limits", {})
        return {
            "actions_this_minute": self.action_count,
            "max_per_minute": limits.get("max_actions_per_minute", 30),
            "remaining": limits.get("max_actions_per_minute", 30) - self.action_count
        }


# 修复导入
from typing import Tuple

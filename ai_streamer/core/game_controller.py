"""
游戏控制器 - Playwright自动化控制
"""
import asyncio
import yaml
from typing import Optional, Dict, Any, Tuple
from pathlib import Path
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from loguru import logger


class GameController:
    """游戏控制器 - 管理浏览器和游戏交互"""
    
    def __init__(self, config_path: str = "config/game_selectors.yaml"):
        self.config_path = config_path
        self.selectors: Dict[str, Any] = {}
        self.current_game: Optional[str] = None
        
        # Playwright实例
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        
        self._load_selectors()
    
    def _load_selectors(self):
        """加载游戏选择器配置"""
        if Path(self.config_path).exists():
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                self.selectors = config.get("games", {})
    
    async def start(self, headless: bool = False, user_data_dir: str = "browser_session"):
        """启动浏览器"""
        self.playwright = await async_playwright().start()
        
        # 启动浏览器(持久化上下文保存登录状态)
        self.browser = await self.playwright.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=headless,
            viewport={"width": 1920, "height": 1080},
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage"
            ]
        )
        
        self.page = await self.browser.new_page()
        
        # 隐藏webdriver特征
        await self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        
        logger.info("浏览器启动完成")
    
    async def navigate_to_game(self, game_key: str):
        """导航到指定游戏"""
        if game_key not in self.selectors:
            raise ValueError(f"未知的游戏: {game_key}")
        
        game_config = self.selectors[game_key]
        url = game_config.get("url")
        
        if not url:
            raise ValueError(f"游戏 {game_key} 未配置URL")
        
        self.current_game = game_key
        
        await self.page.goto(url, wait_until="networkidle")
        logger.info(f"已导航到游戏: {game_config.get('name', game_key)}")
        
        # 等待游戏加载
        await asyncio.sleep(3)
    
    async def get_observation(self) -> Dict[str, Any]:
        """获取当前游戏画面观察"""
        if not self.page:
            return {"error": "浏览器未启动"}
        
        # 截图
        screenshot_path = "data/logs/current_screen.png"
        await self.page.screenshot(path=screenshot_path, full_page=False)
        
        # 获取页面信息
        title = await self.page.title()
        url = self.page.url
        
        return {
            "screenshot_path": screenshot_path,
            "title": title,
            "url": url,
            "game": self.current_game
        }
    
    async def execute_action(self, action: Dict[str, Any]) -> bool:
        """
        执行游戏动作
        
        Args:
            action: {"action": "动作名", "params": {...}}
        
        Returns:
            是否成功
        """
        if not self.page or not self.current_game:
            logger.error("游戏未启动")
            return False
        
        action_name = action.get("action")
        params = action.get("params", {})
        
        game_config = self.selectors.get(self.current_game, {})
        selectors = game_config.get("selectors", {})
        
        try:
            if action_name == "click":
                selector = params.get("selector") or selectors.get(params.get("element"))
                if selector:
                    await self.page.click(selector)
                    logger.info(f"点击元素: {selector}")
                    return True
            
            elif action_name == "click_at":
                x = params.get("x", 0)
                y = params.get("y", 0)
                await self.page.mouse.click(x, y)
                logger.info(f"点击坐标: ({x}, {y})")
                return True
            
            elif action_name == "open_inventory":
                selector = selectors.get("inventory", {}).get("open")
                if selector:
                    await self.page.click(selector)
                    logger.info("打开背包")
                    await asyncio.sleep(1)
                    return True
            
            elif action_name == "close_inventory":
                selector = selectors.get("inventory", {}).get("close")
                if selector:
                    await self.page.click(selector)
                    logger.info("关闭背包")
                    return True
            
            elif action_name == "sort_items":
                selector = selectors.get("inventory", {}).get("sort_button")
                if selector:
                    await self.page.click(selector)
                    logger.info("整理背包")
                    return True
            
            elif action_name == "scroll":
                direction = params.get("direction", "down")
                amount = params.get("amount", 3)
                delta = 300 if direction == "down" else -300
                for _ in range(amount):
                    await self.page.mouse.wheel(0, delta)
                    await asyncio.sleep(0.1)
                logger.info(f"滚动: {direction} x{amount}")
                return True
            
            elif action_name == "drag":
                from_x = params.get("from_x", 0)
                from_y = params.get("from_y", 0)
                to_x = params.get("to_x", 0)
                to_y = params.get("to_y", 0)
                
                await self.page.mouse.move(from_x, from_y)
                await self.page.mouse.down()
                await asyncio.sleep(0.2)
                await self.page.mouse.move(to_x, to_y)
                await self.page.mouse.up()
                logger.info(f"拖拽: ({from_x},{from_y}) -> ({to_x},{to_y})")
                return True
            
            elif action_name == "type":
                selector = params.get("selector")
                text = params.get("text", "")
                if selector:
                    await self.page.fill(selector, text)
                    logger.info(f"输入文本: {text}")
                    return True
            
            elif action_name == "press":
                key = params.get("key")
                if key:
                    await self.page.keyboard.press(key)
                    logger.info(f"按键: {key}")
                    return True
            
            elif action_name == "screenshot":
                path = params.get("path", "data/logs/action_screenshot.png")
                await self.page.screenshot(path=path)
                logger.info(f"截图保存: {path}")
                return True
            
            else:
                logger.warning(f"未知的动作: {action_name}")
                return False
        
        except Exception as e:
            logger.error(f"执行动作失败 {action_name}: {e}")
            return False
        
        return False
    
    async def get_clickable_elements(self) -> list:
        """获取页面上可点击的元素列表(用于LLM决策)"""
        if not self.page:
            return []
        
        elements = await self.page.query_selector_all("button, a, [role='button'], [onclick]")
        element_info = []
        
        for i, elem in enumerate(elements[:20]):  # 限制数量
            try:
                text = await elem.text_content()
                tag = await elem.evaluate("el => el.tagName")
                visible = await elem.is_visible()
                if visible and text:
                    element_info.append({
                        "index": i,
                        "tag": tag,
                        "text": text.strip()[:50]
                    })
            except:
                pass
        
        return element_info
    
    async def close(self):
        """关闭浏览器"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        logger.info("浏览器已关闭")

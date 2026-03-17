"""
VTube Studio 控制 - 通过OSC和热键控制Live2D模型

需要先在VTube Studio中开启OSC:
1. 打开VTube Studio
2. Settings -> Network -> OSC
3. Enable OSC = ON
4. Port = 8001 (默认)

热键控制更可靠，需要在VTube Studio中先绑定热键:
1. Settings -> Hotkeys
2. 为每个表情/动作设置键盘快捷键
3. 在下面的KEY_MAP中配置对应的按键
"""
import asyncio
import random
import time
from pythonosc import udp_client
from pynput.keyboard import Controller, Key
from typing import Optional, Dict, List
from loguru import logger


class VTubeStudioController:
    """VTube Studio控制器"""
    
    # 热键映射 - 在VTube Studio里设置好这些快捷键
    KEY_MAP = {
        "happy": "f1",      # 开心表情
        "sad": "f2",        # 难过表情
        "surprised": "f3",  # 惊讶表情
        "angry": "f4",      # 生气表情
        "neutral": "f5",    # 默认表情
        "laugh": "f6",      # 笑声动画
        "wave": "f7",       # 挥手动画
        "dance": "f8",      # 跳舞动画
    }
    
    def __init__(self, ip: str = "127.0.0.1", port: int = 8001, use_hotkeys: bool = True):
        self.ip = ip
        self.port = port
        self.use_hotkeys = use_hotkeys
        self.enabled = True
        
        # OSC客户端
        self.osc_client: Optional[udp_client.SimpleUDPClient] = None
        
        # 键盘控制器(用于热键)
        self.keyboard = Controller()
        
        # 当前状态
        self.current_expression = "neutral"
        self.talking = False
        
        self._connect_osc()
    
    def _connect_osc(self):
        """连接OSC"""
        try:
            self.osc_client = udp_client.SimpleUDPClient(self.ip, self.port)
            logger.info(f"✓ VTube Studio OSC: {self.ip}:{self.port}")
        except Exception as e:
            logger.warning(f"✗ OSC连接失败: {e}")
    
    # ==================== 表情控制 ====================
    
    def set_expression(self, expression: str, duration: float = 2.0):
        """
        设置表情
        
        Args:
            expression: happy/sad/surprised/angry/neutral
            duration: 表情持续时间(秒)，0表示永久
        """
        if not self.enabled:
            return
        
        expression = expression.lower()
        self.current_expression = expression
        
        # 方法1: 热键触发(更可靠)
        if self.use_hotkeys:
            key = self.KEY_MAP.get(expression)
            if key:
                self._press_key(key)
                logger.debug(f"表情: {expression}")
        
        # 方法2: OSC触发(如果VTube Studio配置了OSC接收)
        elif self.osc_client:
            # VTube Studio OSC格式
            self.osc_client.send_message(
                "/VTubeStudio/Hotkey", 
                [expression]
            )
        
        # 自动恢复默认表情
        if duration > 0 and expression != "neutral":
            asyncio.create_task(self._reset_expression_after(duration))
    
    def _press_key(self, key: str):
        """模拟按键"""
        try:
            if key.startswith("f") and key[1:].isdigit():
                # F1-F12
                func_key = getattr(Key, key)
                self.keyboard.press(func_key)
                self.keyboard.release(func_key)
            else:
                self.keyboard.press(key)
                self.keyboard.release(key)
        except Exception as e:
            logger.warning(f"按键失败 {key}: {e}")
    
    async def _reset_expression_after(self, seconds: float):
        """几秒后恢复默认表情"""
        await asyncio.sleep(seconds)
        if self.current_expression != "neutral":
            self.set_expression("neutral", duration=0)
    
    # ==================== 动画触发 ====================
    
    def trigger_animation(self, animation: str):
        """
        触发动画
        
        Args:
            animation: laugh/wave/dance/...
        """
        if not self.enabled:
            return
        
        key = self.KEY_MAP.get(animation)
        if key:
            self._press_key(key)
            logger.debug(f"动画: {animation}")
    
    def toggle_animation(self, animation: str):
        """开关循环动画"""
        self.trigger_animation(animation)
    
    # ==================== 口型同步 ====================
    
    def start_talking(self):
        """开始说话 - 嘴巴动起来"""
        self.talking = True
        asyncio.create_task(self._talking_loop())
    
    def stop_talking(self):
        """停止说话"""
        self.talking = False
    
    async def _talking_loop(self):
        """说话时的嘴巴动画循环"""
        while self.talking:
            # 模拟说话 - 随机嘴巴开合
            if self.osc_client:
                openness = random.uniform(0.3, 0.8)
                self.osc_client.send_message(
                    "/VMC/Ext/Blend/Val", 
                    ["JawOpen", openness]
                )
            await asyncio.sleep(0.1)
        
        # 闭嘴
        if self.osc_client:
            self.osc_client.send_message(
                "/VMC/Ext/Blend/Val", 
                ["JawOpen", 0.0]
            )
    
    # ==================== 移动控制 ====================
    
    def move_to(self, x: float = 0.0, y: float = 0.0, rotation: float = 0.0):
        """
        移动模型位置
        
        Args:
            x: 左右位置 (-1.0 左 ~ 1.0 右)
            y: 上下位置 (-1.0 下 ~ 1.0 上)
            rotation: 旋转角度 (度)
        """
        if not self.osc_client:
            return
        
        # VTube Studio OSC位置控制
        self.osc_client.send_message("/VMC/Ext/Root/Pos", [x, y, 1.0])
        self.osc_client.send_message("/VMC/Ext/Root/Rot", [0.0, 0.0, rotation])
    
    def look_at(self, x: float = 0.0, y: float = 0.0):
        """
        看向某个方向
        
        Args:
            x: -1.0 (左) ~ 1.0 (右)
            y: -1.0 (下) ~ 1.0 (上)
        """
        if not self.osc_client:
            return
        
        self.osc_client.send_message(
            "/VMC/Ext/Blend/Val",
            ["EyeLeftX", x]
        )
        self.osc_client.send_message(
            "/VMC/Ext/Blend/Val",
            ["EyeLeftY", y]
        )
    
    def set_mouth_open(self, value: float):
        """
        设置嘴巴张开程度(用于口型同步)
        
        Args:
            value: 0.0(闭嘴) - 1.0(最大张开)
        """
        if not self.enabled or not self.osc_client:
            return
        
        try:
            # VMC协议 - 控制BlendShape
            self.osc_client.send_message(
                "/VMC/Ext/Blend/Val",
                ["JawOpen", float(value)]
            )
            # 同时控制嘴巴张开
            self.osc_client.send_message(
                "/VMC/Ext/Blend/Val",
                ["MouthOpen", float(value) * 0.8]  # 稍微小一点更自然
            )
            # 嘴唇分离
            self.osc_client.send_message(
                "/VMC/Ext/Blend/Val",
                ["MouthUpperUp", float(value) * 0.3]
            )
        except Exception as e:
            pass  # OSC失败静默处理
    
    def bounce(self, intensity: float = 1.0):
        """弹跳一下"""
        asyncio.create_task(self._bounce_animation(intensity))
    
    async def _bounce_animation(self, intensity: float):
        """弹跳动画"""
        if not self.osc_client:
            return
        
        # 向上
        for i in range(5):
            y = -0.1 * intensity * (5 - i) / 5
            self.osc_client.send_message("/VMC/Ext/Root/Pos", [0.0, y, 1.0])
            await asyncio.sleep(0.02)
        
        # 向下回弹
        for i in range(5):
            y = 0.05 * intensity * i / 5
            self.osc_client.send_message("/VMC/Ext/Root/Pos", [0.0, y, 1.0])
            await asyncio.sleep(0.02)
        
        # 复位
        self.osc_client.send_message("/VMC/Ext/Root/Pos", [0.0, 0.0, 1.0])
    
    # ==================== 智能反应 ====================
    
    def react_to_message(self, message: str):
        """
        根据消息内容自动反应
        
        Args:
            message: 弹幕/消息内容
        """
        message = message.lower()
        
        # 情绪识别
        happy_words = ["哈哈", "好笑", "哈哈", "😂", "嘻嘻", "开心", "棒", "赞", "牛"]
        sad_words = ["难过", "伤心", "哭", "😢", "呜呜", "惨", "输了"]
        surprised_words = ["惊讶", "哇", "!?", "!!", "卧槽", "wc", "什么", "真的吗"]
        angry_words = ["生气", "讨厌", "烦", "😠", "气死", "坑爹"]
        
        if any(w in message for w in happy_words):
            self.set_expression("happy")
            self.trigger_animation("laugh")
            self.bounce(0.5)
            
        elif any(w in message for w in surprised_words):
            self.set_expression("surprised")
            self.bounce(1.0)
            
        elif any(w in message for w in sad_words):
            self.set_expression("sad")
            
        elif any(w in message for w in angry_words):
            self.set_expression("angry")
            
        else:
            # 默认反应 - 偶尔眨眼/点头
            if random.random() < 0.3:
                self.set_expression("neutral")
    
    def random_idle_animation(self):
        """随机待机动作"""
        animations = [
            lambda: self.set_expression("neutral"),
            lambda: self.look_at(random.uniform(-0.3, 0.3), random.uniform(-0.2, 0.2)),
            lambda: self.trigger_animation("wave"),
        ]
        random.choice(animations)()
    
    # ==================== 测试 ====================
    
    async def test_all(self):
        """测试所有表情和动作"""
        logger.info("测试VTube Studio控制...")
        
        expressions = ["happy", "sad", "surprised", "angry", "neutral"]
        
        for expr in expressions:
            logger.info(f"表情: {expr}")
            self.set_expression(expr)
            await asyncio.sleep(1)
        
        logger.info("测试动画...")
        for anim in ["laugh", "wave"]:
            self.trigger_animation(anim)
            await asyncio.sleep(1)
        
        logger.info("测试弹跳...")
        self.bounce()
        await asyncio.sleep(1)
        
        logger.info("测试完成!")


# 独立测试
if __name__ == "__main__":
    async def main():
        vtube = VTubeStudioController(use_hotkeys=True)
        
        print("\n3秒后开始测试VTube Studio控制...")
        print("请确保VTube Studio已打开，并且设置了对应的热键\n")
        
        await asyncio.sleep(3)
        await vtube.test_all()
    
    asyncio.run(main())

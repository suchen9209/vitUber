"""
LLM API客户端 - 支持Claude和Kimi
"""
import os
import yaml
from typing import List, Dict, Optional
from dataclasses import dataclass
from loguru import logger


@dataclass
class ChatResponse:
    """聊天响应"""
    text: str
    actions: List[Dict]  # 提取的动作
    facts: List[str]     # 提取的事实


class LLMClient:
    """LLM客户端 - 支持多模型"""
    
    def __init__(self, config_path: str = "config/api_keys.yaml"):
        # 加载配置
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # 优先使用Kimi，如果没有则使用Claude
        kimi_config = config.get("kimi", {})
        anthropic_config = config.get("anthropic", {})
        
        # 检测使用哪个模型
        kimi_key = kimi_config.get("api_key", os.getenv("KIMI_API_KEY"))
        claude_key = anthropic_config.get("api_key", os.getenv("ANTHROPIC_API_KEY"))
        
        if kimi_key and kimi_key != "YOUR_KIMI_API_KEY_HERE":
            self.provider = "kimi"
            self.api_key = kimi_key
            self.model = kimi_config.get("model", "kimi-k2-5")
            self.base_url = kimi_config.get("base_url", "https://api.moonshot.cn/v1")
            self._init_kimi()
            logger.info(f"✓ LLM客户端: Kimi ({self.model})")
            
        elif claude_key and claude_key != "YOUR_ANTHROPIC_API_KEY_HERE":
            self.provider = "claude"
            self.api_key = claude_key
            self.model = anthropic_config.get("model", "claude-3-5-sonnet-20241022")
            self._init_claude()
            logger.info(f"✓ LLM客户端: Claude ({self.model})")
        else:
            raise ValueError("请配置API密钥! 支持Kimi或Claude，在config/api_keys.yaml中设置")
        
        self.max_tokens = config.get("max_tokens", 1024)
        self.temperature = config.get("temperature", 0.7)
    
    def _init_kimi(self):
        """初始化Kimi客户端 (OpenAI兼容格式)"""
        try:
            from openai import OpenAI
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
        except ImportError:
            raise ImportError("请安装openai: pip install openai")
    
    def _init_claude(self):
        """初始化Claude客户端"""
        try:
            from anthropic import Anthropic
            self.client = Anthropic(api_key=self.api_key)
        except ImportError:
            raise ImportError("请安装anthropic: pip install anthropic")
    
    def _build_system_prompt(self) -> str:
        """构建系统提示词"""
        return """你是一个AI虚拟主播，正在B站进行24小时游戏直播。

你的角色特点:
- 友好、幽默，偶尔会吐槽
- 会认真回应观众的问题
- 玩游戏时会解释自己的操作思路
- 记住常来的观众，能叫出他们的名字

指令格式:
当观众想要你执行游戏操作时，请用以下格式回复:
[ACTION: {"action": "动作名", "params": {...}}]

可用动作:
- click_menu: 点击菜单
- open_inventory: 打开背包
- close_inventory: 关闭背包
- sort_items: 整理背包
- click_at: 在指定坐标点击 {"x": 100, "y": 200}
- scroll: 滚动页面 {"direction": "up/down", "amount": 3}

事实提取:
如果观众提到了关于自己的信息(如"我喜欢玩法师"、"我是学生"等)，请在回复末尾添加:
[FACT: 提取的事实内容]

例如:
观众: "帮我整理一下背包"
回复: "好的，我来帮你整理背包！[ACTION: {"action": "open_inventory"}] 打开背包...[ACTION: {"action": "sort_items"}] 整理完成！"
"""
    
    def chat(self, message: str, user_context: str = "", chat_history: List[Dict] = None) -> ChatResponse:
        """与LLM对话"""
        if chat_history is None:
            chat_history = []
        
        # 构建当前消息(添加上下文)
        full_message = f"{user_context}\n\n观众弹幕: {message}" if user_context else message
        
        try:
            if self.provider == "kimi":
                response = self._chat_kimi(full_message, chat_history)
            else:
                response = self._chat_claude(full_message, chat_history)
            
            # 解析动作和事实
            actions = self._extract_actions(response)
            facts = self._extract_facts(response)
            clean_text = self._clean_response(response)
            
            return ChatResponse(
                text=clean_text,
                actions=actions,
                facts=facts
            )
            
        except Exception as e:
            logger.error(f"LLM调用失败: {e}")
            return ChatResponse(
                text="哎呀，我卡住了，让我缓缓...",
                actions=[],
                facts=[]
            )
    
    def _chat_kimi(self, message: str, chat_history: List[Dict]) -> str:
        """调用Kimi API"""
        messages = [{"role": "system", "content": self._build_system_prompt()}]
        
        # 添加历史
        for msg in chat_history[-10:]:
            messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")
            })
        
        messages.append({"role": "user", "content": message})
        
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=self.max_tokens,
            temperature=self.temperature
        )
        
        return completion.choices[0].message.content
    
    def _chat_claude(self, message: str, chat_history: List[Dict]) -> str:
        """调用Claude API"""
        messages = []
        
        for msg in chat_history[-10:]:
            messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")
            })
        
        messages.append({"role": "user", "content": message})
        
        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            system=self._build_system_prompt(),
            messages=messages
        )
        
        return response.content[0].text
    
    def _extract_actions(self, text: str) -> List[Dict]:
        """从响应中提取动作指令"""
        import re
        actions = []
        
        pattern = r'\[ACTION:\s*(\{.*?\})\]'
        matches = re.findall(pattern, text, re.DOTALL)
        
        for match in matches:
            try:
                import json
                action_data = json.loads(match)
                actions.append(action_data)
            except json.JSONDecodeError:
                logger.warning(f"无法解析动作: {match}")
        
        return actions
    
    def _extract_facts(self, text: str) -> List[str]:
        """从响应中提取事实"""
        import re
        facts = []
        
        pattern = r'\[FACT:\s*(.+?)\]'
        matches = re.findall(pattern, text)
        
        for match in matches:
            facts.append(match.strip())
        
        return facts
    
    def _clean_response(self, text: str) -> str:
        """清理响应文本，移除标记"""
        import re
        
        text = re.sub(r'\[ACTION:\s*\{.*?\}\]', '', text, flags=re.DOTALL)
        text = re.sub(r'\[FACT:\s*.+?\]', '', text)
        
        return text.strip()
    
    def generate_observation_summary(self, screenshot_desc: str, game_state: str) -> str:
        """生成游戏观察总结"""
        prompt = f"""作为主播，简单描述一下当前游戏画面:

游戏状态: {game_state}
画面描述: {screenshot_desc}

用1-2句话描述你在做什么，语气自然。"""
        
        try:
            if self.provider == "kimi":
                completion = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=200,
                    temperature=0.7
                )
                return completion.choices[0].message.content.strip()
            else:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=200,
                    temperature=0.7,
                    messages=[{"role": "user", "content": prompt}]
                )
                return response.content[0].text.strip()
        except Exception as e:
            logger.error(f"生成观察总结失败: {e}")
            return "让我看看..."

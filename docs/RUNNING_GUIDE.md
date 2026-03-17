# 🎭 AI虚拟主播 - 完整运行指南

> 从启动到运行的全流程说明

---

## 📋 目录

1. [项目架构](#1-项目架构)
2. [启动命令](#2-启动命令)
3. [运行时的进程](#3-运行时的进程)
4. [弹幕监听 → 记忆回答](#4-弹幕监听--记忆回答)
5. [自发说话机制](#5-自发说话机制)
6. [语音接入](#6-语音接入)
7. [语音和任务模型联动](#7-语音和任务模型联动)
8. [OBS/VTube Studio联动](#8-obsvtube-studio联动)
9. [缺少什么](#9-缺少什么)

---

## 1. 项目架构

```
┌─────────────────────────────────────────────────────────────┐
│                     用户视角                                  │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐              │
│  │  B站直播间 │<───>│  OBS画面  │<───>│ 听到声音  │              │
│  └────┬─────┘    └──────────┘    └──────────┘              │
└───────┼─────────────────────────────────────────────────────┘
        │
        │ 弹幕WebSocket
        ▼
┌─────────────────────────────────────────────────────────────┐
│                    AI Streamer Core                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ BilibiliDanmaku│  │ MemoryManager │  │  LLMClient   │      │
│  │   弹幕监听    │  │  用户档案    │  │  Claude/API  │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                │                 │               │
│         └────────────────┼─────────────────┘               │
│                          ▼                                 │
│                   ┌──────────────┐                         │
│                   │  LiveSession │                         │
│                   │   直播会话   │                         │
│                   └──────┬───────┘                         │
│                          │                                 │
│  ┌───────────────────────┼───────────────────────┐        │
│  │                       ▼                       │        │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐│        │
│  │  │MemoryBridge  │  │CompanionMode │  │GameController││        │
│  │  │  记忆桥接    │  │  陪伴模式    │  │  游戏控制    ││        │
│  │  │ 读热梗/新闻  │  │ 自发说话    │  │ 网页自动化   ││        │
│  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘│        │
│  │         │                │                │         │        │
│  │         └────────────────┼────────────────┘         │        │
│  │                          ▼                          │        │
│  │                   ┌──────────────┐                  │        │
│  │                   │   TTSEngine  │                  │        │
│  │                   │  语音合成    │                  │        │
│  │                   │ Edge/GPT-SoVITS│                │        │
│  │                   └──────┬───────┘                  │        │
│  │                          │                          │        │
│  │                          ▼                          │        │
│  │                   ┌──────────────┐                  │        │
│  │                   │VTubeStudio   │                  │        │
│  │                   │  口型同步    │                  │        │
│  │                   └──────────────┘                  │        │
│  └─────────────────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────────────┘
        │
        │ 音频输出
        ▼
┌─────────────────────────────────────────────────────────────┐
│                    外部系统                                   │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐              │
│  │ 扬声器/耳机│    │ OBS音频源 │    │ VTube Studio│              │
│  └──────────┘    └──────────┘    └──────────┘              │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. 启动命令

### 2.1 环境准备（首次运行）

```bash
# 1. 进入项目目录
cd /path/to/vitUber

# 2. 安装Python依赖
pip install -r ai_streamer/requirements.txt

# 3. 安装Playwright浏览器（用于游戏控制）
playwright install chromium

# 4. 配置API密钥
cp ai_streamer/config/api_keys.yaml.example ai_streamer/config/api_keys.yaml
# 编辑 api_keys.yaml，填入你的Anthropic API Key

# 5. 初始化记忆系统（可选，如果memory目录已存在）
cd ai_streamer
python scripts/init_memory.py
```

### 2.2 运行命令

```bash
cd ai_streamer

# 方式1: 纯聊天模式（推荐先测试这个）
python main.py --room 你的房间号

# 方式2: 带游戏控制
python main.py --room 你的房间号 --game generic_web_game

# 方式3: 测试模式（不连接真实弹幕，手动输入测试）
python main.py --room 123456 --test

# 方式4: 无头模式（不显示浏览器窗口）
python main.py --room 你的房间号 --game generic_web_game --headless

# 方式5: 后台运行（Linux/Mac）
nohup python main.py --room 你的房间号 > logs/stream.log 2>&1 &
echo $! > stream.pid  # 保存PID用于后续停止
```

### 2.3 停止运行

```bash
# 如果是前台运行
# 按 Ctrl+C

# 如果是后台运行
kill $(cat stream.pid)
```

---

## 3. 运行时的进程

### 3.1 主进程结构

```python
# main.py 启动后创建的核心对象
AIStreamer
├── MemoryManager          # 用户档案管理 (JSON文件存储)
├── LLMClient             # Claude API客户端
├── GameController        # Playwright浏览器控制
├── ActionExecutor        # 安全执行游戏动作
├── LiveSession           # 直播会话协调器
├── BilibiliDanmaku       # WebSocket弹幕监听
├── TTSEngine             # TTS语音合成
├── VTubeStudioController # VTube Studio口型同步
├── ChatHandler           # 聊天处理
├── GameAutomation        # 游戏自动化
└── CommandParser         # 指令解析
```

### 3.2 运行时线程/任务

| 任务名称 | 类型 | 说明 |
|---------|------|------|
| `WebSocket连接` | asyncio Task | 维持B站弹幕WebSocket连接 |
| `心跳保持` | asyncio Task | 每30秒发送一次心跳包 |
| `弹幕监听` | asyncio Task | 解析并分发弹幕消息 |
| `游戏自动化` | asyncio Task | 游戏空闲时的自动操作 |
| `陪伴模式` | asyncio Task | 🆕 无人时自发说话 |
| `整点播报` | asyncio Task | 🆕 每小时准点播报 |
| `口型同步` | threading.Thread | TTS播放时的嘴型动画 |

### 3.3 检查运行状态

```bash
# 查看Python进程
ps aux | grep "main.py"

# 查看日志
tail -f ai_streamer/data/logs/ai_streamer.log

# 查看WebSocket连接状态（需要安装websocat）
websocat ws://localhost:你的调试端口
```

---

## 4. 弹幕监听 → 记忆回答

### 4.1 完整流程

```
用户发弹幕
    │
    ▼
BilibiliDanmaku._on_danmaku()
    │
    ├── 1. 解析是否为指令（CommandParser）
    │      ├── 是指令 → ActionExecutor执行 → TTS播报结果
    │      └── 不是指令 → 进入聊天流程
    │
    └── 2. LiveSession.handle_danmaku()
           │
           ├── 2.1 更新用户记忆
           │      MemoryManager.get_user(user_id)
           │      MemoryManager.update_user(profile)
           │
           ├── 2.2 构建LLM上下文
           │      memory_manager.get_context_for_llm()
           │      + 当前弹幕
           │      + 历史对话
           │
           ├── 2.3 调用Claude生成回复
           │      LLMClient.chat()
           │
           └── 2.4 TTS播报 + VTube表情
                  TTSEngine.speak()
                  VTubeStudio.react_to_message()
```

### 4.2 记忆系统如何回答

#### A. 用户档案匹配

```python
# 当用户 "小明" 第一次发弹幕
user = memory_manager.get_user("12345", "小明")
# 返回: UserProfile(user_id="12345", username="小明", facts=[], join_count=0)

# 当用户 "小明" 第5次发弹幕
user = memory_manager.get_user("12345", "小明")  
# 返回: UserProfile(user_id="12345", username="小明", facts=["喜欢玩游戏", "是学生"], join_count=5)
```

#### B. LLM上下文注入

```python
# 发给Claude的prompt示例
context = """
当前用户: 小明 (regular)
已知信息:
  - 喜欢玩游戏
  - 是学生
  - 上次来过是昨天

历史对话:
  小明: 主播好
  AI: 你好小明，又来啦？
  
当前弹幕: 今天玩什么游戏？
"""

response = llm.chat(context)
```

#### C. 记忆写入

```python
# 从LLM回复中提取事实，自动记忆
if "我还是学生" in user_message:
    memory_manager.add_fact(user_id, "是学生", username)
```

### 4.3 如何使用热梗回答

#### 已接入：MemoryBridge自动读取

```python
# 在LiveSession中
from core.memory_bridge import get_memory_bridge

class LiveSession:
    def __init__(self, ...):
        self.memory_bridge = get_memory_bridge()
    
    async def generate_reply(self, message):
        # 随机融入热梗
        if random.random() < 0.3:  # 30%概率
            meme = self.memory_bridge.get_random_meme()
            prompt += f"\n可以适当使用这个热梗: {meme['name']} - {meme['meaning']}"
        
        return await self.llm.chat(prompt)
```

---

## 5. 自发说话机制

### 5.1 触发条件

```python
# core/companion_mode.py

class SilentContentGenerator:
    def should_generate_content(self):
        silence = self.get_silence_duration()
        
        # 情况1: 沉默<1分钟
        if silence < 60:
            return False  # 不说话
        
        # 情况2: 沉默1-5分钟
        elif silence < 300:
            return random.random() < 0.1  # 10%概率碎碎念
        
        # 情况3: 沉默5-15分钟  
        elif silence < 900:
            return random.random() < 0.3  # 30%概率说热梗/事件
        
        # 情况4: 沉默>15分钟
        else:
            return True  # 必须说点什么
```

### 5.2 说话内容来源

| 沉默时长 | 内容类型 | 示例 |
|---------|---------|------|
| 1-5分钟 | 陪伴碎碎念 | "还在吗？" "今天过得怎么样？" |
| 5-15分钟 | 热梗分享 | "刚学到一个梗——做完你的，做你的..." |
| 15分钟+ | 热点事件 | "刚看到个消息——OpenClaw被安全预警..." |
| 整点 | 报时+陪伴语 | "14点了，该休息一下了" |

### 5.3 如何启动

```python
# 在main.py中已集成

class AIStreamer:
    async def initialize(self):
        # ...其他初始化...
        
        # 🆕 启动陪伴模式
        from core.companion_mode import create_companion_mode
        
        self.companion = create_companion_mode(
            tts_callback=self.tts.speak,          # TTS播报
            danmaku_callback=self._send_danmaku   # 可选：同时发弹幕
        )
        
        # 在后台运行
        asyncio.create_task(self.companion.start())
    
    async def _on_danmaku(self, user_id, username, message):
        # 🆕 用户发弹幕时重置沉默计时
        if hasattr(self, 'companion'):
            self.companion.on_user_interaction()
        
        # ...原有处理逻辑...
```

---

## 6. 语音接入

### 6.1 当前支持的TTS引擎

| 引擎 | 质量 | 延迟 | 配置方式 | 适用场景 |
|------|------|------|---------|---------|
| **Edge TTS** | 中 | 低 | 开箱即用 | 快速测试、日常直播 |
| **GPT-SoVITS** | 高 | 中 | 需本地部署 | 固定音色、高质量 |

### 6.2 Edge TTS（默认）

```bash
# 无需额外安装，已经包含在requirements.txt中
# 使用微软Azure语音服务，免费

# 配置音色（config/api_keys.yaml）
tts:
  engine: "edge"
  edge_voice: "zh-CN-XiaoxiaoNeural"  # 女声
  # 其他选项: zh-CN-YunxiNeural(男声), zh-CN-XiaoyiNeural(童声)
```

### 6.3 GPT-SoVITS（推荐）

```bash
# 1. 克隆GPT-SoVITS仓库
git clone https://github.com/RVC-Boss/GPT-SoVITS.git
cd GPT-SoVITS

# 2. 安装依赖
pip install -r requirements.txt

# 3. 下载预训练模型
# 按仓库说明下载模型文件

# 4. 启动API服务
python api.py
# 服务会在 http://localhost:9880 启动

# 5. 配置ai_streamer
# config/api_keys.yaml:
tts:
  engine: "gpt_sovits"
  gpt_sovits_url: "http://localhost:9880"
```

### 6.4 添加新的TTS引擎

```python
# interfaces/tts_engine.py

class TTSEngine:
    async def synthesize(self, text: str, output_path: str) -> str:
        if self.engine_type == "edge":
            return await self._edge_tts(text, output_path)
        elif self.engine_type == "gpt_sovits":
            return await self._gpt_sovits(text, output_path)
        elif self.engine_type == "your_engine":  # 🆕 新增
            return await self._your_engine(text, output_path)
    
    async def _your_engine(self, text: str, output_path: str) -> str:
        # 调用你的TTS API
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "http://your-tts-api/tts",
                json={"text": text}
            ) as resp:
                audio_data = await resp.read()
                with open(output_path, "wb") as f:
                    f.write(audio_data)
                return output_path
```

---

## 7. 语音和任务模型联动

### 7.1 当前联动方式

```
弹幕/任务触发
    │
    ▼
生成回复文本
    │
    ├── 文本包含动作指令（如"截图看看"）
    │      │
    │      ├── GameController执行动作
    │      └── 执行完成后TTS播报结果
    │
    └── 纯聊天文本
           │
           └── TTSEngine.speak()
                │
                ├── 1. 合成音频文件
                ├── 2. 分析音量包络
                ├── 3. 播放音频
                └── 4. 同步发送嘴型数据给VTube Studio
```

### 7.2 口型同步原理

```python
# TTSEngine._play_with_lip_sync()

1. 音频分析
   - 将MP3转为WAV
   - 计算每帧的RMS音量
   - 归一化到 0.1-1.0（嘴型开合度）

2. 播放同步
   - 主线程：播放音频
   - 子线程：按时间线发送嘴型数据
   
   time: 0ms    100ms   200ms   300ms...
   mouth: 0.2   0.5     0.8     0.3...
          │      │       │       │
          ▼      ▼       ▼       ▼
   VTubeStudio.set_mouth_open(value)
```

### 7.3 复杂任务联动示例

```python
# 用户说: "帮我整理背包，然后告诉我有什么装备"

async def handle_complex_task(user_message):
    # 1. 解析意图
    if "整理背包" in user_message:
        # 2. 执行游戏动作
        result = await game_controller.click("背包按钮")
        await game_controller.click("整理按钮")
        
        # 3. 截图识别
        screenshot = await game_controller.screenshot()
        items = await llm.vision("识别背包里的装备", screenshot)
        
        # 4. 生成语音回复
        reply = f"整理好了，你有: {items}"
        await tts_engine.speak(reply)
        
        # 5. VTube表情
        vtube.react_to_message("开心" if "好装备" in items else "普通")
```

---

## 8. OBS/VTube Studio联动

### 8.1 VTube Studio连接

```python
# interfaces/vtube_studio.py

class VTubeStudioController:
    def __init__(self):
        self.ws_url = "ws://localhost:8001"  # VTube Studio默认端口
        
    async def connect(self):
        # 连接VTube Studio插件
        self.ws = await websockets.connect(self.ws_url)
        
    def set_mouth_open(self, value: float):
        # 发送嘴型数据
        # value: 0.0(闭嘴) - 1.0(最大张开)
        
    def react_to_message(self, emotion: str):
        # 触发表情
        # emotion: "开心", "惊讶", "思考", etc.
```

### 8.2 OBS集成

```
OBS场景设置:
├── 来源1: VTube Studio捕获（虚拟形象）
├── 来源2: 浏览器捕获（游戏画面，如果需要）
├── 来源3: 音频输入（系统音频，包含TTS输出）
└── 滤镜:  chroma key（如果需要透明背景）
```

### 8.3 音频路由（Windows）

```
方案1: 虚拟音频线
VB-Cable / Voicemeeter
    │
    ├── 输入: TTS输出
    └── 输出: OBS音频源

方案2: 立体声混音（简单）
    系统声音设置 → 录制 → 立体声混音 → 启用
    OBS添加音频源 → 立体声混音
```

---

## 9. 缺少什么

### 9.1 已完成的 ✅

| 模块 | 状态 | 说明 |
|------|------|------|
| 弹幕监听 | ✅ | WebSocket连接B站弹幕服务器 |
| 用户记忆 | ✅ | JSON文件存储用户档案 |
| LLM对话 | ✅ | Claude API接入 |
| TTS语音 | ✅ | Edge TTS + GPT-SoVITS支持 |
| 口型同步 | ✅ | 音量分析 + VTube Studio联动 |
| 游戏控制 | ✅ | Playwright浏览器自动化 |
| 热梗系统 | ✅ | memory/memes/自动学习 |
| 陪伴模式 | ✅ | 无人时自发说话 |
| 整点播报 | ✅ | 每小时自动播报 |

### 9.2 还需要的 🔧

| 优先级 | 模块 | 说明 | 估计工作量 |
|--------|------|------|-----------|
| **P0** | **VTube Studio对接完善** | 目前只有基础口型，需要表情触发 | 2-4小时 |
| **P0** | **主程序main.py集成** | 把companion_mode接入实际运行 | 1-2小时 |
| **P1** | **本地语音克隆** | 录制自己的声音做GPT-SoVITS模型 | 2-3小时 |
| **P1** | **弹幕发送功能** | 目前只能接收，需要发送API | 2-3小时 |
| **P1** | **稳定性监控** | 崩溃自动重启、日志告警 | 4-6小时 |
| **P2** | **Web管理面板** | 查看在线观众、手动触发播报 | 1-2天 |
| **P2** | **多平台支持** | 抖音/快手弹幕适配 | 1-2天 |
| **P2** | **视觉识别增强** | 游戏画面OCR识别、图标点击 | 1-2天 |
| **P3** | **情感分析** | 根据弹幕情绪调整回复语气 | 4-6小时 |
| **P3** | **唱歌功能** | 接入AI歌声合成 | 1-2天 |

### 9.3 配置 checklist

```bash
# 运行前检查清单

# 1. API密钥
[ ] config/api_keys.yaml 已配置Anthropic API Key
[ ] config/api_keys.yaml TTS配置正确

# 2. 外部软件
[ ] OBS Studio 已安装
[ ] VTube Studio 已安装并运行
[ ] VTube Studio插件已启用

# 3. 网络
[ ] B站直播间已开播
[ ] 能访问Anthropic API（可能需要代理）
[ ] 端口8001未被占用（VTube Studio）

# 4. 音频
[ ] 系统音频输出正常
[ ] OBS能捕获到系统声音
[ ] 耳机/扬声器有声音

# 5. 游戏（可选）
[ ] 游戏网页可访问
[ ] config/game_selectors.yaml 已配置
```

### 9.4 下一步建议

**今晚就能跑的MVP:**
1. ✅ 纯聊天模式（已有）
2. 🔄 把companion_mode接入main.py（我帮你做）
3. 🔄 测试整点播报和自发说话

**明天完善:**
4. VTube Studio表情触发
5. 录制你的声音做TTS模型
6. 稳定性测试

需要我先帮你完成哪个？

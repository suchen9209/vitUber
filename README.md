# 🎭 AI虚拟主播 - vitUber

> 24小时自动直播，弹幕互动、游戏控制、赛博陪伴

## ✨ 功能特性

- 🤖 **AI对话** - 基于Claude的智能回复
- 💬 **弹幕互动** - 自动监听B站弹幕并响应
- 🎮 **游戏控制** - 自动控制网页游戏（如整理背包、点击等）
- 🗣️ **语音合成** - Edge TTS或GPT-SoVITS语音输出
- 🎭 **Live2D口型同步** - VTube Studio联动
- 🌙 **赛博陪伴** - 无人时自动说话（热梗/新闻/碎碎念）
- ⏰ **整点播报** - 每小时自动报时
- 🧠 **记忆系统** - 自动学习热梗、记录用户档案

---

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/suchen9209/vitUber.git
cd vitUber
```

### 2. 安装依赖

```bash
cd ai_streamer
pip install -r requirements.txt

# 安装浏览器（用于游戏控制）
playwright install chromium
```

### 3. 配置API密钥

```bash
cp config/api_keys.yaml.example config/api_keys.yaml
# 编辑 config/api_keys.yaml，填入你的 Anthropic API Key
```

### 4. 一键启动

**Linux/Mac:**
```bash
cd ai_streamer
./start.sh
# 或带房间号直接启动: ./start.sh 123456
```

**Windows:**
```cmd
cd ai_streamer
start.bat
:: 或带房间号直接启动: start.bat 123456
```

### 5. 选择模式

启动后会显示菜单：
1. **纯聊天模式** - 只聊天，不控制游戏（推荐首次运行）
2. **测试模式** - 不连接弹幕，手动输入测试
3. **带游戏控制** - 聊天+游戏控制

---

## 📁 项目结构

```
vitUber/
├── ai_streamer/              # AI主播核心
│   ├── core/
│   │   ├── memory_manager.py      # 用户档案管理
│   │   ├── memory_bridge.py       # 热梗/新闻桥接
│   │   ├── companion_mode.py      # 赛博陪伴模式
│   │   ├── llm_client.py          # Claude API
│   │   └── game_controller.py     # 游戏控制
│   ├── interfaces/
│   │   ├── bilibili_danmaku.py    # B站弹幕监听
│   │   ├── tts_engine.py          # 语音合成
│   │   └── vtube_studio.py        # Live2D口型同步
│   ├── config/
│   │   └── api_keys.yaml          # API密钥配置
│   ├── start.sh / start.bat       # 一键启动脚本
│   └── main.py                    # 主程序入口
│
├── memory/                   # 记忆系统
│   ├── memes/
│   │   └── current-hot.md         # 热梗库（自动更新）
│   ├── common-sense/
│   │   └── world-events.md        # 热点新闻（自动更新）
│   ├── learning/
│   │   └── daily-logs/            # 学习日志
│   └── scripts/
│       └── daily-learn.sh         # 自动学习任务
│
├── docs/
│   └── RUNNING_GUIDE.md           # 完整运行指南
│
├── run.sh / run.bat          # 根目录启动脚本
└── README.md                 # 本文件
```

---

## ⚙️ 配置说明

### API密钥 (`config/api_keys.yaml`)

```yaml
anthropic:
  api_key: "sk-ant-xxxxx"  # 你的Claude API Key
  model: "claude-3-5-sonnet-20241022"

tts:
  engine: "edge"  # 或 "gpt_sovits"
  edge_voice: "zh-CN-XiaoxiaoNeural"

vtube_studio:
  enabled: true
  ip: "127.0.0.1"
  port: 8001
```

### 如何获取Claude API Key

1. 访问 https://console.anthropic.com/
2. 注册/登录账号
3. 创建API Key
4. 复制到配置文件

### VTube Studio设置

1. 打开VTube Studio
2. **Settings -> Network -> OSC**
3. Enable OSC = ON
4. Port = 8001
5. **Settings -> Hotkeys** - 设置表情快捷键（F1-F8）

---

## 🎮 使用方式

### 纯聊天模式

```bash
python main.py --room 你的房间号
```

- AI自动回复弹幕
- 无人时自动说话（热梗/新闻/陪伴语）
- 每小时整点播报

### 带游戏控制

```bash
python main.py --room 你的房间号 --game generic_web_game
```

额外功能：
- 观众可发送指令（如"帮我整理背包"）
- AI自动控制网页游戏
- 支持截图、点击、滚动等操作

### 测试模式

```bash
python main.py --room 123456 --test
```

- 不连接真实弹幕
- 手动输入测试消息
- 适合调试和演示

---

## 🧠 记忆系统

### 自动学习内容

每天 **09:13 / 14:13 / 20:13** 自动：
1. 搜索最新网络热梗
2. 抓取热点新闻
3. 更新热梗库和新闻库
4. 记录学习日志

### 手动触发学习

```bash
cd memory
bash scripts/daily-learn.sh
```

### 文件位置

- 热梗库: `memory/memes/current-hot.md`
- 新闻库: `memory/common-sense/world-events.md`
- 学习日志: `memory/learning/daily-logs/`

---

## 📝 日志查看

```bash
# 查看实时日志
tail -f ai_streamer/data/logs/ai_streamer.log

# 查看今日直播日志
cat memory/learning/daily-logs/$(date +%Y-%m-%d)-live.log
```

---

## 🐛 常见问题

### Q: 启动报错 "未找到Anthropic API Key"
**A:** 编辑 `ai_streamer/config/api_keys.yaml`，填入你的API Key

### Q: 弹幕连接失败
**A:** 
1. 检查直播间是否已开播
2. 检查房间号是否正确
3. 检查网络连接

### Q: VTube Studio没有反应
**A:**
1. 确保VTube Studio已打开
2. 检查OSC设置是否正确（端口8001）
3. 检查热键是否已绑定（F1-F8）

### Q: 没有声音
**A:**
1. 检查系统音量
2. 检查OBS音频源设置
3. 检查TTS引擎配置

### Q: 无人时不说话
**A:**
1. 检查陪伴模式是否启动（看日志）
2. 默认需要沉默1分钟后才会触发
3. 检查memory目录是否存在

---

## 🛣️ 路线图

- [x] 基础弹幕互动
- [x] AI对话（Claude）
- [x] TTS语音合成
- [x] VTube Studio口型同步
- [x] 游戏自动化控制
- [x] 用户记忆系统
- [x] 热梗自动学习
- [x] 赛博陪伴模式
- [x] 整点播报
- [ ] 本地语音克隆
- [ ] 弹幕发送功能
- [ ] 多平台支持（抖音/快手）
- [ ] Web管理面板
- [ ] AI唱歌功能

---

## 🤝 贡献

欢迎提交Issue和PR！

---

## 📄 许可证

MIT License

---

## 💖 致谢

- Anthropic Claude - AI对话
- VTube Studio - Live2D控制
- Bilibili - 弹幕API
- Edge TTS / GPT-SoVITS - 语音合成

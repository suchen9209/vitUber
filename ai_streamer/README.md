# AI虚拟主播 - 快速开始

## 📦 环境准备

### 1. 安装Python依赖
```bash
cd ai_streamer
pip install -r requirements.txt
```

### 2. 安装Playwright浏览器
```bash
playwright install chromium
```

### 3. 配置API密钥
```bash
cp config/api_keys.yaml.example config/api_keys.yaml
# 编辑 config/api_keys.yaml，填入你的 Anthropic API Key
```

---

## 🚀 快速启动

### 测试模式（推荐先跑这个）
```bash
python main.py --room 123456 --test
```
输入弹幕内容测试，不用真开直播。

### 正式直播
```bash
# 纯聊天模式
python main.py --room 你的直播间号

# 带游戏控制（需要配置游戏选择器）
python main.py --room 你的直播间号 --game generic_web_game
```

---

## ⚙️ 配置说明

### API密钥 (config/api_keys.yaml)
```yaml
anthropic:
  api_key: "sk-ant-..."  # 你的Claude API密钥
```

### 游戏选择器 (config/game_selectors.yaml)
根据你要玩的网页游戏，配置DOM选择器。

---

## 🎮 观众指令示例

- `帮我整理背包` → AI自动打开背包并点击整理
- `截图看看` → 截图并描述
- `往下翻` → 滚动页面

---

## 📁 项目结构

```
ai_streamer/
├── config/          # 配置文件
├── core/            # 核心逻辑
├── interfaces/      # 外部接口
├── tasks/           # 业务逻辑
├── data/            # 数据存储
├── main.py          # 启动入口
└── requirements.txt # 依赖
```

---

## 🔧 常见问题

1. **浏览器闪退** → 运行 `playwright install chromium`
2. **API错误** → 检查 `config/api_keys.yaml` 中的密钥
3. **弹幕连不上** → 检查房间号是否正确，直播间是否开播

---

## 📝 TODO

- [ ] B站登录态获取（用于获取真实用户ID）
- [ ] 更多游戏预设配置
- [ ] 本地GPT-SoVITS集成
- [ ] 更智能的视觉识别

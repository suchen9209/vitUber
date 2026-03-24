# 🎮 直播间里程碑系统 (Flask版)

完全独立的 Flask 服务端 + WebSocket 实时推送，为直播间提供游戏化进度条展示。

---

## ✨ 效果预览

```
┌─────────────────────────────────────────────────────────┐
│  🌟 Lv.3 话痨新人 🌸                                     │
│  ████████████░░░░░ 68%  ← 彩虹渐变进度条                │
│                                                         │
│  👥 42    🎭 [Miko站这里]    🎁 3                       │
│  💬 156                       ⭐ 350                    │
│                                                         │
│  🔥 已直播 2小时35分  📅 连续 3 天                      │
└─────────────────────────────────────────────────────────┘
```

**特性**:
- ✅ WebSocket 实时推送（延迟 < 100ms）
- ✅ 自动升级动画（全屏庆祝效果）
- ✅ 经验值获得提示（+5XP 弹出动画）
- ✅ 星星背景 + 粒子特效
- ✅ OBS 透明背景支持

---

## 🚀 快速开始（5分钟跑起来）

### 1. 安装依赖

```bash
cd milestone_flask

pip install flask flask-socketio flask-cors
```

### 2. 启动 Demo（推荐先看效果）

```bash
python demo.py
```

这会：
- 启动 Flask 服务器（端口 5000）
- **自动模拟直播数据**（入场、弹幕、礼物）
- 在控制台打印事件日志

打开浏览器看效果：
```
http://localhost:5000
```

---

## 🎬 OBS 配置

### 添加浏览器源

1. OBS → 来源 → + → **浏览器**
2. 属性设置：
   ```
   URL: http://localhost:5000
   宽度: 1920
   高度: 1080
   FPS: 30
   
   ✅ 勾选: 允许透明度（关键！）
   ✅ 勾选: 使用自定义帧率
   ❌ 不勾选: 当源变为活动状态时刷新浏览器
   ```

### 添加 VTube Studio (Miko)

1. 在**里程碑背景上层**添加新来源
2. 选择 **游戏捕获** → 捕获 VTube Studio
3. 调整 Miko 大小，放在画面**中间留白区域**

### 最终层级

```
[顶层] VTube Studio (Miko)
[中层] 弹幕显示（可选）
[底层] 里程碑背景 (http://localhost:5000)
```

---

## 🔌 接入现有系统

如果你已经有 vitUber 主程序在跑，可以这样发送事件：

### Python 代码示例

```python
import requests

def send_milestone_event(event_type, user="", extra=None):
    """
    发送里程碑事件
    
    Args:
        event_type: enter(入场) / chat(弹幕) / gift(礼物)
        user: 用户名
        extra: 额外信息
    """
    try:
        requests.post(
            'http://localhost:5000/api/event',
            json={
                'type': event_type,
                'user': user,
                'extra': extra or {}
            },
            timeout=0.5  # 快速失败，不阻塞
        )
    except:
        pass  # 失败不影响主程序

# 使用示例
send_milestone_event('enter', '小明')      # 有人入场
send_milestone_event('chat', '小红')       # 弹幕互动
send_milestone_event('gift', '大佬', {'gift': '火箭'})  # 收到礼物
```

### 在主程序中集成

在你的 `ai_streamer/main.py` 中：

```python
# 弹幕回调里添加
async def _on_danmaku(self, user_id, username, message):
    # 原有处理...
    
    # 发送里程碑事件（异步，不阻塞）
    import asyncio
    asyncio.create_task(asyncio.to_thread(
        send_milestone_event, 'chat', username
    ))

# 入场回调（需要在弹幕监听里添加 INTERACT_WORD 处理）
async def _on_enter(self, username):
    send_milestone_event('enter', username)
```

---

## 🛠️ API 接口

### REST API

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/status` | GET | 获取当前状态 |
| `/api/event` | POST | 触发事件 |
| `/api/mock` | POST | 模拟批量数据（测试） |
| `/api/reset` | POST | 重置今日数据 |

### WebSocket 事件

前端通过 Socket.IO 连接，实时接收：

```javascript
// 连接
const socket = io('http://localhost:5000');

// 接收事件
socket.on('live_event', (data) => {
    console.log(data);  // {type: 'chat', user: 'xxx', xp_gained: 10, ...}
});

socket.on('level_up', (data) => {
    console.log(data);  // {new_level: 3, name: '话痨新人', ...}
});
```

---

## 📊 数据存储

数据保存在 `data/milestone_flask.json`：

```json
{
  "current_level": 3,
  "total_xp": 350,
  "today": {
    "date": "2026-03-24",
    "enters": 42,
    "chats": 156,
    "gifts": 3
  },
  "streak_days": 3
}
```

**自动处理**:
- 跨天自动重置今日数据
- 连续天数自动累加
- 升级阈值自动判断

---

## 🎯 等级系统

| 等级 | 名称 | 图标 | 所需经验 |
|------|------|------|----------|
| 1 | 初入直播 | 🌱 | 0 |
| 2 | 小透明 | 🌿 | 100 |
| 3 | 话痨新人 | 🌸 | 300 |
| 4 | 互动达人 | 🌺 | 600 |
| 5 | 人气主播 | 🌻 | 1000 |
| 6 | 直播明星 | 🌟 | 2000 |
| 7 | 顶流存在 | 👑 | 5000 |
| 8 | 传奇主播 | 🏆 | 10000 |

**经验获取**:
- 入场: +5 XP
- 弹幕: +10 XP
- 礼物: +50 XP

---

## 🐛 常见问题

### Q: 浏览器打开是空白？
```bash
# 检查服务器是否运行
curl http://localhost:5000/api/status

# 应该返回 JSON 数据
```

### Q: OBS 里看不到页面？
- 确认 URL 是 `http://localhost:5000`（不是 https）
- 检查宽高是 1920x1080
- 尝试刷新浏览器源（右键 → 刷新）

### Q: 页面显示 "连接服务器失败"？
- 检查控制台红色连接状态指示灯
- 刷新页面重连
- 确认 Flask 服务正在运行

### Q: 想清空数据重新开始？
```bash
# 方法1: 调用 API
curl -X POST http://localhost:5000/api/reset

# 方法2: 直接删文件
rm data/milestone_flask.json
```

---

## 📦 文件结构

```
milestone_flask/
├── app.py                 # Flask 主程序
├── data_store.py          # 数据存储类
├── demo.py                # Demo启动器（自动模拟数据）
├── README.md              # 本文件
├── templates/
│   └── background.html    # OBS背景页面
└── data/
    └── milestone_flask.json  # 数据文件（自动生成）
```

---

## 💡 进阶玩法

### 1. 手机当副屏显示数据
```
手机和电脑连同一个WiFi
手机浏览器访问: http://电脑IP:5000
```

### 2. 自定义样式
修改 `templates/background.html` 里的 CSS：
- 改渐变背景色
- 调整统计卡片位置
- 换字体

### 3. 添加更多事件类型
在 `data_store.py` 里：
```python
XP_RULES = {
    "enter": 5,
    "chat": 10,
    "gift": 50,
    "share": 20,      # 新增
    "follow": 30,     # 新增
}
```

---

## 🔗 相关链接

- Flask: https://flask.palletsprojects.com/
- Socket.IO: https://socket.io/
- OBS Browser Source: https://obsproject.com/

---

**有问题？** 直接改代码或者问 Kimi 😄

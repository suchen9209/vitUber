# 🚀 启动指南

## 快速开始（3步）

### 1. 启动脚本
```bash
cd /root/.openclaw/workspace/memory/scripts
bash start-companion.sh
```

### 2. 测试模式（可选）
```bash
python3 cyber_companion.py --test
```

### 3. 手动运行（不经过启动脚本）
```bash
python3 cyber_companion.py
```

---

## 📁 文件说明

| 文件 | 作用 |
|------|------|
| `cyber_companion.py` | 主控脚本，定时触发陪伴语 |
| `start-companion.sh` | 一键启动脚本，带检查 |
| `live-pipeline.md` | 直播主线填充机制文档 |
| `cyber-companion.md` | 赛博陪伴完整实施方案 |

---

## ⚙️ 配置修改

### 修改话术库
编辑 `cyber_companion.py` 中的：
- `COMPANION_PHRASES` - 时间段话术
- `MEME_PHRASES` - 热梗话术

### 修改触发频率
```python
# 当前设置
每小时准点:     固定触发
随机陪伴:       每30分钟检查，40%概率触发

# 修改位置
if time.time() - last_random_chat > 1800:  # 改这里
    if random.random() < 0.4:  # 改这里
```

---

## 📊 日志查看

```bash
# 查看今日直播日志
cat /root/.openclaw/workspace/memory/learning/daily-logs/$(date +%Y-%m-%d)-live.log

# 实时查看
tail -f /root/.openclaw/workspace/memory/learning/daily-logs/$(date +%Y-%m-%d)-live.log
```

---

## 🔗 与其他系统集成

### 接入弹幕系统
修改 `on_user_interaction()` 函数，接入你的弹幕API：
```python
def on_user_interaction(user_msg):
    response = generate_response(user_msg)
    send_danmaku(response)  # 接入弹幕发送
    return response
```

### 接入语音播报
修改 `hourly_announcement()` 和 `random_chat()`，添加：
```python
import subprocess

def speak(text):
    # 方式1: 调用系统TTS
    subprocess.run(["say", text])  # macOS
    # subprocess.run(["espeak", text])  # Linux
    
    # 方式2: 调用预录音频
    play_audio(f"assets/voice/{hash(text)}.mp3")
```

### 接入OBS
1. OBS添加"浏览器源"
2. 指向一个本地HTML页面
3. Python脚本通过WebSocket或文件写入控制页面内容

---

## 🐛 常见问题

### Q: 脚本无法启动
```bash
# 检查Python版本
python3 --version  # 需要 3.7+

# 检查文件权限
chmod +x start-companion.sh
chmod +x cyber_companion.py
```

### Q: 记忆系统读取失败
```bash
# 检查路径
ls /root/.openclaw/workspace/memory/memes/current-hot.md

# 检查文件编码
file /root/.openclaw/workspace/memory/memes/current-hot.md
```

### Q: 定时触发不准
- 脚本使用 `time.sleep(60)`，有一定误差
- 如需精确到秒，改用 `schedule` 库或系统crontab

---

## 📝 更新计划

- [ ] 接入真实弹幕API
- [ ] 接入语音合成(TTS)
- [ ] 接入OBS控制
- [ ] Web可视化面板
- [ ] 观众数据统计

---

**当前版本**: v0.1.0  
**最后更新**: 2026-03-17

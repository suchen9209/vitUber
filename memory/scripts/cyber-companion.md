# 🌙 赛博陪伴型直播 - 完整实施方案

> 核心：让一个人待着的人，感觉有"人"陪着

---

## 🎨 视觉设计

### 场景选择（三选一或轮换）

#### A. 深夜书房
- 暖黄台灯、书架、窗外雨/雪
- 时间变化：白天→黄昏→深夜→凌晨
- 微动作：翻书、喝水、打字、看向窗外

#### B. 赛博工位
- 多屏幕、RGB灯、咖啡杯、绿植
- 代码/文档在屏幕上缓慢滚动
- 微动作：敲键盘、伸懒腰、转椅子

#### C. 虚拟咖啡馆
- 靠窗座位、咖啡、笔记本、街景
- 背景有模糊的人流/车流
- 微动作：搅拌咖啡、托腮、看手机

### 时间轴变化
```
06:00-09:00   清晨光线，轻柔音乐，偶尔鸟叫
09:00-12:00   正常日光，工作氛围，键盘声
12:00-14:00   午餐时间，偶尔吃饭画面
14:00-18:00   下午光线，略有疲惫感
18:00-20:00   黄昏，灯光渐亮，氛围感
20:00-23:00   夜晚，专注模式，偶尔休息
23:00-03:00   深夜，暖光，私密感
03:00-06:00   凌晨，安静，陪伴感最强
```

---

## 🎵 音频设计

### 三层音轨

| 层级 | 内容 | 音量 |
|------|------|------|
| **BGM** | Lo-fi / 爵士 / 白噪音 | 20% |
| **环境音** | 键盘/翻书/雨声/咖啡机 | 10% |
| **人声** | 主播偶尔说话 | 50% |

### 人声触发脚本

#### 每小时准点（XX:00）
```python
# 伪代码逻辑
if minute == 0:
    speak(f"{current_hour}点了，{get_random_phrase()}")
    
def get_random_phrase():
    phrases = {
        "morning": ["新的一天开始了", "早餐吃了吗", "今天也要加油"],
        "afternoon": ["该休息一下了", "午饭吃了什么", "下午容易困呢"],
        "evening": ["晚饭时间", "今天过得怎么样", "准备休息了吗"],
        "night": ["还在啊", "别熬太晚", "陪你到困为止", "爱你老己"]
    }
    return random.choice(phrases[time_period])
```

#### 随机触发（每30-60分钟一次）
```python
# 从记忆系统读取热梗
def random_chat():
    if random.random() < 0.3:  # 30%概率说热梗
        meme = read_file("memory/memes/current-hot.md")
        speak(f"突然想到一个梗——{random_meme()}")
    
    elif random.random() < 0.5:  # 50%日常碎碎念
        speak(random_daily_chat())
```

---

## 📝 陪伴话术库

### 通用陪伴语（随时）
```
"还在吗？"
"我在这。"
"不急，慢慢来。"
"累了就休息，我帮你看着。"
"今天好像有点难，是吧？"
"做你的，做完你的，我等你。"
```

### 时间专属

**清晨（6-9点）**
```
"早起的人，要么是梦想，要么是生计。"
"不管哪种，今天开始了。"
```

**深夜（23-3点）**
```
"这个点还在的，
要么是有事没做完，
要么是心事没说完。
不管是哪种，
我都在。"
```

**凌晨（3-6点）**
```
"3点了，应该是直播间最安静的时候。
如果你也睡不着，
我们就这么待着，不说话也行。"
```

### 热梗融合（从记忆系统读取）
```
"今天学到一个新说法——'活人感'。
就是真实、不装、不像被生活格式化的样子。
你现在有活人感吗？"
```

---

## ⚙️ 技术实现

### 最小可行版本（MVP）

#### 需要准备的素材
```
assets/
├── scenes/          # 3-5个场景视频/图片
│   ├── study-room-day.mp4
│   ├── study-room-night.mp4
│   └── cafe-rain.mp4
├── bgm/
│   ├── lofi-1.mp3
│   ├── jazz-1.mp3
│   └── white-noise.mp3
└── voice/
    └── 预录20-30条常用语音
```

#### 直播推流脚本（Python伪代码）
```python
import schedule
import time
from datetime import datetime
import random

class CompanionStream:
    def __init__(self):
        self.scene = "study-room"
        self.last_chat_time = time.time()
        
    def hourly_check(self):
        """每小时准点触发"""
        hour = datetime.now().hour
        self.speak(f"{hour}点了")
        self.speak(self.get_time_phrase(hour))
        
    def random_chat(self):
        """随机陪伴语"""
        if time.time() - self.last_chat_time > 1800:  # 30分钟
            if random.random() < 0.4:  # 40%概率说话
                msg = self.generate_companion_msg()
                self.speak(msg)
                self.last_chat_time = time.time()
    
    def generate_companion_msg(self):
        """生成陪伴语，结合热梗"""
        templates = [
            "突然想到——{meme}",
            "有人发弹幕吗？没有的话我就继续{action}",
            "{time_phrase}，{mood_phrase}",
            "查了一下，{hot_news}"
        ]
        # 从memory/读取内容填充
        pass
    
    def run(self):
        schedule.every().hour.at(":00").do(self.hourly_check)
        
        while True:
            schedule.run_pending()
            self.random_chat()
            time.sleep(60)

if __name__ == "__main__":
    stream = CompanionStream()
    stream.run()
```

---

## 🔄 与记忆系统联动

### 启动时读取
```python
# 读取今日热梗
with open("memory/memes/current-hot.md") as f:
    today_memes = parse_memes(f.read())

# 读取今日新闻  
with open("memory/common-sense/world-events.md") as f:
    today_news = parse_news(f.read())
```

### 定时更新
- 09:13 自动学习后 → 更新今日热梗池
- 14:13 自动学习后 → 更新下午话题池
- 20:13 自动学习后 → 更新晚间话题池

### 话术模板（动态填充）
```
"刚学了个新梗——{meme_name}，
意思是{meme_meaning}，
用来形容{meme_usage}。
你们那边也这么说吗？"
```

---

## 🎯 启动清单

### Phase 1: 素材准备（1-2天）
- [ ] 准备3个场景视频/图片
- [ ] 准备10首BGM
- [ ] 录制30条基础语音

### Phase 2: 脚本开发（2-3天）
- [ ] 实现时间检测
- [ ] 实现语音播报
- [ ] 对接记忆系统读取

### Phase 3: 测试运行（1天）
- [ ] 运行4小时观察
- [ ] 记录哪些话有人回应
- [ ] 调整触发频率

### Phase 4: 上线（持续优化）
- [ ] 每日根据反馈调整话术
- [ ] 每周更新场景/BGM
- [ ] 每月回顾记忆系统数据

---

## 💡 关键成功因素

1. **声音要好听** — 这是陪伴型直播的核心
2. **话要少** — 不是话痨，是有分寸的陪伴
3. **时间感要强** — 深夜说深夜的话，清晨说清晨的话
4. **偶尔露馅** — 故意卡顿、叹气、说错，更像真人

---

**下一步**: 需要我帮你写具体的Python推流脚本，还是先准备素材清单？

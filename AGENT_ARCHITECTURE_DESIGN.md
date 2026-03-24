# vitUber 多Agent架构改造设计文档

> 版本: v1.1  
> 日期: 2026-03-24  
> 更新: 新增观众入场欢迎Agent设计  
> 目标: 将单体架构重构为事件驱动的多Agent协作系统

---

## 一、现状分析

### 1.1 当前架构问题

```
┌─────────────────────────────────────────┐
│              main.py                    │
│  ┌─────────┐ ┌─────────┐ ┌──────────┐  │
│  │ 弹幕监听 │ │LiveSession│ │  记忆管理  │  │
│  │ (直接调用)│ │ (处理一切) │ │ (JSON读写) │  │
│  └────┬────┘ └────┬────┘ └────┬─────┘  │
│       └───────────┴───────────┘         │
│              高度耦合                    │
└─────────────────────────────────────────┘
```

**核心痛点**:
| 问题 | 表现 | 影响 |
|------|------|------|
| 上帝类 | LiveSession 处理弹幕、LLM、状态、TTS | 改动困难，测试复杂 |
| 紧耦合 | 模块间直接调用 | 新增功能牵一发而动全身 |
| 无自我进化 | 学习靠外部脚本 | 无法根据效果自动优化 |
| 记忆膨胀 | JSON文件无限增长 | Token爆炸，响应变慢 |

---

## 二、目标架构设计

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                         输入层                                   │
│    B站弹幕 ──┬── 礼物事件 ──┬── 系统定时 ──┬── 外部数据源        │
└──────────────┼─────────────┼──────────────┼─────────────────────┘
               │             │              │
               └─────────────┴──────┬───────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────┐
│                      事件总线 (Event Bus)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────┐ │
│  │ DanmakuEvent │  │  GiftEvent   │  │  EnterEvent  │  │TickEvent│ │
│  │  弹幕解析     │  │   礼物处理    │  │  观众入场    │  │ 定时触发 │ │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └───┬────┘ │
└─────────┼─────────────────┼─────────────────┼───────────────────┘
          │                 │                 │
          └─────────────────┴────────┬────────┘
                                   ↓
┌─────────────────────────────────────────────────────────────────┐
│                    中央调度器 (Conductor)                        │
│           状态机管理 │ 任务路由 │ 冲突裁决 │ 生命周期管理          │
└─────────────────────────────────────────────────────────────────┘
       ↓              ↓              ↓              ↓
  ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐
  │ 感知Agent │   │ 大脑Agent │   │ 记忆Agent │   │ 表达Agent │
  │ Sensor  │   │  Brain  │   │ Memory  │   │ Express │
  └────┬────┘   └────┬────┘   └────┬────┘   └────┬────┘
       │             │             │             │
       └─────────────┴─────────────┴─────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│              共享上下文 (Shared Context) - 只读                   │
│     时间状态 │ 用户档案 │ 会话历史 │ 环境感知 │ 学习数据          │
└─────────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│                    自我进化循环 (Evolution Loop)                  │
│     效果收集 → 反思分析 → 策略优化 → 知识更新 → 效果验证           │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Agent 职责边界

| Agent | 核心职责 | 输入 | 输出 | 禁止行为 |
|-------|----------|------|------|----------|
| **感知Agent** | 事件解析与分类 | 原始弹幕/礼物/入场/API数据 | 结构化Event + 元数据 | 不做决策，不调用LLM |
| **大脑Agent** | 决策生成 | Event + 记忆上下文 | Decision对象 | 不直接操作硬件(TTS/游戏) |
| **记忆Agent** | 记忆存取与压缩 | 查询请求/存储数据 | 上下文/确认信号 | 不解释记忆内容 |
| **表达Agent** | 执行输出 | Decision对象 | TTS语音/Live2D动作/游戏控制 | 不修改决策 |
| **进化Agent** | 后台学习与优化 | 历史日志/效果反馈 | 策略更新/新知识 | 不影响实时交互 |
| **欢迎Agent** | 入场欢迎策略 | 入场Event + 直播间状态 | 欢迎Decision | 不处理弹幕/礼物 |

### 2.3 关键设计原则

1. **事件驱动**: Agent间不直接调用，通过Event Bus通信
2. **上下文只读**: 每次交互新建Context，避免状态混乱
3. **单一职责**: 每个Agent只处理一种抽象层次的任务
4. **可观测性**: 所有决策和事件都有日志，支持回放调试

---

## 三、运转模式详解

### 3.1 正常交互流程

#### 场景：用户发送弹幕"你好"

```
Step 1: 输入层捕获
─────────────────────────────────────────
B站WebSocket → bilibili_danmaku.py
原始数据: {"cmd":"DANMU_MSG","info":[[...],"你好",[123,"小明",...]]}


Step 2: 感知Agent处理
─────────────────────────────────────────
输入: 原始弹幕数据
处理:
  - 提取: user_id=123, username="小明", content="你好"
  - 意图识别: greeting (轻量级规则/小模型)
  - 情感分析: friendly (关键词匹配)
  - 重要性评分: 3/10 (普通问候)
  
输出Event:
{
  "event_type": "DANMU_EVENT",
  "user_id": "123",
  "username": "小明",
  "content": "你好",
  "intent": "greeting",
  "emotion": "friendly",
  "importance": 3,
  "timestamp": "2026-03-24T15:40:00"
}


Step 3: Conductor调度
─────────────────────────────────────────
接收Event → 查询当前状态
决策:
  - 当前状态: interactive (有人模式)
  - 是否需要响应: 是 (importance >= 2)
  - 路由目标: BrainAgent
  - 需要记忆: 是 (用户识别)


Step 4: 记忆Agent召回
─────────────────────────────────────────
查询: user_id="123"
检索策略:
  L1工作记忆: 本场直播最近3条对话 (内存)
  L2短期记忆: 用户档案、最近7天互动 (SQLite)
  L3长期记忆: 关键事件摘要 (向量库，仅Top-2)

输出Context:
{
  "user_profile": {
    "username": "小明",
    "user_type": "regular",
    "join_count": 5,
    "last_seen": "2天前",
    "facts": ["喜欢原神", "大学生", "上次聊抽卡"],
    "recent_chats": ["上次说到抽卡歪了"]
  },
  "current_mood": "neutral",
  "estimated_tokens": 280
}


Step 5: 大脑Agent决策
─────────────────────────────────────────
输入: Event + Context + 人设Prompt

LLM思考过程:
  "小明是老观众，2天没来
   上次聊抽卡歪了，可以关心一下结果
   人设是活泼女大学生，语气轻松"

输出Decision:
{
  "decision_type": "REPLY",
  "content": "小明！两天不见，上次说的抽卡出了吗？",
  "emotion": "happy",
  "intensity": 0.7,
  "gestures": ["wave", "smile"],
  "voice_style": "default",
  "expected_outcome": "用户回应抽卡结果",
  "store_memory": true
}


Step 6: 表达Agent执行
─────────────────────────────────────────
并行执行:
  ├─ TTS: 调用edge-tts生成语音
  ├─ Live2D: 触发wave动画 → smile表情
  └─ 日志: 记录决策执行时间


Step 7: 记忆Agent存储 (异步)
─────────────────────────────────────────
存储内容:
  - 交互记录: 用户:"你好" → 主播:"小明！两天不见..."
  - 提取事实: "询问抽卡结果" (用户画像更新)
  - 效果追踪: 记录expected_outcome，等待验证
```

### 3.1b 观众入场欢迎流程

#### 场景：观众进入直播间

```
Step 1: B站API捕获入场
─────────────────────────────────────────
WebSocket消息: {"cmd":"INTERACT_WORD","data":{"uname":"新观众", "uid":456}}


Step 2: 感知Agent解析
─────────────────────────────────────────
输入: 原始入场数据
处理:
  - 提取: uid=456, username="新观众"
  - 查询用户等级信息 (从API或缓存)
  - 判断用户类型:
    * user_level: 23 (较高)
    * is_vip: false
    * fans_medal: "小K的舰长" (有粉丝牌)
    
输出Event (根据等级分发不同事件):
情况A - 高价值用户 → VIP_ENTER_EVENT
{
  "event_type": "VIP_ENTER",
  "user_id": "456",
  "username": "新观众",
  "user_level": 23,
  "has_medal": true,
  "medal_name": "小K的舰长",
  "last_visit": "3天前",  // 从记忆查询
  "priority": 2  // 高优先级
}

情况B - 普通用户 → ENTER_EVENT  
{
  "event_type": "ENTER",
  "user_id": "789",
  "username": "路人甲",
  "user_level": 5,
  "has_medal": false,
  "priority": 8  // 低优先级
}


Step 3: Conductor路由决策
─────────────────────────────────────────
根据直播间当前状态决定处理方式:

场景A - 直播间人少 (< 20人)
  处理: 欢迎所有观众
  → 路由到 WelcomeAgent

场景B - 直播间人多 (> 50人)
  处理: 只欢迎VIP/高等级
  判断:
    - VIP_ENTER → 路由到 WelcomeAgent
    - ENTER (普通) → 忽略，只记录记忆

场景C - 深夜模式 (2-6点)
  处理: 降低欢迎频率，避免打扰
  → 只欢迎VIP/老粉


Step 4: WelcomeAgent生成欢迎策略
─────────────────────────────────────────
专门负责入场欢迎的Agent，根据用户画像定制欢迎语:

输入: VIP_ENTER_EVENT + 用户档案

策略判断:
  if 用户有粉丝牌且等级高:
    → 热情欢迎 + 回忆杀
    示例: "舰长新观众回来啦！3天不见，上次说的论文写完了吗？"
    
  elif 用户是老粉(互动>10次):
    → 亲切欢迎 + 提及上次互动
    示例: "新观众~ 又来啦！今天也是来催更的吗😆"
    
  elif 用户等级高(>20级)但新人:
    → 热情欢迎 + 自我介绍
    示例: "欢迎新观众！23级大佬！我是小K，主玩原神和独立游戏~"
    
  else:
    → 标准欢迎
    示例: "欢迎新观众！"

输出Decision:
{
  "decision_type": "WELCOME",
  "content": "舰长新观众回来啦！3天不见~",
  "emotion": "happy",
  "gestures": ["wave", "smile"],
  "priority": 2,  // 插队优先播报
  "interrupt_current": false  // 不中断当前说话
}


Step 5: 表达Agent执行（带优先级）
─────────────────────────────────────────
欢迎消息支持优先级插队:

队列处理逻辑:
  - 当前正在说话: "话说今天天气..."
  - 新消息优先级: 2 (VIP欢迎)
  - 当前消息优先级: 5 (普通闲聊)
  
处理:
  if new_priority < current_priority:
    // VIP欢迎优先
     options:
    A. 等待当前说完再欢迎 (默认)
    B. 如果设置了interrupt_current: 礼貌打断
       "等一下哈，欢迎一下舰长~ 新观众回来啦！"
       然后继续之前的话题

执行:
  - TTS: "舰长新观众回来啦！3天不见~"
  - Live2D: wave + smile


Step 6: 记忆Agent记录
─────────────────────────────────────────
存储入场记录:
  {
    "user_id": "456",
    "event": "enter",
    "timestamp": "...",
    "user_level": 23,
    "welcome_sent": true,
    "welcome_type": "vip_with_recall"
  }

更新用户统计:
  - 今日入场人数 +1
  - 该用户入场次数 +1
  - 识别为"活跃用户"
```

#### 入场欢迎策略配置

```yaml
# config/welcome.yaml

welcome_policy:
  # 基础开关
  enabled: true
  
  # 根据直播间人数动态调整
  by_viewer_count:
    low:       # 人少 (< 20)
      threshold: 20
      welcome_all: true        # 欢迎所有人
      max_per_minute: 10       # 每分钟最多欢迎10人
      
    medium:    # 中等 (20-50)
      threshold: 50
      welcome_all: false
      min_user_level: 10       # 10级以上才欢迎
      welcome_vip: true        # VIP必欢迎
      welcome_with_medal: true # 有粉丝牌必欢迎
      max_per_minute: 5
      
    high:      # 人多 (> 50)
      threshold: 999
      welcome_all: false
      min_user_level: 20       # 只有高等级
      welcome_vip: true
      welcome_with_medal: true
      welcome_old_fans: true   # 老粉必欢迎
      max_per_minute: 3
  
  # 时间段策略
  by_time:
    night:     # 深夜 2-6点
      hours: [2, 3, 4, 5, 6]
      enabled: true
      whisper_mode: true       # 小声模式
      only_vip: true           # 只欢迎VIP
      min_interval: 300        # 最少间隔5分钟
      
  # 用户类型优先级 (数字越小优先级越高)
  priority:
    vip_enter: 1               # VIP进入
    high_level_enter: 2        # 高等级 (>20)
    old_fan_enter: 3           # 老粉 (>10次互动)
    medal_holder: 4            # 有粉丝牌
    normal_enter: 8            # 普通用户
    
  # 欢迎语模板
  templates:
    vip_return:              # VIP回归
      - "{username}回来啦！想死你了~"
      - "舰长{username}！好久不见！"
      - "欢迎{username}！今天也是来陪我的吗🥰"
      
    old_fan_return:          # 老粉回归
      - "{username}~ 又来啦！"
      - "欢迎{username}！上次聊的{topic}后来怎么样了？"
      
    high_level_new:          # 高等级新观众
      - "欢迎{username}！{level}级大佬！"
      - "新来的{level}级大佬{username}！请多关照~"
      
    normal:                  # 标准欢迎
      - "欢迎{username}！"
      - "欢迎{username}~ 玩得开心！"
```

#### 防刷屏机制

```python
class WelcomeThrottler:
    """欢迎节流器 - 防止人多时欢迎刷屏"""
    
    def __init__(self):
        self.recent_welcomes = []  # 最近欢迎记录
        self.viewer_count = 0
    
    def should_welcome(self, user_event: EnterEvent) -> Tuple[bool, str]:
        """
        判断是否该欢迎这个用户
        返回: (是否欢迎, 原因)
        """
        # 1. 检查全局开关
        if not config.welcome_policy.enabled:
            return False, "欢迎功能已关闭"
        
        # 2. 检查用户优先级
        priority = self._get_priority(user_event)
        
        # VIP直接通过
        if priority <= 2:
            return True, "VIP用户"
        
        # 3. 检查频率限制
        recent_count = len([
            w for w in self.recent_welcomes 
            if time.time() - w['time'] < 60
        ])
        max_per_minute = self._get_rate_limit()
        
        if recent_count >= max_per_minute:
            return False, f"超过每分钟欢迎上限({max_per_minute})"
        
        # 4. 检查直播间人数策略
        if self.viewer_count > 50 and priority > 4:
            return False, "直播间人数过多，只欢迎高优先级用户"
        
        # 5. 检查重复欢迎（防止同一人反复进出）
        if self._is_recently_welcomed(user_event.user_id):
            return False, "10分钟内已欢迎过"
        
        return True, "通过所有检查"
    
    def _get_priority(self, event: EnterEvent) -> int:
        """计算用户优先级"""
        if event.is_vip:
            return 1
        if event.user_level >= 20:
            return 2
        if event.interaction_count > 10:
            return 3
        if event.has_medal:
            return 4
        return 8
```

### 3.2 无人模式运转

```
触发条件: 5分钟无弹幕

Step 1: 进入Idle模式
─────────────────────────────────────────
Conductor状态切换: interactive → idle
触发TickEvent: {"type": "IDLE_TICK", "silence_duration": 300}


Step 2: 进化Agent介入
─────────────────────────────────────────
后台启动:
  - 学习Agent: 浏览微博/小红书获取热梗
  - 反思Agent: 分析今天哪些话题效果好
  - 压缩Agent: 整理过期记忆，释放空间


Step 3: 陪伴内容生成
─────────────────────────────────────────
大脑Agent根据silence_duration生成内容:
  5-10分钟: 简单陪伴语 ("还有人吗~")
  10-20分钟: 分享热梗 ("刚看到个搞笑视频...")
  20分钟+: 整活 ("那我给你们讲讲今天学到的东西")


Step 4: 表达Agent播报
─────────────────────────────────────────
正常执行TTS + 表情，但降低频率:
  - 深夜(2-6点): 延长触发间隔到10分钟
  - 白天: 正常3-5分钟随机触发
```

### 3.3 自我进化循环

```
每日进化流程 (无人时运行):

┌─────────────────────────────────────────────────────────────┐
│ 阶段1: 数据收集 (10分钟)                                      │
├─────────────────────────────────────────────────────────────┤
│ 读取今日日志:                                                 │
│   - 互动次数: 150次                                           │
│   - 平均响应时间: 1.2秒                                       │
│   - 话题统计:                                                 │
│     * 游戏话题: 60次，平均点赞3.2个                           │
│     * 热梗话题: 40次，平均点赞5.1个 ← 效果最好                 │
│     * 日常闲聊: 50次，平均点赞1.8个                           │
│   - 被忽略回复: 20次 (用户没回应)                              │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ 阶段2: 反思分析 (20分钟)                                      │
├─────────────────────────────────────────────────────────────┤
│ 调用LLM分析:                                                 │
│   "哪些回复效果好？为什么？                                   │
│    哪些被忽略了？如何改进？"                                  │
│                                                              │
│ 输出洞察:                                                     │
│   - 提到"抽象梗"时观众互动率高40%                              │
│   - 深夜(2-6点)回复被忽略率80%，应减少输出                     │
│   - 老用户(X互动>10次)更喜欢回忆杀类型的回复                    │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ 阶段3: 策略优化 (10分钟)                                      │
├─────────────────────────────────────────────────────────────┤
│ 生成新策略配置:                                               │
│   {                                                          │
│     "topic_weights": {                                       │
│       "meme": 0.8,      ← 从0.5提升                           │
│       "game": 0.5,      ← 从0.7降低                           │
│       "greeting": 0.3                                            │
│     },                                                       │
│     "time_rules": {                                          │
│       "night_silence_threshold": 600  ← 深夜延长到10分钟       │
│     },                                                       │
│     "user_strategies": {                                     │
│       "old_user": "more_memory_recall"  ← 老用户多回忆         │
│     }                                                        │
│   }                                                          │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ 阶段4: 知识更新 (持续)                                        │
├─────────────────────────────────────────────────────────────┤
│ 根据优化后的策略:                                             │
│   - 增加热梗来源的爬取频率                                     │
│   - 减少游戏新闻的权重                                         │
│   - 更新回复模板库                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 四、核心模块设计

### 4.1 事件总线 (Event Bus)

```python
# core/event_bus.py

from typing import Dict, List, Callable, Any
from dataclasses import dataclass
from enum import Enum
import asyncio

class EventType(Enum):
    DANMAKU = "danmaku"           # 弹幕事件
    GIFT = "gift"                 # 礼物事件
    ENTER = "enter"               # 用户进入（新增）
    VIP_ENTER = "vip_enter"       # VIP/高等级用户进入（新增）
    TICK = "tick"                 # 定时触发
    IDLE = "idle"                 # 进入无人模式
    DECISION = "decision"         # 决策事件
    MEMORY_UPDATE = "memory_update"  # 记忆更新

@dataclass
class Event:
    event_type: EventType
    payload: Dict[str, Any]
    timestamp: float
    source: str  # 产生事件的Agent
    priority: int = 5  # 1-10，数字越小优先级越高

class EventBus:
    """异步事件总线"""
    
    def __init__(self):
        self.subscribers: Dict[EventType, List[Callable]] = {
            et: [] for et in EventType
        }
        self.event_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self.running = False
    
    def subscribe(self, event_type: EventType, handler: Callable):
        """订阅事件"""
        self.subscribers[event_type].append(handler)
    
    async def publish(self, event: Event):
        """发布事件"""
        await self.event_queue.put((event.priority, event))
    
    async def _process_loop(self):
        """事件处理循环"""
        while self.running:
            priority, event = await self.event_queue.get()
            handlers = self.subscribers.get(event.event_type, [])
            
            # 并发执行所有订阅者
            await asyncio.gather(*[
                self._safe_call(handler, event)
                for handler in handlers
            ])
    
    async def _safe_call(self, handler: Callable, event: Event):
        """安全调用处理器"""
        try:
            await handler(event)
        except Exception as e:
            logger.error(f"Handler {handler.__name__} failed: {e}")
```

### 4.2 中央调度器 (Conductor)

```python
# core/conductor.py

from enum import Enum

class LiveMode(Enum):
    INTERACTIVE = "interactive"   # 有人互动模式
    IDLE = "idle"                 # 无人模式
    LEARNING = "learning"         # 主动学习模式
    SLEEP = "sleep"               # 深夜低功耗模式

class Conductor:
    """中央调度器 - 直播中控大脑"""
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.mode = LiveMode.INTERACTIVE
        self.agents: Dict[str, BaseAgent] = {}
        self.context: LiveContext = LiveContext()
        
        # 状态机配置
        self.transitions = {
            LiveMode.INTERACTIVE: [LiveMode.IDLE],
            LiveMode.IDLE: [LiveMode.INTERACTIVE, LiveMode.LEARNING, LiveMode.SLEEP],
            LiveMode.LEARNING: [LiveMode.IDLE],
            LiveMode.SLEEP: [LiveMode.IDLE, LiveMode.INTERACTIVE]
        }
        
        self._register_handlers()
    
    def register_agent(self, name: str, agent: BaseAgent):
        """注册Agent"""
        self.agents[name] = agent
        agent.set_conductor(self)
    
    def _register_handlers(self):
        """注册事件处理器"""
        self.event_bus.subscribe(EventType.DANMAKU, self._handle_danmaku)
        self.event_bus.subscribe(EventType.TICK, self._handle_tick)
        self.event_bus.subscribe(EventType.GIFT, self._handle_gift)
        self.event_bus.subscribe(EventType.ENTER, self._handle_enter)
        self.event_bus.subscribe(EventType.VIP_ENTER, self._handle_vip_enter)
    
    async def _handle_danmaku(self, event: Event):
        """处理弹幕事件"""
        # 有人来了，切回互动模式
        if self.mode != LiveMode.INTERACTIVE:
            await self._switch_mode(LiveMode.INTERACTIVE)
        
        # 更新上下文
        self.context.last_interaction = time.time()
        
        # 路由到感知Agent
        sensor = self.agents.get("sensor")
        if sensor:
            parsed_event = await sensor.process(event.payload)
            
            # 根据重要性路由
            if parsed_event.importance >= 5:
                # 重要事件，直接给大脑Agent
                await self.agents["brain"].handle(parsed_event, self.context)
            else:
                # 普通事件，先查记忆
                memory = await self.agents["memory"].recall(
                    user_id=parsed_event.user_id
                )
                await self.agents["brain"].handle(
                    parsed_event, 
                    self.context.with_memory(memory)
                )
    
    async def _handle_tick(self, event: Event):
        """处理定时事件 - 模式切换判断"""
        silence_time = time.time() - self.context.last_interaction
        
        if self.mode == LiveMode.INTERACTIVE and silence_time > 300:
            # 5分钟无人，进入Idle
            await self._switch_mode(LiveMode.IDLE)
        
        elif self.mode == LiveMode.IDLE:
            hour = datetime.now().hour
            if 2 <= hour <= 6:
                # 深夜进入Sleep模式
                await self._switch_mode(LiveMode.SLEEP)
            elif silence_time > 600:
                # 10分钟无人，开始学习
                await self._switch_mode(LiveMode.LEARNING)
    
    async def _switch_mode(self, new_mode: LiveMode):
        """切换模式"""
        if new_mode not in self.transitions.get(self.mode, []):
            logger.warning(f"Invalid mode transition: {self.mode} -> {new_mode}")
            return
        
        logger.info(f"Mode transition: {self.mode.value} -> {new_mode.value}")
        self.mode = new_mode
        
        # 通知所有Agent模式变更
        for agent in self.agents.values():
            await agent.on_mode_change(new_mode)
```

### 4.3 Agent基类

```python
# agents/base.py

from abc import ABC, abstractmethod
from typing import Optional

class BaseAgent(ABC):
    """Agent基类"""
    
    def __init__(self, name: str):
        self.name = name
        self.conductor: Optional[Conductor] = None
        self.state = {}
    
    def set_conductor(self, conductor: Conductor):
        """设置调度器引用"""
        self.conductor = conductor
    
    @abstractmethod
    async def initialize(self):
        """初始化Agent"""
        pass
    
    @abstractmethod
    async def shutdown(self):
        """关闭Agent"""
        pass
    
    async def on_mode_change(self, mode: LiveMode):
        """模式变更回调（可选实现）"""
        pass
    
    def emit(self, event: Event):
        """发布事件"""
        if self.conductor and self.conductor.event_bus:
            asyncio.create_task(self.conductor.event_bus.publish(event))
```

### 4.4 具体Agent实现示例

#### 感知Agent

```python
# agents/sensor_agent.py

class SensorAgent(BaseAgent):
    """
    感知Agent - 负责数据解析和意图识别
    特点: 轻量级，不调用大模型
    """
    
    def __init__(self):
        super().__init__("sensor")
        # 轻量级意图分类器（可以用规则或小模型）
        self.intent_rules = {
            r"^(你好|在吗|hi|hello)": "greeting",
            r"^(!|！).+": "command",
            r"^(为什么|怎么|如何)": "question",
            r"^(哈哈|笑死|草)": "reaction",
        }
        
        self.emotion_keywords = {
            "happy": ["哈哈", "开心", "棒", "好耶"],
            "sad": ["难过", "哭了", "emo"],
            "angry": ["气", "怒", "md"],
            "surprise": ["哇", "啊这", "震惊"],
        }
    
    async def process(self, raw_data: dict) -> ParsedEvent:
        """解析原始数据"""
        content = raw_data.get("content", "")
        
        # 意图识别（规则匹配）
        intent = self._classify_intent(content)
        
        # 情感分析（关键词匹配）
        emotion = self._classify_emotion(content)
        
        # 重要性评分
        importance = self._score_importance(content, intent)
        
        return ParsedEvent(
            user_id=raw_data["user_id"],
            username=raw_data["username"],
            content=content,
            intent=intent,
            emotion=emotion,
            importance=importance
        )
    
    def _classify_intent(self, content: str) -> str:
        for pattern, intent in self.intent_rules.items():
            if re.search(pattern, content, re.I):
                return intent
        return "chat"
    
    def _classify_emotion(self, content: str) -> str:
        for emotion, keywords in self.emotion_keywords.items():
            if any(kw in content for kw in keywords):
                return emotion
        return "neutral"
    
    def _score_importance(self, content: str, intent: str) -> int:
        """简单评分规则"""
        base_scores = {
            "greeting": 3,
            "command": 8,
            "question": 6,
            "chat": 4,
        }
        return base_scores.get(intent, 5)
```

#### 大脑Agent

```python
# agents/brain_agent.py

class BrainAgent(BaseAgent):
    """
    大脑Agent - 决策核心
    负责: 生成回复、选择话题、决定动作
    """
    
    def __init__(self, llm_router: LLMRouter):
        super().__init__("brain")
        self.llm = llm_router
        self.decision_history: List[Decision] = []
    
    async def handle(self, event: ParsedEvent, context: LiveContext):
        """处理事件并生成决策"""
        
        # 构建Prompt
        prompt = self._build_prompt(event, context)
        
        # 根据重要性选择模型
        model = "kimi" if event.importance < 7 else "claude"
        
        # 调用LLM
        response = await self.llm.chat(
            prompt=prompt,
            model=model,
            max_tokens=150
        )
        
        # 解析决策
        decision = self._parse_decision(response)
        
        # 记录历史（用于后续反思）
        self.decision_history.append(decision)
        
        # 发布决策事件
        self.emit(Event(
            event_type=EventType.DECISION,
            payload={
                "decision": decision,
                "trigger_event": event
            },
            source=self.name
        ))
    
    def _build_prompt(self, event: ParsedEvent, context: LiveContext) -> str:
        """构建Prompt（严格控制token）"""
        parts = [
            "人设: 活泼女大学生游戏主播，说话简短口语化，带emoji",
            f"当前时间: {context.current_time}",
            f"直播间人数: {context.viewer_count}",
        ]
        
        if context.user_profile:
            parts.append(f"用户: {context.user_profile.summary}")
        
        parts.append(f"弹幕: [{event.username}] {event.content}")
        parts.append("回复要求: 50字以内，活泼友好，可以玩梗")
        
        return "\n".join(parts)
```

#### 记忆Agent（三层架构）

```python
# agents/memory_agent.py

class MemoryAgent(BaseAgent):
    """
    记忆Agent - 三层记忆管理
    L1: 工作记忆 (内存，最近10条)
    L2: 短期记忆 (SQLite，7天活跃)
    L3: 长期记忆 (向量库，压缩摘要)
    """
    
    def __init__(self):
        super().__init__("memory")
        self.l1_working: Dict[str, List[dict]] = {}  # user_id -> recent_chats
        self.l2_short = SQLiteShortTerm("data/memory_v2/short.db")
        self.l3_long = ChromaLongTerm("data/memory_v2/long.db")
        
        # Token预算
        self.max_context_tokens = 500
    
    async def recall(self, user_id: str, max_tokens: int = None) -> UserContext:
        """
        智能召回记忆
        策略: 逐级填充，直到token预算用完
        """
        max_tokens = max_tokens or self.max_context_tokens
        context_parts = []
        current_tokens = 0
        
        # L1: 工作记忆（最高优先级）
        if user_id in self.l1_working:
            working = self.l1_working[user_id][-5:]  # 最近5条
            text = "最近对话:\n" + "\n".join([
                f"{m['role']}: {m['content']}" for m in working
            ])
            context_parts.append(text)
            current_tokens += self._estimate_tokens(text)
        
        # L2: 短期记忆（用户档案）
        if current_tokens < max_tokens * 0.6:
            profile = await self.l2_short.get_user(user_id)
            if profile:
                summary = self._compress_profile(profile)
                context_parts.append(summary)
                current_tokens += self._estimate_tokens(summary)
        
        # L3: 长期记忆（向量检索）
        if current_tokens < max_tokens * 0.8:
            # 用最近对话作为查询向量
            query = self.l1_working.get(user_id, [{}])[-1].get("content", "")
            relevant = await self.l3_long.search(query, top_k=2)
            if relevant:
                text = "相关记忆:\n" + "\n".join(relevant)
                context_parts.append(text)
        
        return UserContext(
            summary="\n\n".join(context_parts),
            estimated_tokens=current_tokens
        )
    
    async def store_interaction(self, user_id: str, user_msg: str, 
                                bot_reply: str, metadata: dict):
        """存储交互（异步，不阻塞主流程）"""
        
        # 更新L1
        if user_id not in self.l1_working:
            self.l1_working[user_id] = []
        
        self.l1_working[user_id].extend([
            {"role": "user", "content": user_msg, "time": time.time()},
            {"role": "assistant", "content": bot_reply, "time": time.time()}
        ])
        self.l1_working[user_id] = self.l1_working[user_id][-10:]  # 只保留10条
        
        # 异步写入L2
        asyncio.create_task(self.l2_short.add_interaction(
            user_id, user_msg, bot_reply, metadata
        ))
        
        # 如果L2数据过多，触发压缩到L3
        if await self.l2_short.should_compress(user_id):
            asyncio.create_task(self._compress_user_memory(user_id))
    
    def _estimate_tokens(self, text: str) -> int:
        """粗略估计token数（中文约1字=1token）"""
        return len(text)
    
    def _compress_profile(self, profile: dict) -> str:
        """压缩用户档案为一句话"""
        facts = profile.get("facts", [])[-3:]  # 只取最近3条
        if facts:
            return f"[{profile['username']}] {', '.join(facts)}"
        return f"[{profile['username']}] 新观众"
```

### 4.5 欢迎Agent (WelcomeAgent)

```python
# agents/welcome_agent.py

class WelcomeAgent(BaseAgent):
    """
    欢迎Agent - 专门处理观众入场欢迎
    根据用户等级、直播间人数、时间段等动态调整欢迎策略
    """
    
    def __init__(self):
        super().__init__("welcome")
        self.throttler = WelcomeThrottler()
        self.memory_agent = None  # 将在initialize时设置
        
    async def initialize(self):
        """初始化"""
        self.memory_agent = self.conductor.agents.get("memory")
    
    async def handle_enter(self, event_data: dict, viewer_count: int) -> Optional[Decision]:
        """
        处理普通观众入场
        
        Args:
            event_data: 入场事件数据
            viewer_count: 当前直播间人数
            
        Returns:
            Decision对象或None（不欢迎）
        """
        # 更新节流器的直播间人数
        self.throttler.viewer_count = viewer_count
        
        # 创建入场事件对象
        enter_event = EnterEvent(
            user_id=event_data["user_id"],
            username=event_data["username"],
            user_level=event_data.get("user_level", 0),
            is_vip=event_data.get("is_vip", False),
            has_medal=event_data.get("has_medal", False),
            medal_name=event_data.get("medal_name", ""),
            timestamp=event_data["timestamp"]
        )
        
        # 检查是否应该欢迎
        should_welcome, reason = self.throttler.should_welcome(enter_event)
        
        if not should_welcome:
            logger.debug(f"不欢迎 {enter_event.username}: {reason}")
            return None
        
        # 获取用户历史（用于个性化欢迎）
        user_history = await self._get_user_history(enter_event.user_id)
        
        # 生成欢迎语
        welcome_text = self._generate_welcome(enter_event, user_history)
        
        # 构建决策
        return Decision(
            decision_type="WELCOME",
            content=welcome_text,
            emotion="happy",
            intensity=self._calculate_intensity(enter_event),
            gestures=["wave", "smile"] if enter_event.is_vip else ["nod"],
            voice_style="excited" if enter_event.is_vip else "normal",
            expected_outcome="user_feels_welcomed",
            store_memory=True
        )
    
    async def handle_vip_enter(self, event_data: dict) -> Decision:
        """
        处理VIP入场 - 必定欢迎，且优先级高
        """
        enter_event = EnterEvent(
            user_id=event_data["user_id"],
            username=event_data["username"],
            user_level=event_data.get("user_level", 0),
            is_vip=True,
            has_medal=event_data.get("has_medal", False),
            medal_name=event_data.get("medal_name", ""),
            timestamp=event_data["timestamp"]
        )
        
        # VIP必定获取历史记录
        user_history = await self._get_user_history(enter_event.user_id)
        
        # VIP使用特殊模板
        welcome_text = self._generate_vip_welcome(enter_event, user_history)
        
        return Decision(
            decision_type="WELCOME",
            content=welcome_text,
            emotion="excited",
            intensity=0.9,
            gestures=["wave", "smile", "heart"],
            voice_style="excited",
            expected_outcome="vip_feels_valued",
            store_memory=True
        )
    
    async def _get_user_history(self, user_id: str) -> dict:
        """获取用户历史记录"""
        if not self.memory_agent:
            return {}
        
        # 查询用户档案
        profile = await self.memory_agent.recall(user_id)
        
        return {
            "last_visit": profile.last_seen if profile else None,
            "interaction_count": profile.join_count if profile else 0,
            "recent_topics": profile.facts[-3:] if profile and profile.facts else [],
            "is_returning": profile and profile.join_count > 1
        }
    
    def _generate_welcome(self, event: EnterEvent, history: dict) -> str:
        """生成欢迎语"""
        templates = config.welcome_policy.templates
        
        # VIP/舰长回归
        if event.is_vip and history.get("is_returning"):
            template = random.choice(templates.vip_return)
            return template.format(
                username=event.username,
                medal=event.medal_name
            )
        
        # 老粉回归（有互动历史）
        if history.get("interaction_count", 0) > 5:
            template = random.choice(templates.old_fan_return)
            recent_topic = history["recent_topics"][0] if history["recent_topics"] else ""
            return template.format(
                username=event.username,
                topic=recent_topic
            )
        
        # 高等级新观众
        if event.user_level >= 20:
            template = random.choice(templates.high_level_new)
            return template.format(
                username=event.username,
                level=event.user_level
            )
        
        # 标准欢迎
        template = random.choice(templates.normal)
        return template.format(username=event.username)
    
    def _generate_vip_welcome(self, event: EnterEvent, history: dict) -> str:
        """生成VIP专属欢迎语"""
        # VIP可以有更多个性化
        if history.get("is_returning"):
            days_away = self._calculate_days_away(history["last_visit"])
            
            if days_away == 0:
                return f"{event.username}回来啦！刚才去哪儿了~"
            elif days_away <= 3:
                return f"{event.username}~ {days_away}天不见，想你了！"
            else:
                return f"欢迎{event.username}回归！好久不见，最近忙什么呢？"
        
        return f"欢迎{event.username}！感谢支持~"
    
    def _calculate_intensity(self, event: EnterEvent) -> float:
        """计算欢迎强度 (0-1)"""
        if event.is_vip:
            return 0.9
        if event.user_level >= 20:
            return 0.7
        if event.has_medal:
            return 0.6
        return 0.5


class WelcomeThrottler:
    """欢迎节流器 - 防止刷屏"""
    
    def __init__(self):
        self.recent_welcomes: List[dict] = []
        self.viewer_count = 0
        self._cleanup_task = None
    
    def should_welcome(self, event: EnterEvent) -> Tuple[bool, str]:
        """判断是否该欢迎"""
        now = time.time()
        
        # 清理过期记录（保留10分钟）
        self.recent_welcomes = [
            w for w in self.recent_welcomes 
            if now - w["time"] < 600
        ]
        
        # 获取当前策略
        policy = self._get_current_policy()
        
        # VIP直接通过
        if event.is_vip:
            return True, "VIP用户"
        
        # 检查是否被策略排除
        if not policy["welcome_all"]:
            if event.user_level < policy.get("min_user_level", 0):
                return False, f"用户等级{event.user_level}低于阈值{policy['min_user_level']}"
            
            if policy.get("only_vip") and not event.is_vip:
                return False, "当前只欢迎VIP"
        
        # 检查频率限制
        recent_count = len(self.recent_welcomes)
        max_per_minute = policy.get("max_per_minute", 10)
        
        if recent_count >= max_per_minute:
            return False, f"超过每分钟欢迎上限({max_per_minute})"
        
        # 检查是否重复欢迎（同一人10分钟内）
        for welcome in self.recent_welcomes:
            if welcome["user_id"] == event.user_id:
                return False, "10分钟内已欢迎过"
        
        # 记录本次欢迎
        self.recent_welcomes.append({
            "user_id": event.user_id,
            "time": now,
            "username": event.username
        })
        
        return True, "通过所有检查"
    
    def _get_current_policy(self) -> dict:
        """根据直播间人数获取当前策略"""
        policy_config = config.welcome_policy.by_viewer_count
        
        if self.viewer_count < policy_config.low.threshold:
            return {
                "welcome_all": True,
                "max_per_minute": policy_config.low.max_per_minute
            }
        elif self.viewer_count < policy_config.medium.threshold:
            return {
                "welcome_all": False,
                "min_user_level": policy_config.medium.min_user_level,
                "max_per_minute": policy_config.medium.max_per_minute
            }
        else:
            return {
                "welcome_all": False,
                "min_user_level": policy_config.high.min_user_level,
                "max_per_minute": policy_config.high.max_per_minute,
                "only_vip": False
            }
```

### 4.6 自我进化Agent

```python
# agents/evolution_agent.py

class EvolutionAgent(BaseAgent):
    """
    进化Agent - 后台自我优化
    在无人模式下运行，不影响实时交互
    """
    
    def __init__(self):
        super().__init__("evolution")
        self.learning_sources = [
            {"name": "weibo", "url": "https://weibo.com/hot/search", "weight": 0.8},
            {"name": "xiaohongshu", "url": "...", "weight": 0.6},
        ]
        self.reflection_logs = []
    
    async def on_mode_change(self, mode: LiveMode):
        """进入无人模式时启动进化"""
        if mode == LiveMode.LEARNING:
            asyncio.create_task(self._evolution_loop())
    
    async def _evolution_loop(self):
        """进化主循环"""
        while self.conductor.mode == LiveMode.LEARNING:
            try:
                # 1. 学习新知识
                await self._learn_new_knowledge()
                
                # 2. 反思今日表现
                await self._reflect_today()
                
                # 3. 优化策略
                await self._optimize_strategy()
                
                # 4. 压缩旧记忆
                await self._compress_memories()
                
            except Exception as e:
                logger.error(f"Evolution error: {e}")
            
            # 休眠一段时间
            await asyncio.sleep(3600)  # 每小时检查一次
    
    async def _learn_new_knowledge(self):
        """学习新知识"""
        for source in self.learning_sources:
            if source["weight"] < 0.3:
                continue  # 跳过低权重来源
            
            # 爬取内容
            content = await self._crawl(source["url"])
            
            # 提取有价值信息
            summary = await self.llm.summarize(content)
            
            # 存储
            await self.knowledge_base.store(summary, source=source["name"])
    
    async def _reflect_today(self):
        """反思今日表现"""
        # 读取今日日志
        logs = await self._load_today_logs()
        
        # 分析指标
        stats = {
            "total_interactions": len(logs),
            "avg_response_time": sum(l["response_time"] for l in logs) / len(logs),
            "topic_performance": self._analyze_topic_performance(logs),
            "ignored_rate": len([l for l in logs if l["ignored"]]) / len(logs)
        }
        
        # 生成洞察
        insights = await self.llm.analyze(f"""
        今日数据: {json.dumps(stats, ensure_ascii=False)}
        请分析:
        1. 哪些话题效果好？为什么？
        2. 哪些回复被忽略了？如何改进？
        3. 有什么可以优化的策略？
        """)
        
        self.reflection_logs.append({
            "date": datetime.now(),
            "stats": stats,
            "insights": insights
        })
    
    async def _optimize_strategy(self):
        """基于反思优化策略"""
        if len(self.reflection_logs) < 3:
            return  # 数据不足
        
        # 分析趋势
        recent_logs = self.reflection_logs[-7:]  # 最近7天
        
        # 调整来源权重
        for source in self.learning_sources:
            effectiveness = self._calculate_source_effectiveness(
                source["name"], recent_logs
            )
            source["weight"] = min(1.0, effectiveness * 1.2)
        
        # 生成新配置
        new_config = {
            "learning_sources": self.learning_sources,
            "topic_weights": self._calculate_topic_weights(recent_logs),
            "response_templates": await self._optimize_templates(recent_logs)
        }
        
        # 保存配置
        await self._save_strategy(new_config)
        
        # 通知大脑Agent更新
        self.emit(Event(
            event_type=EventType.STRATEGY_UPDATE,
            payload=new_config,
            source=self.name
        ))
```

---

## 五、改造路线图

### Phase 1: 基础设施 (Week 1)

**目标**: 搭建事件总线和Conductor框架

| 任务 | 工作量 | 输出 |
|------|--------|------|
| 实现Event Bus | 1天 | core/event_bus.py |
| 实现Conductor | 2天 | core/conductor.py + 状态机 |
| 实现Agent基类 | 1天 | agents/base.py |
| 重构main.py | 1天 | 使用新架构启动 |

**验证标准**: 
- 系统能正常启动
- 弹幕能触发事件
- Conductor能切换模式

### Phase 2: Agent拆分 (Week 2-3)

**目标**: 将现有功能拆分到各Agent

| 任务 | 工作量 | 说明 |
|------|--------|------|
| SensorAgent | 2天 | 从bilibili_danmaku迁移解析逻辑 |
| BrainAgent | 3天 | 从LiveSession迁移LLM调用 |
| MemoryAgent V2 | 3天 | 实现三层记忆，迁移原有JSON数据 |
| ExpressAgent | 2天 | 整合TTS和VTube Studio |

**验证标准**:
- 完整交互链路跑通
- 功能与改造前一致

### Phase 3: 记忆优化 (Week 4)

**目标**: 实现三层记忆和Token控制

| 任务 | 工作量 | 说明 |
|------|--------|------|
| L2 SQLite实现 | 2天 | 短期记忆数据库存储 |
| L3 向量库集成 | 2天 | Chroma/Milvus接入 |
| 记忆压缩逻辑 | 2天 | 自动压缩旧记忆 |
| Token控制 | 1天 | 严格控制上下文长度 |

**验证标准**:
- 上下文token < 500
- 记忆查询延迟 < 100ms

### Phase 4: 自我进化 (Week 5-6)

**目标**: 实现进化Agent和自我优化

| 任务 | 工作量 | 说明 |
|------|--------|------|
| EvolutionAgent框架 | 2天 | 后台运行框架 |
| 数据收集 | 2天 | 日志分析和指标统计 |
| 反思逻辑 | 3天 | LLM分析和洞察生成 |
| 策略优化 | 3天 | 自动调整配置 |

**验证标准**:
- 无人时能自动学习
- 策略会根据效果调整

---

## 六、数据结构定义

### 6.1 核心数据类

```python
# core/models.py

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime

@dataclass
class UserProfile:
    """用户档案"""
    user_id: str
    username: str
    user_type: str = "regular"  # regular/vip
    join_count: int = 0
    last_seen: datetime = None
    facts: List[str] = None
    preferences: Dict[str, Any] = None
    created_at: datetime = None
    
    def __post_init__(self):
        if self.facts is None:
            self.facts = []
        if self.preferences is None:
            self.preferences = {}
        if self.created_at is None:
            self.created_at = datetime.now()
    
    @property
    def summary(self) -> str:
        """一句话摘要"""
        recent_facts = self.facts[-3:] if self.facts else []
        if recent_facts:
            return f"[{self.username}] {', '.join(recent_facts)}"
        return f"[{self.username}] 新观众"

@dataclass
class ParsedEvent:
    """感知Agent输出的事件"""
    user_id: str
    username: str
    content: str
    intent: str
    emotion: str
    importance: int
    timestamp: float
    metadata: Dict[str, Any] = None

@dataclass
class Decision:
    """大脑Agent输出的决策"""
    decision_type: str  # REPLY / ACTION / IGNORE
    content: str  # 回复内容
    emotion: str  # 情感标签
    intensity: float  # 强度 0-1
    gestures: List[str]  # 表情动作
    voice_style: str  # 语音风格
    expected_outcome: str  # 预期效果
    store_memory: bool  # 是否存储记忆
    metadata: Dict[str, Any] = None

@dataclass
class LiveContext:
    """直播上下文（只读）"""
    timestamp: datetime
    session_start: datetime
    viewer_count: int
    current_mode: str
    last_interaction: float
    current_user: Optional[UserProfile] = None
    recent_danmaku: List[str] = None
    topic_tags: List[str] = None
    
    @property
    def session_duration(self) -> int:
        return int((self.timestamp - self.session_start).total_seconds())
    
    def with_memory(self, memory_context: "UserContext") -> "LiveContext":
        """返回带有记忆的新Context"""
        # Context不可变，返回新实例
        new_context = LiveContext(
            timestamp=self.timestamp,
            session_start=self.session_start,
            viewer_count=self.viewer_count,
            current_mode=self.current_mode,
            last_interaction=self.last_interaction,
            current_user=self.current_user,
            recent_danmaku=self.recent_danmaku,
            topic_tags=self.topic_tags
        )
        new_context.memory_context = memory_context
        return new_context

@dataclass
class UserContext:
    """用户记忆上下文"""
    summary: str
    estimated_tokens: int
    sources: List[str] = None  # 记忆来源（L1/L2/L3）
```

---

## 七、配置规范

### 7.1 主配置文件

```yaml
# config/system.yaml

# Agent配置
agents:
  sensor:
    intent_classifier: "rule"  # rule / mini_model
    emotion_analysis: true
    
  brain:
    default_model: "kimi"
    fallback_model: "claude"
    max_tokens: 150
    temperature: 0.7
    
  memory:
    max_context_tokens: 500
    l1_size: 10  # 工作记忆条数
    l2_retention_days: 7
    compression_threshold: 100  # L2超过100条触发压缩
    
  express:
    tts_engine: "edge"  # edge / gpt_sovits
    vtube_enabled: true
    gesture_delay: 0.5  # 表情延迟(秒)
    
  evolution:
    enabled: true
    run_interval: 3600  # 进化间隔(秒)
    learning_sources:
      - name: "weibo"
        weight: 0.8
        max_items: 10
      - name: "xiaohongshu"
        weight: 0.6
        max_items: 5

# 模式切换配置
mode_switch:
  idle_timeout: 300  # 5分钟无弹幕进入idle
  sleep_start: 2     # 深夜模式开始(2点)
  sleep_end: 6       # 深夜模式结束(6点)
  learning_min_silence: 600  # 10分钟无人开始学习

# 人设配置
character:
  name: "小K"
  persona: "活泼女大学生游戏主播"
  speaking_style: "简短口语化，带emoji"
  interests: ["原神", "王者", "Steam独立游戏"]
  traits: ["毒舌", "爱吐槽", "偶尔卖萌"]
```

---

## 八、关键算法

### 8.1 Token控制算法

```python
def build_context_with_budget(events: List[Event], 
                               user_profile: UserProfile,
                               max_tokens: int = 500) -> str:
    """
    智能构建上下文，严格控制token预算
    """
    parts = []
    budget = max_tokens
    
    # 1. 人设 (固定开销 ~50 tokens)
    persona = "人设: 活泼女大学生主播，简短回复带emoji"
    parts.append(persona)
    budget -= 50
    
    # 2. 用户档案 (优先级高)
    if user_profile:
        profile_text = user_profile.summary
        profile_tokens = len(profile_text)
        
        if profile_tokens < budget * 0.4:  # 占用不超过40%
            parts.append(profile_text)
            budget -= profile_tokens
    
    # 3. 最近对话 (填充剩余空间)
    recent_chats = []
    for event in reversed(events):  # 从近到远
        chat_line = f"{event.username}: {event.content}"
        line_tokens = len(chat_line)
        
        if line_tokens < budget * 0.5:  # 留50%给回复
            recent_chats.insert(0, chat_line)
            budget -= line_tokens
        else:
            break
    
    if recent_chats:
        parts.append("最近对话:\n" + "\n".join(recent_chats))
    
    return "\n\n".join(parts)
```

### 8.2 记忆压缩算法

```python
async def compress_conversation(history: List[dict]) -> str:
    """
    将对话历史压缩为关键信息
    """
    if len(history) <= 3:
        return "近期互动: " + "; ".join([
            f"{h['role']}说{h['content'][:20]}" 
            for h in history
        ])
    
    # 使用LLM提取关键信息
    prompt = f"""
    将以下对话压缩为2-3条关键事实，用于后续回忆：
    {json.dumps(history, ensure_ascii=False)}
    
    格式：
    - 事实1
    - 事实2
    """
    
    result = await llm.extract(prompt)
    return result
```

---

## 九、测试策略

### 9.1 单元测试

```python
# tests/test_sensor_agent.py

async def test_intent_classification():
    sensor = SensorAgent()
    
    test_cases = [
        ("你好", "greeting"),
        ("!帮我整理背包", "command"),
        ("为什么打不过", "question"),
        ("哈哈哈笑死", "reaction"),
    ]
    
    for content, expected in test_cases:
        event = await sensor.process({
            "user_id": "123",
            "username": "test",
            "content": content
        })
        assert event.intent == expected, f"Failed for: {content}"

# tests/test_memory_agent.py

async def test_memory_recall_budget():
    memory = MemoryAgent(max_context_tokens=500)
    
    # 添加大量记忆
    for i in range(100):
        await memory.store_interaction("user1", f"消息{i}", f"回复{i}")
    
    context = await memory.recall("user1")
    
    # 验证token预算
    assert context.estimated_tokens <= 500
    # 验证包含最近对话
    assert "消息99" in context.summary
```

### 9.2 集成测试

```python
# 完整链路测试
async def test_full_pipeline():
    # 初始化系统
    bus = EventBus()
    conductor = Conductor(bus)
    
    # 注册Agents
    conductor.register_agent("sensor", SensorAgent())
    conductor.register_agent("brain", BrainAgent(mock_llm))
    conductor.register_agent("memory", MemoryAgent())
    conductor.register_agent("welcome", WelcomeAgent())  # 新增欢迎Agent
    conductor.register_agent("express", MockExpressAgent())
    
    # 模拟弹幕事件
    await bus.publish(Event(
        event_type=EventType.DANMAKU,
        payload={"user_id": "123", "username": "test", "content": "你好"},
        source="test"
    ))
    
    # 等待处理
    await asyncio.sleep(1)
    
    # 验证ExpressAgent收到了决策
    express = conductor.agents["express"]
    assert len(express.received_decisions) == 1
    assert "你好" in express.received_decisions[0].content

# 入场欢迎测试
async def test_welcome_flow():
    """测试入场欢迎流程"""
    welcome_agent = WelcomeAgent()
    
    # 场景1: 直播间人少，普通用户应该被欢迎
    decision = await welcome_agent.handle_enter(
        {"user_id": "1", "username": "路人", "user_level": 5},
        viewer_count=10
    )
    assert decision is not None
    
    # 场景2: 直播间人多，普通用户不应被欢迎
    decision = await welcome_agent.handle_enter(
        {"user_id": "2", "username": "路人2", "user_level": 5},
        viewer_count=100
    )
    assert decision is None  # 被节流
    
    # 场景3: VIP用户无论人数都应被欢迎
    decision = await welcome_agent.handle_vip_enter(
        {"user_id": "3", "username": "舰长大人", "user_level": 30, "is_vip": True}
    )
    assert decision is not None
    assert decision.intensity > 0.8  # VIP高强度欢迎
```

---

## 十、部署与监控

### 10.1 监控指标

| 指标 | 类型 | 阈值 | 说明 |
|------|------|------|------|
| event_processing_time | Histogram | < 100ms | 事件处理延迟 |
| llm_request_duration | Histogram | < 2s | LLM调用延迟 |
| memory_query_time | Gauge | < 50ms | 记忆查询时间 |
| context_token_count | Gauge | < 500 | 上下文token数 |
| mode_switch_count | Counter | - | 模式切换次数 |
| agent_error_rate | Rate | < 1% | Agent错误率 |

### 10.2 日志规范

```python
# 结构化日志
logger.info("event_processed", {
    "event_type": "danmaku",
    "user_id": "123",
    "processing_time_ms": 45,
    "agent_path": ["sensor", "memory", "brain", "express"]
})

logger.info("decision_made", {
    "decision_type": "reply",
    "model_used": "kimi",
    "token_used": 320,
    "expected_outcome": "user_response"
})
```

---

## 十一、总结

### 11.1 核心改进点

| 维度 | 改造前 | 改造后 |
|------|--------|--------|
| 架构 | 单体，高度耦合 | 多Agent，事件驱动 |
| 记忆 | JSON文件无限增长 | 三层架构，自动压缩 |
| 入场欢迎 | 无或简单打印 | **智能分层欢迎（VIP优先）** |
| Token | 无控制，易爆炸 | 严格预算，智能召回 |
| 进化 | 外部脚本定时更新 | Agent自主反思优化 |
| 扩展 | 改动困难 | 新增Agent即插即用 |

### 11.2 预期收益

1. **可维护性**: 各Agent独立，修改不影响其他模块
2. **可扩展性**: 新增功能只需新增Agent
3. **智能程度**: 自我进化，越播越聪明
4. **成本控制**: Token控制+模型路由，降低API费用
5. **可观测性**: 全链路事件追踪，问题定位快

### 11.3 风险提示

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 改造成本高 | 2-3周工作量 | 分阶段实施，每阶段可独立运行 |
| 调试复杂 | 多Agent难追踪 | 完善日志，提供事件回放工具 |
| 性能下降 | 事件序列化开销 | 异步处理，关键路径保持高效 |
| 进化失控 | 策略优化走偏 | 人工审核重大策略变更 |

---

## 附录：参考资源

- [CrewAI 多Agent框架](https://docs.crewai.com/)
- [AutoGen 对话系统](https://microsoft.github.io/autogen/)
- [LangGraph 状态管理](https://langchain-ai.github.io/langgraph/)
- [Mem0 记忆层](https://github.com/mem0ai/mem0)

---

*文档结束*

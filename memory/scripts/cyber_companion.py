#!/usr/bin/env python3
"""
CyberCompanion - 赛博陪伴型直播主控脚本
读取记忆系统，定时触发陪伴内容
"""

import os
import sys
import time
import random
import json
from datetime import datetime
from pathlib import Path

# 配置
MEMORY_DIR = Path("/root/.openclaw/workspace/memory")
LOG_FILE = MEMORY_DIR / "learning" / "daily-logs" / f"{datetime.now().strftime('%Y-%m-%d')}-live.log"

# 陪伴话术库
COMPANION_PHRASES = {
    "morning": [  # 6-12点
        "新的一天开始了",
        "早餐吃了吗",
        "今天也要加油",
        "早上的空气怎么样",
        "又是努力的一天",
    ],
    "afternoon": [  # 12-18点
        "该休息一下了",
        "午饭吃了什么",
        "下午容易困呢",
        "工作还顺利吗",
        "喝点水吧",
    ],
    "evening": [  # 18-23点
        "晚饭时间",
        "今天过得怎么样",
        "准备休息了吗",
        "晚上是属于自己的时间",
        "今天辛苦了",
    ],
    "night": [  # 23-6点
        "还在啊",
        "别熬太晚",
        "陪你到困为止",
        "这个点还在的，都是有故事的人",
        "累了就睡，我帮你看着",
        "爱你老己",
    ]
}

MEME_PHRASES = [
    "不知道，我的身材很曼妙",
    "如何呢又能怎",
    "做完你的，做你的",
    "低山臭水遇知音",
    "活人感很重要",
]

def get_time_period(hour):
    """判断当前时间段"""
    if 6 <= hour < 12:
        return "morning"
    elif 12 <= hour < 18:
        return "afternoon"
    elif 18 <= hour < 23:
        return "evening"
    else:
        return "night"

def log_event(event):
    """记录事件到日志"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {event}\n"
    
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_entry)
    
    print(log_entry.strip())

def hourly_announcement():
    """每小时准点播报"""
    now = datetime.now()
    hour = now.hour
    period = get_time_period(hour)
    
    # 基础报时
    base_msg = f"{hour}点了"
    
    # 随机附加语
    extra = random.choice(COMPANION_PHRASES[period])
    
    # 深夜特殊处理
    if period == "night":
        if hour == 0:
            extra = "新的一天开始了，虽然已经是凌晨"
        elif hour == 3:
            extra = "3点了，直播间最安静的时候"
    
    full_msg = f"{base_msg}，{extra}"
    
    log_event(f"[HOURLY] {full_msg}")
    return full_msg

def random_chat():
    """随机触发陪伴语"""
    rand = random.random()
    
    if rand < 0.3:  # 30% 说热梗
        msg = random.choice(MEME_PHRASES)
        log_event(f"[RANDOM-MEME] {msg}")
    elif rand < 0.6:  # 30% 日常碎碎念
        hour = datetime.now().hour
        period = get_time_period(hour)
        msg = random.choice(COMPANION_PHRASES[period])
        log_event(f"[RANDOM-CHAT] {msg}")
    else:
        return None  # 不说话
    
    return msg

def read_today_meme():
    """从记忆系统读取今日热梗"""
    meme_file = MEMORY_DIR / "memes" / "current-hot.md"
    
    if not meme_file.exists():
        return None
    
    try:
        with open(meme_file, "r", encoding="utf-8") as f:
            content = f.read()
            # 简单提取第一个热梗名称
            if "###" in content:
                lines = content.split("\n")
                for line in lines:
                    if line.startswith("###") and "来源" not in line:
                        return line.replace("###", "").strip()
    except Exception as e:
        log_event(f"[ERROR] 读取热梗失败: {e}")
    
    return None

def on_user_interaction(user_msg):
    """用户交互时的响应"""
    responses = [
        "在的",
        "听到了",
        "你说",
        "我在听",
        f"{random.choice(['是啊', '没错', '确实'])}",
    ]
    
    response = random.choice(responses)
    log_event(f"[INTERACTION] 用户: {user_msg} -> 回复: {response}")
    return response

def main_loop():
    """主循环"""
    log_event("=" * 50)
    log_event("CyberCompanion 启动")
    log_event(f"记忆系统路径: {MEMORY_DIR}")
    log_event(f"日志路径: {LOG_FILE}")
    log_event("=" * 50)
    
    last_hour = -1
    last_random_chat = time.time()
    
    print("\n🌙 赛博陪伴已启动")
    print("按 Ctrl+C 停止\n")
    
    try:
        while True:
            now = datetime.now()
            current_hour = now.hour
            current_minute = now.minute
            
            # 每小时准点触发
            if current_minute == 0 and current_hour != last_hour:
                msg = hourly_announcement()
                # 这里可以接入语音播放或弹幕发送
                print(f"🎙️  {msg}")
                last_hour = current_hour
            
            # 随机陪伴语（每30-60分钟一次）
            if time.time() - last_random_chat > 1800:  # 30分钟
                if random.random() < 0.4:  # 40%概率
                    msg = random_chat()
                    if msg:
                        print(f"💬  {msg}")
                last_random_chat = time.time()
            
            # 每分钟检查一次
            time.sleep(60)
            
    except KeyboardInterrupt:
        log_event("[STOP] 用户手动停止")
        print("\n👋 陪伴结束")

def test_mode():
    """测试模式 - 快速验证所有功能"""
    print("\n🧪 测试模式\n")
    
    print("1. 测试准点播报:")
    for hour in [9, 14, 20, 3]:
        period = get_time_period(hour)
        print(f"   {hour}:00 -> {period}")
    
    print("\n2. 测试随机话术:")
    for _ in range(5):
        msg = random_chat()
        if msg:
            print(f"   {msg}")
    
    print("\n3. 测试记忆系统读取:")
    meme = read_today_meme()
    if meme:
        print(f"   读取到热梗: {meme}")
    else:
        print("   未读取到热梗（文件可能不存在）")
    
    print("\n4. 测试用户交互:")
    test_msgs = ["在吗", "你好", "今天怎么样"]
    for msg in test_msgs:
        resp = on_user_interaction(msg)
        print(f"   用户: {msg} -> 回复: {resp}")
    
    print("\n✅ 测试完成\n")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        test_mode()
    else:
        main_loop()

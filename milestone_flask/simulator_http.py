"""
HTTP模拟器 - 调用8080端口API
"""
import time
import random
import requests

fake_users = ["小可爱", "路人甲", "B站用户", "舰长大人", "吃瓜群众",
              "老粉", "新来的", "夜猫子", "打工人", "学生党",
              "大佬", "萌新", "围观群众", "潜水员", "活跃粉"]

messages = ["主播好！", "来了来了", "晚上好", "666", "哈哈哈",
            "这波可以", "爱了爱了", "打卡", "第一", "好听"]

print("🎮 HTTP模拟器启动！向 http://localhost:8080 发送模拟数据...\n")

count = 0
while True:
    try:
        time.sleep(2)  # 每2秒一个事件
        user = random.choice(fake_users)
        rand = random.random()
        
        if rand < 0.4:
            # 入场
            r = requests.post('http://localhost:8080/api/event', 
                            json={"type": "enter", "user": user},
                            timeout=5)
            count += 1
            print(f"👥 [{count}] {user} 进入直播间")
            
        elif rand < 0.85:
            # 弹幕
            msg = random.choice(messages)
            r = requests.post('http://localhost:8080/api/event',
                            json={"type": "chat", "user": f"{user}: {msg}"},
                            timeout=5)
            count += 1
            print(f"💬 [{count}] {user}: {msg}")
            
        else:
            # 礼物
            gifts = ["小花花", "辣条", "奶茶", "小心心", "大火箭"]
            gift = random.choice(gifts)
            r = requests.post('http://localhost:8080/api/event',
                            json={"type": "gift", "user": user, "data": {"gift_name": gift}},
                            timeout=5)
            count += 1
            print(f"🎁 [{count}] {user} 赠送了 {gift}!")
            
    except Exception as e:
        print(f"❌ 错误: {e}")
        time.sleep(3)

"""
里程碑系统 Demo 启动器
一键启动，自动模拟数据，立刻看到效果
"""
import sys
import time
import random
import threading
from pathlib import Path

# 切换到当前目录
sys.path.insert(0, str(Path(__file__).parent))

from app import start_server, data_store


def simulate_live_stream():
    """
    模拟直播数据
    自动产生入场、弹幕、礼物事件
    """
    fake_users = [
        "小可爱", "路人甲", "B站用户", "舰长大人", "吃瓜群众",
        "老粉", "新来的", "夜猫子", "打工人", "学生党",
        "大佬", "萌新", "围观群众", "潜水员", "活跃粉"
    ]
    
    messages = [
        "主播好！", "来了来了", "晚上好", "666", "哈哈哈",
        "这波可以", "爱了爱了", "打卡", "第一", "好听"
    ]
    
    print("\n🎮 Demo模式启动！自动模拟直播数据...\n")
    print("=" * 50)
    
    while True:
        try:
            # 随机等待 1-5 秒
            time.sleep(random.uniform(1, 5))
            
            # 随机选择事件类型
            rand = random.random()
            user = random.choice(fake_users)
            
            if rand < 0.4:
                # 40% 概率：有人入场
                result = data_store.add_event("enter", user)
                print(f"👥 [{result['current']['today']['enters']:3d}] {user} 进入直播间 +{result['xp_gained']}XP")
                
            elif rand < 0.85:
                # 45% 概率：弹幕聊天
                msg = random.choice(messages)
                result = data_store.add_event("chat", f"{user}: {msg}")
                print(f"💬 [{result['current']['today']['chats']:3d}] {user}: {msg} +{result['xp_gained']}XP")
                
            else:
                # 15% 概率：收到礼物（大额经验）
                gifts = ["小花花", "辣条", "奶茶", "小心心", "大火箭"]
                gift = random.choice(gifts)
                result = data_store.add_event("gift", user, {"gift_name": gift})
                print(f"🎁 [{result['current']['today']['gifts']:3d}] {user} 赠送了 {gift}! +{result['xp_gained']}XP")
            
            # 如果有升级，额外显示
            if result.get('level_up'):
                level_info = result['level_up']
                print("\n" + "=" * 50)
                print(f"🎉🎉🎉 恭喜升级！Lv.{level_info['new_level']} {level_info['name']} {level_info['icon']} 🎉🎉🎉")
                print("=" * 50 + "\n")
                
        except Exception as e:
            print(f"模拟出错: {e}")
            time.sleep(1)


def main():
    """启动 Demo"""
    print("""
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║   🎮 vitUber 里程碑系统 Demo                             ║
║                                                          ║
║   1. 启动 Flask 服务器...                                ║
║   2. 自动模拟直播数据...                                 ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
    """)
    
    # 启动模拟数据线程
    sim_thread = threading.Thread(target=simulate_live_stream, daemon=True)
    sim_thread.start()
    
    # 启动 Flask 服务器（阻塞主线程）
    print("\n🚀 启动服务器...")
    print("📍 访问地址: http://localhost:5000")
    print("📊 OBS浏览器源: http://localhost:5000")
    print("\n💡 提示: 用浏览器打开 http://localhost:5000 即可看到效果！")
    print("=" * 50 + "\n")
    
    start_server(host='0.0.0.0', port=5000, debug=False)


if __name__ == '__main__':
    main()

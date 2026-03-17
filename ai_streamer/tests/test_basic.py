# AI虚拟主播测试脚本
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.memory_manager import MemoryManager
from core.llm_client import LLMClient
from core.command_parser import CommandParser


async def test_memory():
    """测试记忆系统"""
    print("=" * 50)
    print("测试记忆系统")
    print("=" * 50)
    
    memory = MemoryManager()
    
    # 添加用户
    memory.add_fact("user1", "喜欢玩法系角色", "小明")
    memory.add_fact("user1", "是学生", "小明")
    
    # 获取上下文
    context = memory.get_context_for_llm("user1", "小明")
    print(f"\n用户上下文:\n{context}")
    
    print("\n✓ 记忆系统测试通过\n")


async def test_llm():
    """测试LLM"""
    print("=" * 50)
    print("测试LLM客户端")
    print("=" * 50)
    
    try:
        llm = LLMClient()
        
        response = llm.chat("你好呀", "当前用户: 测试用户 (regular)")
        print(f"\n用户: 你好呀")
        print(f"AI: {response.text}")
        print(f"动作: {response.actions}")
        print(f"事实: {response.facts}")
        
        print("\n✓ LLM测试通过\n")
    except Exception as e:
        print(f"\n✗ LLM测试失败: {e}\n")


async def test_command_parser():
    """测试指令解析"""
    print("=" * 50)
    print("测试指令解析")
    print("=" * 50)
    
    parser = CommandParser()
    
    test_messages = [
        "帮我整理背包",
        "打开背包看看",
        "向下滚动一下",
        "截个图",
        "今天天气真好",  # 不是指令
    ]
    
    for msg in test_messages:
        result = parser.parse(msg)
        print(f"'{msg}' -> {result}")
    
    print("\n✓ 指令解析测试通过\n")


async def main():
    """运行所有测试"""
    print("\n🎮 AI虚拟主播测试套件\n")
    
    # 测试记忆系统
    await test_memory()
    
    # 测试指令解析
    await test_command_parser()
    
    # 测试LLM（需要API密钥）
    try:
        await test_llm()
    except Exception as e:
        print(f"LLM测试跳过: {e}")
    
    print("=" * 50)
    print("测试完成!")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())

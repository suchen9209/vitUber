#!/usr/bin/env python3
"""
记忆系统整合初始化脚本
一键将memory系统和ai_streamer整合
"""
import os
import sys
import shutil
from pathlib import Path
from loguru import logger


def setup_memory_symlink():
    """创建memory目录的符号链接（如果需要）"""
    ai_streamer_dir = Path(__file__).parent.parent
    memory_link = ai_streamer_dir / "memory"
    
    # 检查是否已经有memory目录
    if memory_link.exists():
        if memory_link.is_symlink():
            logger.info("memory符号链接已存在")
            return True
        elif memory_link.is_dir():
            logger.info("memory目录已存在（可能是独立的）")
            return True
    
    # 查找memory目录
    possible_paths = [
        ai_streamer_dir.parent / "memory",  # 同级的memory
        Path("/root/.openclaw/workspace/memory"),  # 绝对路径
    ]
    
    for memory_path in possible_paths:
        if memory_path.exists():
            try:
                memory_link.symlink_to(memory_path, target_is_directory=True)
                logger.info(f"创建符号链接: {memory_link} -> {memory_path}")
                return True
            except Exception as e:
                logger.error(f"创建符号链接失败: {e}")
                return False
    
    logger.warning("未找到memory目录，请手动创建")
    return False


def check_integration():
    """检查整合状态"""
    ai_streamer_dir = Path(__file__).parent.parent
    
    checks = {
        "memory_bridge": ai_streamer_dir / "core" / "memory_bridge.py",
        "companion_mode": ai_streamer_dir / "core" / "companion_mode.py",
        "memory_dir": ai_streamer_dir / "memory",
    }
    
    results = {}
    for name, path in checks.items():
        exists = path.exists()
        results[name] = exists
        status = "✅" if exists else "❌"
        print(f"{status} {name}: {path}")
    
    return all(results.values())


def test_memory_bridge():
    """测试记忆桥接器"""
    print("\n🧪 测试记忆桥接器...")
    
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from core.memory_bridge import get_memory_bridge
        
        bridge = get_memory_bridge()
        
        print(f"  加载了 {len(bridge.memes_cache)} 个热梗")
        print(f"  加载了 {len(bridge.events_cache)} 个事件")
        
        # 测试生成内容
        meme_chat = bridge.generate_meme_chat()
        if meme_chat:
            print(f"  示例热梗话题: {meme_chat[:50]}...")
        
        hourly = bridge.generate_hourly_announcement()
        print(f"  示例整点播报: {hourly}")
        
        return True
        
    except Exception as e:
        logger.error(f"测试失败: {e}")
        return False


def main():
    """主函数"""
    print("=" * 50)
    print("记忆系统整合初始化")
    print("=" * 50)
    
    # 1. 设置符号链接
    print("\n📁 设置目录链接...")
    setup_memory_symlink()
    
    # 2. 检查整合状态
    print("\n🔍 检查整合状态...")
    if check_integration():
        print("\n✅ 所有组件已就绪")
    else:
        print("\n⚠️ 部分组件缺失")
    
    # 3. 测试
    print("\n" + "=" * 50)
    if test_memory_bridge():
        print("\n✅ 测试通过！")
    else:
        print("\n❌ 测试失败，请检查错误")
    
    print("\n" + "=" * 50)
    print("初始化完成")
    print("=" * 50)


if __name__ == "__main__":
    main()

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
快速检查日志中的优化信息
"""

import sys
import os

def find_log_file():
    """查找日志文件"""
    possible_paths = [
        "log.txt",
        "app.log",
        "picacg.log",
        "src/log.txt",
        "src/app.log",
    ]

    for path in possible_paths:
        if os.path.exists(path):
            return path

    return None

def check_optimization_logs(log_file):
    """检查日志中的优化相关信息"""

    if not log_file or not os.path.exists(log_file):
        print("❌ 未找到日志文件")
        print("\n请手动指定日志文件路径:")
        print("  python check_logs.py <日志文件路径>")
        return False

    print(f"📄 读取日志文件: {log_file}")
    print("="*70)

    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    # 检查关键标记
    checks = {
        "Phase 4 - 启动优化": [
            "[Startup]",
            "Application starting",
            "Waifu2x models loading started in background",
            "Application started in"
        ],
        "Waifu2x功能": [
            "Waifu2x init",
            "SR_VULKAN",
            "init model num"
        ],
        "性能日志": [
            "consume",
            "elapsed",
            ".XXs"
        ]
    }

    all_found = True

    for category, markers in checks.items():
        print(f"\n【{category}】")
        found_any = False
        for marker in markers:
            if marker in content:
                print(f"  ✅ 找到: {marker}")
                found_any = True
                # 打印相关行
                for line in content.split('\n'):
                    if marker in line:
                        print(f"     → {line.strip()}")
                        break
            else:
                print(f"  ⚠️  未找到: {marker}")

        if found_any:
            print(f"  ✅ {category} 相关日志存在")
        else:
            print(f"  ❌ {category} 相关日志缺失")
            all_found = False

    print("\n" + "="*70)

    # 提取关键性能数据
    print("\n【性能数据提取】")

    # 提取启动时间
    for line in content.split('\n'):
        if "Application started in" in line:
            print(f"  ⚡ 启动时间: {line.strip()}")
        elif "Waifu2x models loaded in" in line:
            print(f"  🔧 Waifu2x加载: {line.strip()}")
        elif "Waifu2x init" in line and "WARNING" in line:
            print(f"  ✅ Waifu2x状态: {line.strip()}")

    print("\n" + "="*70)

    if all_found:
        print("✅ 所有优化相关日志都找到了！")
        print("\n建议：查看上面提取的性能数据，验证优化效果")
    else:
        print("⚠️  部分日志缺失，但这不一定意味着优化无效")
        print("\n可能原因：")
        print("  1. 日志级别设置导致部分日志未输出")
        print("  2. 日志被截断或轮转")
        print("  3. 查看的是旧的日志文件")
        print("\n建议：")
        print("  1. 重新启动应用生成新日志")
        print("  2. 通过主观感受验证优化效果（更直观）")

    return all_found

if __name__ == "__main__":
    if len(sys.argv) > 1:
        log_file = sys.argv[1]
    else:
        log_file = find_log_file()

    check_optimization_logs(log_file)

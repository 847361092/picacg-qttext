#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
显卡检测脚本 - 诊断Tile Size为什么不是2048
"""

import subprocess

print("="*70)
print("         显卡信息诊断")
print("="*70)
print()

# 方法1：使用nvidia-smi检测显存
print("【nvidia-smi检测】")
try:
    result = subprocess.run(
        ['nvidia-smi', '--query-gpu=name,memory.total', '--format=csv,noheader,nounits'],
        capture_output=True, text=True, timeout=5
    )

    if result.returncode == 0 and result.stdout.strip():
        lines = result.stdout.strip().split('\n')
        for idx, line in enumerate(lines):
            parts = line.split(',')
            if len(parts) >= 2:
                gpu_name = parts[0].strip()
                vram_mb = float(parts[1].strip())
                vram_gb = vram_mb / 1024

                print(f"GPU {idx}: {gpu_name}")
                print(f"  显存: {vram_mb:.0f}MB ({vram_gb:.2f}GB)")

                # 判断应该用什么Tile Size
                if vram_gb >= 16:
                    recommended = 2048
                    level = "⚡⚡⚡"
                elif vram_gb >= 8:
                    recommended = 1024
                    level = "⚡⚡"
                elif vram_gb >= 4:
                    recommended = 512
                    level = "⚡"
                else:
                    recommended = 400
                    level = ""

                print(f"  推荐Tile Size: {recommended} {level}")
                print()
    else:
        print("❌ nvidia-smi无法检测显存")
        print(f"   返回码: {result.returncode}")
        print(f"   输出: {result.stdout}")
        print(f"   错误: {result.stderr}")

except FileNotFoundError:
    print("❌ nvidia-smi未找到")
    print("   请确保NVIDIA驱动已正确安装")
except Exception as e:
    print(f"❌ 检测失败: {e}")

# 方法2：通过Vulkan检测（和程序实际使用的方法一致）
print("\n【Vulkan检测（程序实际使用）】")
try:
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

    from sr_vulkan import sr_vulkan as sr

    gpu_count = sr.get_gpu_count()
    print(f"检测到 {gpu_count} 个GPU")

    for i in range(gpu_count):
        gpu_info = sr.get_gpu_info(i)
        print(f"\nGPU {i}: {gpu_info}")

except ImportError as e:
    print(f"❌ 无法加载sr_vulkan: {e}")
except Exception as e:
    print(f"❌ Vulkan检测失败: {e}")

print("\n" + "="*70)
print("【分析】")
print("="*70)
print()
print("如果nvidia-smi显示的显存小于16GB：")
print("  1. 可能检测到了集成显卡（Intel/AMD）")
print("  2. 可能显存被其他程序占用")
print("  3. 需要手动指定Tile Size = 2048")
print()
print("如果nvidia-smi显示16GB但程序使用1024：")
print("  1. 可能是显存检测代码的问题")
print("  2. 可以手动修改代码强制使用2048")

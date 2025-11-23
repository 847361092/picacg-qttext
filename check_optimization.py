#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
优化诊断脚本 - 检查软件优化是否正确加载
"""

import sys
import os

# 添加src到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

print("="*70)
print("         PicACG-Qt 优化诊断工具")
print("="*70)
print()

# 1. 检查软件优化器模块是否存在
print("【1. 模块检查】")
try:
    from tools.software_optimizer import get_software_optimizer, SoftwareOptimizer
    print("✅ software_optimizer.py: 已找到")
except ImportError as e:
    print(f"❌ software_optimizer.py: 未找到 - {e}")
    print("\n请确保你已经pull最新代码：git pull")
    sys.exit(1)

try:
    from tools.io_optimizer import get_io_optimizer, IOOptimizer
    print("✅ io_optimizer.py: 已找到")
except ImportError as e:
    print(f"❌ io_optimizer.py: 未找到 - {e}")

# 2. 检查task_waifu2x是否集成优化器
print("\n【2. 集成检查】")
try:
    with open('src/task/task_waifu2x.py', 'r', encoding='utf-8') as f:
        content = f.read()

    if 'from tools.software_optimizer import get_software_optimizer' in content:
        print("✅ task_waifu2x.py: 已导入软件优化器")
    else:
        print("❌ task_waifu2x.py: 未导入软件优化器")

    if 'self.sw_optimizer = get_software_optimizer()' in content:
        print("✅ task_waifu2x.py: 已初始化优化器")
    else:
        print("❌ task_waifu2x.py: 未初始化优化器")

    if 'self.optimal_tile_size = self.sw_optimizer.get_optimal_tile_size()' in content:
        print("✅ task_waifu2x.py: 已获取optimal_tile_size")
    else:
        print("❌ task_waifu2x.py: 未获取optimal_tile_size")

    if 'tileSize = self.optimal_tile_size' in content:
        print("✅ task_waifu2x.py: 已使用optimal_tile_size")
    else:
        print("❌ task_waifu2x.py: 未使用optimal_tile_size")

except Exception as e:
    print(f"❌ 无法读取task_waifu2x.py: {e}")

# 3. 测试优化器功能
print("\n【3. 功能测试】")
try:
    optimizer = get_software_optimizer()
    print(f"✅ 优化器实例化成功")
    print(f"   系统: {optimizer.system}")

    # 测试Tile Size优化
    tile_size = optimizer.get_optimal_tile_size()
    print(f"✅ Tile Size检测: {tile_size}")

    if tile_size == 2048:
        print("   ⚡⚡⚡ 已识别16GB显存，Tile Size = 2048（最优）")
    elif tile_size == 1024:
        print("   ⚡⚡ 已识别8GB显存，Tile Size = 1024")
    elif tile_size == 512:
        print("   ⚡ 已识别4GB显存，Tile Size = 512")
    else:
        print(f"   ⚠️  使用默认值 Tile Size = {tile_size}")

except Exception as e:
    print(f"❌ 优化器测试失败: {e}")
    import traceback
    traceback.print_exc()

# 4. 检查Python缓存
print("\n【4. 缓存检查】")
import glob
pyc_files = glob.glob('src/**/__pycache__/**/*.pyc', recursive=True)
if pyc_files:
    print(f"⚠️  发现 {len(pyc_files)} 个.pyc缓存文件")
    print("   建议清除缓存以确保使用最新代码：")
    print("   方法1: 删除所有__pycache__目录")
    print("   方法2: 运行 python -B start.py (忽略缓存)")
else:
    print("✅ 无.pyc缓存文件")

# 5. 检查I/O优化器
print("\n【5. I/O优化器检查】")
try:
    io_opt = get_io_optimizer()
    if io_opt.has_turbojpeg:
        print("✅ TurboJPEG: 已启用")
        print("   ⚡⚡⚡ JPEG编解码将获得3-5倍性能提升")
    else:
        print("⚠️  TurboJPEG: 未安装")
        print("   建议安装获得I/O加速:")
        print("   1. pip install PyTurboJPEG")
        print("   2. 安装libjpeg-turbo库（参考INSTALL_TURBOJPEG_WINDOWS.md）")
except Exception as e:
    print(f"❌ I/O优化器初始化失败: {e}")

# 6. 给出建议
print("\n" + "="*70)
print("【诊断建议】")
print("="*70)

print("\n如果上面有❌标记，请按以下步骤操作：")
print()
print("1. 确保代码是最新的：")
print("   git pull origin claude/claude-md-mia2539vewe98kcw-01KyWuJbFRTui7f1sdw2vTM4")
print()
print("2. 清除Python缓存：")
print("   方法1: 手动删除所有 src/__pycache__ 目录")
print("   方法2: 运行以下命令")
if os.name == 'nt':  # Windows
    print('   for /d /r src %d in (__pycache__) do @if exist "%d" rd /s /q "%d"')
else:  # Linux/Mac
    print('   find src -type d -name "__pycache__" -exec rm -rf {} +')
print()
print("3. 重新启动软件：")
print("   cd src")
print("   python start.py")
print()
print("4. 查看启动日志，应该包含：")
print("   [SoftwareOptimizer] 进程优先级: ... ⚡")
print("   [SoftwareOptimizer] Tile Size: 2048 (检测到16.0GB显存) ⚡")
print("   [IOOptimizer] ✅ libjpeg-turbo加速: 已启用 ⚡⚡⚡")
print()
print("5. 运行超分时日志应显示：")
print("   [SR_VULKAN] start encode ... tileSize:2048")
print("   (而不是tileSize:400)")

print("\n" + "="*70)

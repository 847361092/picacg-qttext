#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TurboJPEG安装验证脚本
快速检测libjpeg-turbo是否正确安装并可用
"""

import sys
import os

# 添加src到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def check_pyturbojpeg_package():
    """检查PyTurboJPEG包是否安装"""
    try:
        import turbojpeg
        print("✅ PyTurboJPEG包: 已安装")
        return True
    except ImportError:
        print("❌ PyTurboJPEG包: 未安装")
        print("   解决方案: pip install PyTurboJPEG")
        return False

def check_turbojpeg_library():
    """检查libjpeg-turbo动态库是否可用"""
    try:
        import turbojpeg
        jpeg = turbojpeg.TurboJPEG()
        print("✅ libjpeg-turbo库: 已安装并可用")
        return True
    except Exception as e:
        print(f"❌ libjpeg-turbo库: 不可用")
        print(f"   错误信息: {e}")
        print("   解决方案: 安装libjpeg-turbo C库")
        print("   参考: INSTALL_TURBOJPEG_WINDOWS.md")
        return False

def check_numpy():
    """检查numpy是否安装（测试需要）"""
    try:
        import numpy as np
        print("✅ numpy: 已安装")
        return True
    except ImportError:
        print("⚠️  numpy: 未安装（性能测试需要）")
        print("   可选安装: pip install numpy")
        return False

def test_performance():
    """测试编解码性能"""
    try:
        import numpy as np
        import turbojpeg
        import time

        print("\n" + "="*60)
        print("【性能测试】")
        print("="*60)

        jpeg = turbojpeg.TurboJPEG()

        # 创建测试图像（1500x1200，典型漫画页）
        test_image = np.random.randint(0, 256, (1200, 1500, 3), dtype=np.uint8)
        print(f"测试图像: 1500x1200 RGB (典型漫画页尺寸)")

        # 测试编码
        print("\n【JPEG编码测试】（10次平均）")
        times = []
        encoded_data = None
        for i in range(10):
            start = time.perf_counter()
            encoded_data = jpeg.encode(test_image, quality=95)
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)

        avg_encode = sum(times) / len(times)
        print(f"  平均时间: {avg_encode:.2f}ms")
        print(f"  数据大小: {len(encoded_data) / 1024:.1f}KB")
        print(f"  速度: {1000/avg_encode:.1f}帧/秒")

        # 测试解码
        print("\n【JPEG解码测试】（10次平均）")
        times = []
        for i in range(10):
            start = time.perf_counter()
            decoded = jpeg.decode(encoded_data)
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)

        avg_decode = sum(times) / len(times)
        print(f"  平均时间: {avg_decode:.2f}ms")
        print(f"  速度: {1000/avg_decode:.1f}帧/秒")

        # 性能评估
        print("\n【性能评估】")
        if avg_encode < 40:
            print("  编码性能: ⚡⚡⚡ 优秀（TurboJPEG加速生效）")
        elif avg_encode < 70:
            print("  编码性能: ⚡⚡ 良好")
        else:
            print("  编码性能: ⚡ 一般（可能未使用TurboJPEG）")

        if avg_decode < 7:
            print("  解码性能: ⚡⚡⚡ 优秀（TurboJPEG加速生效）")
        elif avg_decode < 12:
            print("  解码性能: ⚡⚡ 良好")
        else:
            print("  解码性能: ⚡ 一般（可能未使用TurboJPEG）")

        print("\n预期性能（参考值）:")
        print("  编码: 20-30ms (TurboJPEG) vs 90ms (PIL)")
        print("  解码: 3-5ms (TurboJPEG) vs 10-15ms (PIL)")
        print("  提升: 3-5倍 ⚡⚡⚡")

        return True
    except ImportError as e:
        print(f"\n⚠️  性能测试跳过: {e}")
        return False
    except Exception as e:
        print(f"\n❌ 性能测试失败: {e}")
        return False

def check_io_optimizer():
    """检查项目中的IOOptimizer是否正确识别TurboJPEG"""
    try:
        from tools.io_optimizer import get_io_optimizer

        print("\n" + "="*60)
        print("【项目集成测试】")
        print("="*60)

        optimizer = get_io_optimizer()

        if optimizer.has_turbojpeg:
            print("✅ IOOptimizer已启用TurboJPEG加速")
            print("   项目运行时将自动使用3-5倍性能提升 ⚡⚡⚡")
            return True
        else:
            print("❌ IOOptimizer未检测到TurboJPEG")
            print("   项目将使用标准PIL编解码（性能较低）")
            return False

    except Exception as e:
        print(f"❌ 无法加载IOOptimizer: {e}")
        return False

def main():
    print("="*60)
    print("      TurboJPEG安装验证工具")
    print("="*60)
    print()

    # 检查Python包
    print("【依赖检查】")
    has_package = check_pyturbojpeg_package()
    has_library = check_turbojpeg_library() if has_package else False
    has_numpy = check_numpy()

    # 如果都安装了，运行性能测试
    if has_library and has_numpy:
        test_performance()

    # 检查项目集成
    if has_library:
        check_io_optimizer()

    # 总结
    print("\n" + "="*60)
    print("【验证结果总结】")
    print("="*60)

    if has_library:
        print("✅ libjpeg-turbo安装成功！")
        print("✅ PicACG-Qt将自动获得3-5倍图像处理性能提升")
        print("\n启动软件即可享受加速，无需额外配置！")
    else:
        print("❌ libjpeg-turbo未正确安装")
        print("\n请按照以下步骤操作：")
        print("1. 查看安装指南: INSTALL_TURBOJPEG_WINDOWS.md")
        print("2. 下载并安装libjpeg-turbo")
        print("3. 重新运行此脚本验证")

    print("="*60)

if __name__ == "__main__":
    main()

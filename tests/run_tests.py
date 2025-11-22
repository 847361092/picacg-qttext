#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试运行器 - 运行所有测试并生成覆盖率报告
"""
import sys
import os
import unittest

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src"))


def run_tests_with_coverage():
    """运行测试并生成覆盖率报告"""
    try:
        import coverage

        # 创建coverage对象
        cov = coverage.Coverage(
            source=['tools'],
            omit=[
                '*/test_*.py',
                '*/__pycache__/*',
                '*/images_rc.py',  # 排除大型资源文件
            ]
        )

        cov.start()

        # 运行测试
        success = run_tests()

        cov.stop()
        cov.save()

        # 生成报告
        print("\n" + "=" * 70)
        print("代码覆盖率报告")
        print("=" * 70)
        cov.report()

        # 生成HTML报告
        html_dir = os.path.join(os.path.dirname(__file__), "htmlcov")
        cov.html_report(directory=html_dir)
        print(f"\n✓ HTML报告已生成到: {html_dir}/index.html")

        # 获取总覆盖率
        total_coverage = cov.report(show_missing=False)

        return success, total_coverage

    except ImportError:
        print("警告: coverage模块未安装，跳过覆盖率分析")
        print("安装方法: pip install coverage")
        return run_tests(), None


def run_tests():
    """运行所有测试"""
    # 发现并运行测试
    loader = unittest.TestLoader()
    start_dir = os.path.dirname(__file__)
    suite = loader.discover(start_dir, pattern='test_*.py')

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


def main():
    """主函数"""
    print("=" * 70)
    print("PicACG-Qt 优化模块测试套件")
    print("=" * 70)
    print()

    # 运行测试
    success, coverage_pct = run_tests_with_coverage()

    # 输出总结
    print("\n" + "=" * 70)
    print("测试总结")
    print("=" * 70)

    if success:
        print("✅ 所有测试通过")
    else:
        print("❌ 部分测试失败")

    if coverage_pct is not None:
        if coverage_pct >= 95:
            print(f"✅ 代码覆盖率: {coverage_pct:.1f}% (目标: ≥95%)")
        elif coverage_pct >= 80:
            print(f"⚠️  代码覆盖率: {coverage_pct:.1f}% (目标: ≥95%)")
        else:
            print(f"❌ 代码覆盖率: {coverage_pct:.1f}% (目标: ≥95%)")

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()

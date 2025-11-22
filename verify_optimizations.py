#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
优化效果验证脚本
检查Phase 1-6优化是否正确部署
"""

import os
import sys

def check_file_modifications():
    """检查关键文件是否包含优化代码"""

    checks = {
        "Phase 4 - 启动优化": {
            "file": "src/start.py",
            "markers": [
                "lazy_load_waifu2x_models",
                "[Startup]",
                "QSplashScreen",
                "startup_begin = time.time()"
            ]
        },
        "Phase 5 - 封面优先加载": {
            "file": "src/component/list/comic_list_widget.py",
            "markers": [
                "_get_visible_indices",
                "_get_priority_indices",
                "_trigger_visible_loads",
                "self._pending_loads = set()"
            ]
        },
        "Phase 6 - 双重缓存": {
            "file": "src/component/widget/comic_item_widget.py",
            "markers": [
                "scaled_cache_key",
                "cover_scaled_",
                "waifu_scaled_",
                "# Level 1: Check scaled cache"
            ]
        }
    }

    print("="*70)
    print("优化部署验证报告")
    print("="*70)

    all_passed = True

    for phase, config in checks.items():
        print(f"\n检查 {phase}:")
        file_path = config["file"]

        if not os.path.exists(file_path):
            print(f"  ❌ 文件不存在: {file_path}")
            all_passed = False
            continue

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        phase_passed = True
        for marker in config["markers"]:
            if marker in content:
                print(f"  ✅ 找到标记: {marker}")
            else:
                print(f"  ❌ 缺少标记: {marker}")
                phase_passed = False
                all_passed = False

        if phase_passed:
            print(f"  ✅ {phase} 已正确部署")
        else:
            print(f"  ❌ {phase} 未完整部署")

    print("\n" + "="*70)
    if all_passed:
        print("✅ 所有优化已正确部署！")
        print("\n建议测试步骤：")
        print("1. 重启应用，观察启动时间（应该看到[Startup]日志）")
        print("2. 进入漫画列表，观察首屏封面加载速度")
        print("3. 快速滚动列表，观察流畅度")
        return 0
    else:
        print("❌ 部分优化未部署，请确认：")
        print("1. 是否已经 git pull 最新代码？")
        print("2. 当前分支是否正确？")
        print("\n运行以下命令检查：")
        print("  git log -3 --oneline")
        print("  git status")
        return 1

if __name__ == "__main__":
    sys.exit(check_file_modifications())

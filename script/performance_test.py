#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
性能基准测试工具
用于验证优化效果和生成性能报告
"""

import sys
import os
import time
import json
from datetime import datetime

# 添加src到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src"))


def test_cache_performance():
    """测试缓存性能"""
    print("=" * 60)
    print("测试1: 缓存性能测试")
    print("=" * 60)

    try:
        from tools.image_cache import get_image_cache
        from tools.pixmap_cache import get_pixmap_cache
        from tools.db_pool import get_connection_pool

        results = {
            'image_cache': {},
            'pixmap_cache': {},
            'db_pool': {}
        }

        # 测试图片缓存
        print("\n[1/3] 测试图片内存缓存...")
        img_cache = get_image_cache()
        stats = img_cache.get_stats()
        results['image_cache'] = {
            'max_size_mb': stats['max_size_mb'],
            'current_size_mb': round(stats['size_mb'], 2),
            'entries': stats['entries'],
            'hits': stats['hits'],
            'misses': stats['misses'],
            'hit_rate': round(stats['hit_rate'] * 100, 1),
            'usage_percent': round(stats['usage_percent'], 1)
        }

        print(f"  ✓ 缓存大小: {stats['max_size_mb']}MB")
        print(f"  ✓ 当前使用: {stats['size_mb']:.1f}MB ({stats['usage_percent']:.1f}%)")
        print(f"  ✓ 缓存条目: {stats['entries']}")
        print(f"  ✓ 命中率: {stats['hit_rate']*100:.1f}%")

        # 测试QPixmap缓存
        print("\n[2/3] 测试QPixmap缓存...")
        pixmap_cache = get_pixmap_cache()
        stats = pixmap_cache.get_stats()
        results['pixmap_cache'] = {
            'max_entries': stats['max_entries'],
            'current_entries': stats['entries'],
            'hits': stats['hits'],
            'misses': stats['misses'],
            'hit_rate': round(stats['hit_rate'] * 100, 1) if stats['hit_rate'] else 0,
            'evictions': stats['evictions']
        }

        print(f"  ✓ 最大条目: {stats['max_entries']}")
        print(f"  ✓ 当前条目: {stats['entries']}")
        print(f"  ✓ 命中率: {stats['hit_rate']*100:.1f}%")
        print(f"  ✓ 驱逐次数: {stats['evictions']}")

        # 测试数据库连接池
        print("\n[3/3] 测试数据库连接池...")
        try:
            db_pool = get_connection_pool()
            stats = db_pool.get_stats()
            results['db_pool'] = {
                'pool_size': stats['pool_size'],
                'active_connections': stats.get('active_connections', 'N/A'),
                'total_queries': stats.get('total_queries', 'N/A')
            }
            print(f"  ✓ 连接池大小: {stats['pool_size']}")
        except Exception as e:
            print(f"  ⊙ 数据库连接池未使用: {e}")
            results['db_pool'] = {'status': 'not_in_use'}

        return results

    except Exception as e:
        print(f"  ✗ 错误: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_memory_usage():
    """测试内存使用"""
    print("\n" + "=" * 60)
    print("测试2: 内存使用情况")
    print("=" * 60)

    try:
        import psutil
        import gc

        # 强制垃圾回收
        gc.collect()

        process = psutil.Process()
        mem_info = process.memory_info()

        results = {
            'rss_mb': round(mem_info.rss / 1024 / 1024, 2),
            'vms_mb': round(mem_info.vms / 1024 / 1024, 2),
            'percent': round(process.memory_percent(), 2)
        }

        print(f"  ✓ RSS内存: {results['rss_mb']} MB")
        print(f"  ✓ VMS内存: {results['vms_mb']} MB")
        print(f"  ✓ 内存占用率: {results['percent']}%")

        return results

    except ImportError:
        print("  ⊙ psutil未安装，跳过内存测试")
        print("  提示: pip install psutil")
        return {'status': 'psutil_not_installed'}
    except Exception as e:
        print(f"  ✗ 错误: {e}")
        return None


def test_database_performance():
    """测试数据库性能"""
    print("\n" + "=" * 60)
    print("测试3: 数据库性能测试")
    print("=" * 60)

    try:
        import sqlite3

        # 检查数据库索引
        db_path = "../src/db/book.db"
        if not os.path.exists(db_path):
            db_path = "db/book.db"

        if not os.path.exists(db_path):
            print("  ⊙ 数据库文件不存在，跳过测试")
            return {'status': 'db_not_found'}

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 获取索引数量
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indexes = [row[0] for row in cursor.fetchall()]

        # 获取书籍数量
        cursor.execute("SELECT COUNT(*) FROM book")
        book_count = cursor.fetchone()[0]

        # 简单查询性能测试
        test_queries = [
            ("按分类查询", "SELECT COUNT(*) FROM book WHERE categories LIKE '%同人%'"),
            ("按作者查询", "SELECT COUNT(*) FROM book WHERE author LIKE '%test%'"),
            ("按更新时间排序", "SELECT id FROM book ORDER BY updated_at DESC LIMIT 20"),
        ]

        query_times = []
        for name, sql in test_queries:
            start = time.time()
            cursor.execute(sql)
            cursor.fetchall()
            elapsed = (time.time() - start) * 1000
            query_times.append((name, elapsed))
            print(f"  ✓ {name}: {elapsed:.2f}ms")

        conn.close()

        results = {
            'indexes_count': len(indexes),
            'book_count': book_count,
            'avg_query_time_ms': round(sum(t for _, t in query_times) / len(query_times), 2),
            'queries': {name: round(t, 2) for name, t in query_times}
        }

        print(f"\n  ✓ 索引数量: {len(indexes)}")
        print(f"  ✓ 书籍数量: {book_count:,}")
        print(f"  ✓ 平均查询时间: {results['avg_query_time_ms']:.2f}ms")

        return results

    except Exception as e:
        print(f"  ✗ 错误: {e}")
        import traceback
        traceback.print_exc()
        return None


def generate_report(results):
    """生成性能报告"""
    print("\n" + "=" * 60)
    print("性能测试报告")
    print("=" * 60)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    report = {
        'timestamp': timestamp,
        'cache_performance': results.get('cache'),
        'memory_usage': results.get('memory'),
        'database_performance': results.get('database')
    }

    # 评分系统
    score = 100
    recommendations = []

    # 缓存评分
    if results.get('cache'):
        cache = results['cache']

        # 图片缓存命中率
        if 'image_cache' in cache:
            hit_rate = cache['image_cache'].get('hit_rate', 0)
            if hit_rate < 50:
                score -= 10
                recommendations.append("图片缓存命中率偏低，建议增加缓存大小")
            elif hit_rate >= 80:
                print("\n  ✓ 图片缓存表现优秀（命中率 ≥80%）")

        # QPixmap缓存命中率
        if 'pixmap_cache' in cache:
            hit_rate = cache['pixmap_cache'].get('hit_rate', 0)
            if hit_rate < 60:
                score -= 10
                recommendations.append("QPixmap缓存命中率偏低，可能需要更多使用时间")
            elif hit_rate >= 80:
                print("  ✓ QPixmap缓存表现优秀（命中率 ≥80%）")

    # 数据库评分
    if results.get('database'):
        db = results['database']
        if db.get('indexes_count', 0) < 5:
            score -= 20
            recommendations.append("数据库索引不足，建议运行 optimize_database.py")
        else:
            print("  ✓ 数据库索引充足")

        avg_time = db.get('avg_query_time_ms', 0)
        if avg_time > 100:
            score -= 10
            recommendations.append("数据库查询较慢，检查是否需要更多索引")
        elif avg_time < 20:
            print("  ✓ 数据库查询速度优秀（<20ms）")

    print(f"\n{'='*60}")
    print(f"综合评分: {score}/100")
    print(f"{'='*60}")

    if score >= 90:
        print("\n✅ 优秀！优化效果显著，性能表现出色！")
    elif score >= 70:
        print("\n✓ 良好！优化已生效，仍有提升空间。")
    else:
        print("\n⚠️ 需要改进！请查看以下建议。")

    if recommendations:
        print("\n建议:")
        for i, rec in enumerate(recommendations, 1):
            print(f"  {i}. {rec}")

    report['score'] = score
    report['recommendations'] = recommendations

    # 保存报告
    report_file = f"performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\n📄 详细报告已保存到: {report_file}")

    return report


def main():
    """主函数"""
    print("\n" + "🚀" * 30)
    print("PicACG-Qt 性能基准测试工具")
    print("Phase 1 + Phase 2 + Phase 3 优化验证")
    print("🚀" * 30 + "\n")

    results = {}

    # 测试1: 缓存性能
    cache_results = test_cache_performance()
    if cache_results:
        results['cache'] = cache_results

    # 测试2: 内存使用
    memory_results = test_memory_usage()
    if memory_results:
        results['memory'] = memory_results

    # 测试3: 数据库性能
    db_results = test_database_performance()
    if db_results:
        results['database'] = db_results

    # 生成报告
    if results:
        generate_report(results)
    else:
        print("\n⚠️ 无法收集足够的性能数据")
        print("请确保应用已运行一段时间后再测试")

    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)
    print("\n提示:")
    print("  1. 首次运行时缓存命中率会较低，这是正常的")
    print("  2. 建议使用应用浏览一段时间后再次测试")
    print("  3. 缓存命中率 ≥80% 说明优化效果显著")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n测试已取消")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

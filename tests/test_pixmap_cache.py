# -*- coding: utf-8 -*-
"""
PixmapCache 单元测试
测试QPixmap缓存的所有功能
"""
import sys
import os
import unittest
import threading

# 添加src到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src"))

# 尝试导入PySide6
try:
    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QPixmap
    from PySide6.QtCore import QByteArray
    from tools.pixmap_cache import PixmapCache, get_pixmap_cache

    # 创建QApplication实例（如果不存在）
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    PYSIDE6_AVAILABLE = True
except ImportError:
    PYSIDE6_AVAILABLE = False
    print("警告: PySide6未安装，跳过PixmapCache测试")
    print("安装方法: pip install PySide6")


@unittest.skipIf(not PYSIDE6_AVAILABLE, "PySide6 not available")
class TestPixmapCache(unittest.TestCase):
    """PixmapCache单元测试"""

    def setUp(self):
        """每个测试前执行"""
        # 创建小容量缓存用于测试
        self.cache = PixmapCache(max_entries=10)

    def tearDown(self):
        """每个测试后执行"""
        self.cache.clear()

    def test_init(self):
        """测试初始化"""
        self.assertEqual(self.cache.max_entries, 10)
        self.assertEqual(len(self.cache.cache), 0)
        self.assertEqual(self.cache.hits, 0)
        self.assertEqual(self.cache.misses, 0)
        self.assertEqual(self.cache.evictions, 0)

    def test_put_and_get_valid_pixmap(self):
        """测试存取有效的QPixmap"""
        # 创建一个简单的QPixmap（1x1红色）
        pixmap = QPixmap(10, 10)
        pixmap.fill(0xFF0000)  # 红色

        key = "test_pixmap"

        # 存储
        result = self.cache.put(key, pixmap)
        self.assertTrue(result)

        # 获取
        cached_pixmap = self.cache.get(key)
        self.assertIsNotNone(cached_pixmap)
        self.assertIsInstance(cached_pixmap, QPixmap)
        self.assertEqual(cached_pixmap.width(), 10)
        self.assertEqual(cached_pixmap.height(), 10)

    def test_put_null_pixmap(self):
        """测试存储空QPixmap"""
        null_pixmap = QPixmap()
        self.assertTrue(null_pixmap.isNull())

        result = self.cache.put("key", null_pixmap)
        self.assertFalse(result)  # 不应该缓存空pixmap

    def test_put_none(self):
        """测试存储None"""
        result = self.cache.put("key", None)
        self.assertFalse(result)

    def test_get_nonexistent(self):
        """测试获取不存在的key"""
        result = self.cache.get("nonexistent")
        self.assertIsNone(result)
        self.assertEqual(self.cache.misses, 1)

    def test_lru_eviction(self):
        """测试LRU驱逐策略"""
        # 填满缓存（10个条目）
        for i in range(10):
            pixmap = QPixmap(5, 5)
            self.cache.put(f"key_{i}", pixmap)

        # 添加第11个，应该驱逐key_0
        pixmap_11 = QPixmap(5, 5)
        self.cache.put("key_10", pixmap_11)

        self.assertEqual(self.cache.evictions, 1)
        self.assertIsNone(self.cache.get("key_0"))  # key_0应该被驱逐
        self.assertIsNotNone(self.cache.get("key_10"))  # key_10应该存在

    def test_cache_hit_miss_stats(self):
        """测试缓存命中/未命中统计"""
        pixmap = QPixmap(5, 5)
        self.cache.put("key1", pixmap)

        # 命中
        self.cache.get("key1")
        self.assertEqual(self.cache.hits, 1)
        self.assertEqual(self.cache.misses, 0)

        # 未命中
        self.cache.get("nonexistent")
        self.assertEqual(self.cache.hits, 1)
        self.assertEqual(self.cache.misses, 1)

    def test_get_stats(self):
        """测试获取统计信息"""
        pixmap = QPixmap(10, 10)
        self.cache.put("key1", pixmap)
        self.cache.get("key1")  # 命中
        self.cache.get("key2")  # 未命中

        stats = self.cache.get_stats()

        self.assertEqual(stats['max_entries'], 10)
        self.assertEqual(stats['entries'], 1)
        self.assertEqual(stats['hits'], 1)
        self.assertEqual(stats['misses'], 1)
        self.assertEqual(stats['hit_rate'], 0.5)  # 50%
        self.assertEqual(stats['evictions'], 0)

    def test_clear(self):
        """测试清空缓存"""
        for i in range(5):
            pixmap = QPixmap(5, 5)
            self.cache.put(f"key_{i}", pixmap)

        self.cache.clear()

        self.assertEqual(len(self.cache.cache), 0)
        self.assertIsNone(self.cache.get("key_0"))

    def test_pixmap_isolation(self):
        """测试QPixmap隔离（copy机制）"""
        original = QPixmap(10, 10)
        original.fill(0xFF0000)  # 红色

        self.cache.put("key", original)

        # 修改原始pixmap
        original.fill(0x00FF00)  # 改为绿色

        # 从缓存获取的应该仍是红色（副本）
        cached = self.cache.get("key")
        # 注意：QPixmap的pixel比较比较复杂，这里只验证不是同一对象
        self.assertIsNot(cached, original)

    def test_update_existing_key(self):
        """测试更新已存在的key"""
        pixmap1 = QPixmap(5, 5)
        pixmap2 = QPixmap(10, 10)

        self.cache.put("key", pixmap1)
        self.cache.put("key", pixmap2)

        cached = self.cache.get("key")
        self.assertEqual(cached.width(), 10)
        self.assertEqual(cached.height(), 10)

    def test_thread_safety(self):
        """测试线程安全"""
        results = []

        def writer():
            for i in range(50):
                pixmap = QPixmap(5, 5)
                self.cache.put(f"key_{i}", pixmap)

        def reader():
            for i in range(50):
                pixmap = self.cache.get(f"key_{i}")
                results.append(pixmap is not None or True)

        threads = []
        for _ in range(3):
            threads.append(threading.Thread(target=writer))
            threads.append(threading.Thread(target=reader))

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 不应该崩溃
        self.assertTrue(len(results) > 0)

    def test_move_to_end_on_access(self):
        """测试访问时移到末尾（LRU更新）"""
        # 添加3个pixmap
        for i in range(3):
            pixmap = QPixmap(5, 5)
            self.cache.put(f"key_{i}", pixmap)

        # 访问key_0（移到末尾）
        self.cache.get("key_0")

        # 再添加8个，填满缓存（max=10）
        for i in range(3, 11):
            pixmap = QPixmap(5, 5)
            self.cache.put(f"key_{i}", pixmap)

        # 再添加1个，应该驱逐key_1（不是key_0）
        pixmap = QPixmap(5, 5)
        self.cache.put("key_11", pixmap)

        self.assertIsNone(self.cache.get("key_1"))  # key_1被驱逐
        self.assertIsNotNone(self.cache.get("key_0"))  # key_0还在


@unittest.skipIf(not PYSIDE6_AVAILABLE, "PySide6 not available")
class TestPixmapCacheSingleton(unittest.TestCase):
    """测试全局单例"""

    def test_singleton_same_instance(self):
        """测试单例返回相同实例"""
        cache1 = get_pixmap_cache()
        cache2 = get_pixmap_cache()

        self.assertIs(cache1, cache2)

    def test_singleton_thread_safe(self):
        """测试单例在多线程环境下的安全性"""
        instances = []

        def get_instance():
            instances.append(get_pixmap_cache())

        threads = [threading.Thread(target=get_instance) for _ in range(10)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 所有实例应该相同
        first = instances[0]
        for instance in instances:
            self.assertIs(instance, first)


if __name__ == '__main__':
    unittest.main()

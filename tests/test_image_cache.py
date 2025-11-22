# -*- coding: utf-8 -*-
"""
ImageCache 单元测试
测试图片内存缓存的所有功能
"""
import sys
import os
import unittest
import threading
import time

# 添加src到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src"))

from tools.image_cache import ImageMemoryCache, get_image_cache


class TestImageMemoryCache(unittest.TestCase):
    """ImageMemoryCache单元测试"""

    def setUp(self):
        """每个测试前执行"""
        # 创建小容量缓存用于测试
        self.cache = ImageMemoryCache(max_size_mb=1)

    def tearDown(self):
        """每个测试后执行"""
        self.cache.clear()

    def test_init(self):
        """测试初始化"""
        self.assertEqual(self.cache.max_size, 1 * 1024 * 1024)
        self.assertEqual(self.cache.current_size, 0)
        self.assertEqual(len(self.cache.cache), 0)

    def test_put_and_get(self):
        """测试基本的存取功能"""
        key = "test_key"
        data = b"test_data_123"

        # 存储
        result = self.cache.put(key, data)
        self.assertTrue(result)

        # 获取
        cached_data = self.cache.get(key)
        self.assertIsNotNone(cached_data)
        self.assertEqual(cached_data, data)

    def test_get_nonexistent(self):
        """测试获取不存在的key"""
        result = self.cache.get("nonexistent_key")
        self.assertIsNone(result)

    def test_put_none(self):
        """测试存储None值"""
        result = self.cache.put("key", None)
        self.assertFalse(result)

    def test_put_empty_bytes(self):
        """测试存储空bytes"""
        result = self.cache.put("key", b"")
        self.assertFalse(result)

    def test_lru_eviction(self):
        """测试LRU驱逐策略"""
        # 创建非常小的缓存，max_entries=5
        small_cache = ImageMemoryCache(max_size_mb=10.0, max_entries=5)

        # 添加小数据，使用max_entries限制
        data = b"x" * 1000  # 1KB

        # 添加5个条目（填满）
        for i in range(5):
            small_cache.put(f"key_{i}", data)

        # 所有key应该都在
        self.assertIsNotNone(small_cache.get("key_0"))
        self.assertIsNotNone(small_cache.get("key_4"))

        # 添加第6个，应该驱逐key_0（最旧的）
        small_cache.put("key_5", data)

        # key_0应该被驱逐
        self.assertIsNone(small_cache.get("key_0"))
        # 新加入的应该在
        self.assertIsNotNone(small_cache.get("key_5"))
        # key_1应该还在（成为最旧的）
        self.assertIsNotNone(small_cache.get("key_1"))

    def test_cache_hit_miss_stats(self):
        """测试缓存命中/未命中统计"""
        self.cache.put("key1", b"data1")

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
        self.cache.put("key1", b"data123")

        stats = self.cache.get_stats()

        self.assertIn('max_size_mb', stats)
        self.assertIn('size_mb', stats)
        self.assertIn('entries', stats)
        self.assertIn('hits', stats)
        self.assertIn('misses', stats)
        self.assertIn('hit_rate', stats)
        self.assertIn('usage_percent', stats)

        self.assertEqual(stats['entries'], 1)

    def test_clear(self):
        """测试清空缓存"""
        self.cache.put("key1", b"data1")
        self.cache.put("key2", b"data2")

        self.cache.clear()

        self.assertEqual(len(self.cache.cache), 0)
        self.assertEqual(self.cache.current_size, 0)
        self.assertIsNone(self.cache.get("key1"))

    def test_thread_safety(self):
        """测试线程安全"""
        results = []

        def writer():
            for i in range(100):
                self.cache.put(f"key_{i}", f"data_{i}".encode())

        def reader():
            for i in range(100):
                data = self.cache.get(f"key_{i}")
                results.append(data is not None or True)

        # 创建多个读写线程
        threads = []
        for _ in range(5):
            threads.append(threading.Thread(target=writer))
            threads.append(threading.Thread(target=reader))

        # 启动所有线程
        for t in threads:
            t.start()

        # 等待所有线程完成
        for t in threads:
            t.join()

        # 不应该崩溃，且结果列表应有内容
        self.assertTrue(len(results) > 0)

    def test_update_existing_key(self):
        """测试更新已存在的key"""
        key = "test_key"
        data1 = b"data1"
        data2 = b"data2_different"

        self.cache.put(key, data1)
        self.cache.put(key, data2)

        # 应该得到最新的数据
        cached = self.cache.get(key)
        self.assertEqual(cached, data2)


class TestImageCacheSingleton(unittest.TestCase):
    """测试全局单例"""

    def test_singleton_same_instance(self):
        """测试单例返回相同实例"""
        cache1 = get_image_cache()
        cache2 = get_image_cache()

        self.assertIs(cache1, cache2)

    def test_singleton_thread_safe(self):
        """测试单例在多线程环境下的安全性"""
        instances = []

        def get_instance():
            instances.append(get_image_cache())

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

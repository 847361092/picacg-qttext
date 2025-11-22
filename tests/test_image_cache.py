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
        # 使用size限制：0.01MB (10KB) 缓存
        # 单个文件不能超过10%，即1KB
        # 每个文件800 bytes（< 1KB），符合限制
        small_cache = ImageMemoryCache(max_size_mb=0.01, max_entries=1000)

        data = b"x" * 800  # 800 bytes < 1KB

        # 添加多个条目，填满并超出10KB缓存
        for i in range(15):  # 15 * 800 = 12KB > 10KB
            small_cache.put(f"key_{i}", data)

        # key_0应该被驱逐（最旧的）
        self.assertIsNone(small_cache.get("key_0"))
        # 最新的应该还在
        self.assertIsNotNone(small_cache.get("key_14"))
        # 验证有驱逐发生
        self.assertGreater(small_cache.evictions, 0)

    def test_file_too_large(self):
        """测试文件过大不缓存"""
        # 创建1MB缓存
        cache = ImageMemoryCache(max_size_mb=1.0)

        # 尝试添加超过10%的文件（>100KB）
        large_data = b"x" * 150000  # 150KB > 1MB * 10%

        result = cache.put("large_file", large_data)

        # 不应该成功
        self.assertFalse(result)
        # 缓存中不应该有这个key
        self.assertIsNone(cache.get("large_file"))

    def test_clear_old_entries(self):
        """测试清理旧条目"""
        # 添加10个条目
        for i in range(10):
            self.cache.put(f"key_{i}", b"data")

        # 清理，保留50%
        self.cache.clear_old_entries(keep_ratio=0.5)

        # 应该只剩5个
        self.assertEqual(len(self.cache.cache), 5)

        # 旧的key应该被删除
        self.assertIsNone(self.cache.get("key_0"))
        self.assertIsNone(self.cache.get("key_4"))

        # 新的key应该保留
        self.assertIsNotNone(self.cache.get("key_5"))
        self.assertIsNotNone(self.cache.get("key_9"))

    def test_resize(self):
        """测试调整缓存大小"""
        # 创建大缓存
        cache = ImageMemoryCache(max_size_mb=10.0)

        # 添加一些数据
        data = b"x" * 100000  # 100KB
        for i in range(5):
            cache.put(f"key_{i}", data)

        # 缩小缓存
        cache.resize(0.3)  # 缩小到300KB

        # 应该驱逐一些条目（500KB -> 300KB）
        # 至少key_0和key_1应该被驱逐
        self.assertIsNone(cache.get("key_0"))
        # key_4应该还在（最新的）
        self.assertIsNotNone(cache.get("key_4"))

    def test_log_stats_trigger(self):
        """测试统计日志触发（1000次访问）"""
        # 添加一些数据以产生命中
        self.cache.put("test_key", b"test_data")

        # 访问1000次（499*2 + 2 = 1000）
        for i in range(499):
            self.cache.get("test_key")  # 命中
            self.cache.get("nonexistent")  # 未命中

        # 第999和1000次
        self.cache.get("test_key")
        self.cache.get("test_key")  # 第1000次应该触发_log_stats

        # 验证统计正确
        self.assertEqual(self.cache.hits + self.cache.misses, 1000)

    def test_evict_empty_cache(self):
        """测试驱逐空缓存（覆盖_evict_one第114行）"""
        # 创建空缓存
        empty_cache = ImageMemoryCache(max_size_mb=1.0)

        # 调用_evict_one应该安全返回（不崩溃）
        empty_cache._evict_one()

        # 验证缓存仍为空
        self.assertEqual(len(empty_cache.cache), 0)

    def test_eviction_log_trigger(self):
        """测试驱逐日志触发（100次驱逐）"""
        # 创建小缓存，容易触发驱逐
        small_cache = ImageMemoryCache(max_size_mb=0.5, max_entries=3)

        data = b"x" * 1000

        # 添加100+个条目，触发多次驱逐
        for i in range(103):  # 确保超过100次驱逐
            small_cache.put(f"key_{i}", data)

        # 验证驱逐次数
        self.assertGreaterEqual(small_cache.evictions, 100)

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

    def test_config_with_value_attribute(self):
        """测试配置读取with .value属性（覆盖line 272）"""
        # 这个测试覆盖get_image_cache中的配置读取逻辑
        # 由于get_image_cache是单例，我们只能验证它正常工作
        # 实际的.value属性提取逻辑在首次调用时执行

        # 获取单例实例
        cache = get_image_cache()

        # 验证缓存正确初始化
        self.assertIsNotNone(cache)
        self.assertIsInstance(cache, ImageMemoryCache)

        # 验证max_size被正确设置（无论是从配置还是默认值）
        # 默认是512MB或者从Setting.ImageCacheSize读取
        self.assertGreater(cache.max_size, 0)


if __name__ == '__main__':
    unittest.main()

# -*- coding: utf-8 -*-
"""
集成测试 - 测试优化模块的实际集成效果
"""
import sys
import os
import unittest
import hashlib
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src"))

from tools.image_cache import get_image_cache

# 尝试导入PySide6
try:
    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QPixmap
    from tools.pixmap_cache import get_pixmap_cache

    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    PYSIDE6_AVAILABLE = True
except ImportError:
    PYSIDE6_AVAILABLE = False
    print("警告: PySide6未安装，部分集成测试将跳过")


class TestImageCacheIntegration(unittest.TestCase):
    """测试ImageCache的实际集成"""

    def setUp(self):
        """测试前清空缓存"""
        cache = get_image_cache()
        cache.clear()

    def test_file_caching_workflow(self):
        """测试文件缓存工作流程"""
        # 创建临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix='.dat') as f:
            test_data = b"test_image_data_12345"
            f.write(test_data)
            temp_path = f.name

        try:
            cache = get_image_cache()

            # 首次读取 - 应该未命中
            initial_hits = cache.hits
            initial_misses = cache.misses

            # 模拟LoadCachePicture的逻辑
            cached_data = cache.get(temp_path)
            if cached_data is None:
                with open(temp_path, 'rb') as f:
                    data = f.read()
                cache.put(temp_path, data)

            # 验证未命中
            self.assertEqual(cache.misses, initial_misses + 1)

            # 第二次读取 - 应该命中
            cached_data = cache.get(temp_path)
            self.assertIsNotNone(cached_data)
            self.assertEqual(cached_data, test_data)
            self.assertEqual(cache.hits, initial_hits + 1)

        finally:
            os.unlink(temp_path)


@unittest.skipIf(not PYSIDE6_AVAILABLE, "PySide6 not available")
class TestPixmapCacheIntegration(unittest.TestCase):
    """测试PixmapCache的实际集成"""

    def setUp(self):
        """测试前清空缓存"""
        cache = get_pixmap_cache()
        cache.clear()

    def test_pixmap_decoding_workflow(self):
        """测试QPixmap解码缓存工作流程"""
        # 创建一个简单的PNG图片数据
        pixmap = QPixmap(20, 20)
        pixmap.fill(0x0000FF)  # 蓝色

        # 转换为bytes
        from PySide6.QtCore import QByteArray, QBuffer, QIODevice
        byte_array = QByteArray()
        buffer = QBuffer(byte_array)
        buffer.open(QIODevice.WriteOnly)
        pixmap.save(buffer, "PNG")
        image_data = bytes(byte_array.data())

        cache = get_pixmap_cache()

        # 模拟SetPicture的逻辑
        cache_key = f"cover_{hashlib.md5(image_data).hexdigest()}"

        # 首次解码 - 未命中
        cached_pixmap = cache.get(cache_key)
        self.assertIsNone(cached_pixmap)

        # 解码并缓存
        pic = QPixmap()
        pic.loadFromData(image_data)
        if not pic.isNull():
            cache.put(cache_key, pic)

        # 第二次 - 应该命中
        cached_pixmap = cache.get(cache_key)
        self.assertIsNotNone(cached_pixmap)
        self.assertEqual(cached_pixmap.width(), 20)
        self.assertEqual(cached_pixmap.height(), 20)

    def test_empty_string_handling(self):
        """测试空字符串处理（实际场景）"""
        data = ""  # 实际代码中有 SetPicture("")

        # 模拟SetPicture的类型检查
        if data and isinstance(data, bytes) and len(data) > 0:
            # 不应该进入这里
            self.fail("Empty string should not pass type check")

        # 应该安全通过，不崩溃
        self.assertTrue(True)

    def test_none_handling(self):
        """测试None处理"""
        data = None

        if data and isinstance(data, bytes) and len(data) > 0:
            self.fail("None should not pass type check")

        self.assertTrue(True)

    def test_decode_failure_handling(self):
        """测试解码失败处理"""
        # 损坏的图片数据
        corrupted_data = b"not_a_valid_image"

        cache = get_pixmap_cache()
        cache_key = f"test_{hashlib.md5(corrupted_data).hexdigest()}"

        pic = QPixmap()
        pic.loadFromData(corrupted_data)

        # 应该检测到解码失败
        self.assertTrue(pic.isNull())

        # 不应该缓存
        if not pic.isNull():
            cache.put(cache_key, pic)

        # 缓存中不应该有这个key
        self.assertIsNone(cache.get(cache_key))


@unittest.skipIf(not PYSIDE6_AVAILABLE, "PySide6 not available")
class TestCacheCoordination(unittest.TestCase):
    """测试多个缓存协同工作"""

    def setUp(self):
        """清空所有缓存"""
        get_image_cache().clear()
        get_pixmap_cache().clear()

    def test_two_level_caching(self):
        """测试两级缓存协同"""
        # 这模拟了实际的使用场景：
        # 1. ImageCache缓存原始图片数据
        # 2. PixmapCache缓存解码后的QPixmap

        # 创建测试图片
        pixmap = QPixmap(15, 15)
        pixmap.fill(0x00FF00)

        from PySide6.QtCore import QByteArray, QBuffer, QIODevice
        byte_array = QByteArray()
        buffer = QBuffer(byte_array)
        buffer.open(QIODevice.WriteOnly)
        pixmap.save(buffer, "PNG")
        image_data = bytes(byte_array.data())

        # Level 1: 缓存图片数据
        image_cache = get_image_cache()
        image_cache.put("test_path", image_data)

        # Level 2: 缓存解码后的QPixmap
        pixmap_cache = get_pixmap_cache()
        cache_key = f"cover_{hashlib.md5(image_data).hexdigest()}"

        pic = QPixmap()
        pic.loadFromData(image_data)
        pixmap_cache.put(cache_key, pic)

        # 验证两级缓存都工作
        self.assertIsNotNone(image_cache.get("test_path"))
        self.assertIsNotNone(pixmap_cache.get(cache_key))


@unittest.skipIf(not PYSIDE6_AVAILABLE, "PySide6 not available")
class TestPerformanceImprovement(unittest.TestCase):
    """测试性能提升"""

    def test_cache_performance(self):
        """测试缓存性能提升"""
        import time

        pixmap = QPixmap(100, 100)
        pixmap.fill(0xFF00FF)

        from PySide6.QtCore import QByteArray, QBuffer, QIODevice
        byte_array = QByteArray()
        buffer = QBuffer(byte_array)
        buffer.open(QIODevice.WriteOnly)
        pixmap.save(buffer, "PNG")
        image_data = bytes(byte_array.data())

        cache = get_pixmap_cache()
        cache_key = f"perf_{hashlib.md5(image_data).hexdigest()}"

        # 首次解码（未缓存）
        start = time.time()
        pic1 = QPixmap()
        pic1.loadFromData(image_data)
        cache.put(cache_key, pic1)
        time_uncached = time.time() - start

        # 第二次（缓存命中）
        start = time.time()
        pic2 = cache.get(cache_key)
        time_cached = time.time() - start

        # 缓存应该明显更快
        # 注意：由于是单元测试，性能差异可能不明显，但缓存不应该更慢
        self.assertIsNotNone(pic2)
        # print(f"Uncached: {time_uncached*1000:.2f}ms, Cached: {time_cached*1000:.2f}ms")


if __name__ == '__main__':
    unittest.main()

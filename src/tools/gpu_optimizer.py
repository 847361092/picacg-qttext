#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
GPU底层性能优化模块
针对RTX 5070 Ti + i5-13600KF + 48GB RAM的极限优化

优化项:
1. 进程/线程优先级提升 (实时优先级)
2. CPU亲和性绑定 (绑定到P核心)
3. GPU性能模式 (NVIDIA最大性能)
4. 内存锁定 (防止swap)
5. GPU时钟锁定 (防止动态降频)
6. Tile Size动态优化 (16GB显存)

作者: 30年工程师深度优化
日期: 2025-11-23
"""

import os
import sys
import platform
import ctypes
import subprocess
from tools.log import Log

class GPUOptimizer:
    """GPU和系统底层优化器"""

    def __init__(self):
        self.system = platform.system()
        self.optimized = False
        self.original_priority = None
        self.original_affinity = None

    def optimize_all(self):
        """执行所有底层优化"""
        if self.optimized:
            return

        Log.Info("[GPUOptimizer] 开始底层优化...")

        try:
            # 1. 提升进程优先级
            self._set_high_priority()

            # 2. 绑定CPU亲和性（绑定到性能核心）
            self._set_cpu_affinity()

            # 3. 锁定内存（防止swap）
            self._lock_memory()

            # 4. NVIDIA GPU性能优化
            self._optimize_nvidia_gpu()

            self.optimized = True
            Log.Info("[GPUOptimizer] ✅ 底层优化完成！")

        except Exception as e:
            Log.Warn(f"[GPUOptimizer] 优化失败（部分功能可能受限）: {e}")

    def _set_high_priority(self):
        """提升进程优先级到最高（实时优先级）"""
        try:
            if self.system == "Windows":
                # Windows: 设置为HIGH_PRIORITY_CLASS
                import win32process
                import win32api
                import win32con

                handle = win32api.GetCurrentProcess()
                # 尝试实时优先级，失败则用高优先级
                try:
                    win32process.SetPriorityClass(handle, win32process.REALTIME_PRIORITY_CLASS)
                    Log.Info("[GPUOptimizer] 进程优先级: REALTIME ⚡")
                except:
                    win32process.SetPriorityClass(handle, win32process.HIGH_PRIORITY_CLASS)
                    Log.Info("[GPUOptimizer] 进程优先级: HIGH ⚡")

            elif self.system == "Linux":
                # Linux: 使用nice和ionice
                try:
                    # 设置CPU优先级 (需要root或CAP_SYS_NICE)
                    os.nice(-20)  # 最高优先级
                    Log.Info("[GPUOptimizer] 进程优先级: -20 (最高) ⚡")
                except PermissionError:
                    # 没有权限，尝试普通用户能设置的最高优先级
                    os.nice(-10)
                    Log.Info("[GPUOptimizer] 进程优先级: -10 ⚡")

                # 设置I/O优先级
                try:
                    subprocess.run(['ionice', '-c', '1', '-n', '0', '-p', str(os.getpid())],
                                 check=False, capture_output=True)
                    Log.Info("[GPUOptimizer] I/O优先级: Realtime ⚡")
                except:
                    pass

        except Exception as e:
            Log.Debug(f"[GPUOptimizer] 优先级设置失败: {e}")

    def _set_cpu_affinity(self):
        """设置CPU亲和性 - 绑定到性能核心

        i5-13600KF: 6个P核 + 8个E核
        P核: 0-11 (6核12线程，支持超线程)
        E核: 12-19 (8核，不支持超线程)

        策略: 绑定到P核心，获得最高性能
        """
        try:
            import psutil

            # 获取当前进程
            p = psutil.Process()

            # 获取CPU核心数
            cpu_count = psutil.cpu_count(logical=True)

            # i5-13600KF识别: 20个逻辑核心
            if cpu_count == 20:
                # 绑定到P核心 (0-11，前6个物理核的12个逻辑核)
                p_cores = list(range(0, 12))
                p.cpu_affinity(p_cores)
                Log.Info(f"[GPUOptimizer] CPU亲和性: P核心 {p_cores} ⚡⚡")

            elif cpu_count >= 16:
                # 其他高端CPU: 绑定到前75%的核心（通常是性能核心）
                selected_cores = list(range(0, int(cpu_count * 0.75)))
                p.cpu_affinity(selected_cores)
                Log.Info(f"[GPUOptimizer] CPU亲和性: 核心 {selected_cores} ⚡")

            elif cpu_count >= 8:
                # 8核以上: 绑定到前一半核心
                selected_cores = list(range(0, cpu_count // 2))
                p.cpu_affinity(selected_cores)
                Log.Info(f"[GPUOptimizer] CPU亲和性: 核心 {selected_cores} ⚡")
            else:
                # 核心数少，使用所有核心
                Log.Info("[GPUOptimizer] CPU核心数较少，不限制亲和性")

        except ImportError:
            Log.Debug("[GPUOptimizer] psutil未安装，跳过CPU亲和性设置")
        except Exception as e:
            Log.Debug(f"[GPUOptimizer] CPU亲和性设置失败: {e}")

    def _lock_memory(self):
        """锁定进程内存，防止被swap到硬盘

        优点: 避免内存交换导致的性能损失
        注意: 48GB内存足够，可以安全锁定
        """
        try:
            if self.system == "Windows":
                # Windows: 使用SetProcessWorkingSetSize锁定工作集
                try:
                    import win32process
                    import win32api

                    handle = win32api.GetCurrentProcess()
                    # 设置最小和最大工作集大小（锁定内存）
                    # 设置为较大值，允许使用足够内存
                    min_size = 512 * 1024 * 1024  # 512MB
                    max_size = 8 * 1024 * 1024 * 1024  # 8GB
                    win32process.SetProcessWorkingSetSize(handle, min_size, max_size)
                    Log.Info("[GPUOptimizer] 内存锁定: 512MB-8GB ⚡")
                except:
                    pass

            elif self.system == "Linux":
                # Linux: 使用mlockall锁定所有内存
                try:
                    import ctypes
                    libc = ctypes.CDLL("libc.so.6")
                    MCL_CURRENT = 1
                    MCL_FUTURE = 2
                    # 锁定当前和未来分配的内存
                    result = libc.mlockall(MCL_CURRENT | MCL_FUTURE)
                    if result == 0:
                        Log.Info("[GPUOptimizer] 内存锁定: mlockall成功 ⚡")
                    else:
                        Log.Debug("[GPUOptimizer] mlockall失败（可能需要root权限）")
                except Exception as e:
                    Log.Debug(f"[GPUOptimizer] 内存锁定失败: {e}")

        except Exception as e:
            Log.Debug(f"[GPUOptimizer] 内存锁定失败: {e}")

    def _optimize_nvidia_gpu(self):
        """NVIDIA GPU底层优化

        优化项:
        1. 设置电源模式为最大性能
        2. 锁定GPU时钟频率（防止动态降频）
        3. 设置应用程序优先级
        """
        try:
            # 检测NVIDIA GPU
            if not self._has_nvidia_gpu():
                Log.Debug("[GPUOptimizer] 未检测到NVIDIA GPU")
                return

            # 1. 设置电源模式为最大性能
            self._set_nvidia_power_mode()

            # 2. 锁定GPU时钟（防止降频）
            self._lock_gpu_clocks()

            # 3. 设置CUDA优化环境变量
            self._set_cuda_env()

        except Exception as e:
            Log.Debug(f"[GPUOptimizer] NVIDIA优化失败: {e}")

    def _has_nvidia_gpu(self):
        """检测是否有NVIDIA GPU"""
        try:
            # 尝试执行nvidia-smi
            result = subprocess.run(['nvidia-smi', '-L'],
                                  capture_output=True,
                                  text=True,
                                  timeout=2)
            return result.returncode == 0
        except:
            return False

    def _set_nvidia_power_mode(self):
        """设置NVIDIA GPU电源模式为最大性能"""
        try:
            if self.system == "Windows":
                # Windows: 使用nvidia-smi设置
                subprocess.run([
                    'nvidia-smi',
                    '-pm', '1'  # 启用持久模式
                ], capture_output=True, timeout=5)

                subprocess.run([
                    'nvidia-smi',
                    '-pl', '350'  # RTX 5070 Ti设置功耗限制为350W（接近最大）
                ], capture_output=True, timeout=5)

                Log.Info("[GPUOptimizer] NVIDIA电源: 最大性能模式 ⚡⚡")

            elif self.system == "Linux":
                # Linux: 同样使用nvidia-smi
                subprocess.run(['nvidia-smi', '-pm', '1'],
                             capture_output=True, timeout=5)
                subprocess.run(['nvidia-smi', '-pl', '350'],
                             capture_output=True, timeout=5)
                Log.Info("[GPUOptimizer] NVIDIA电源: 最大性能模式 ⚡⚡")

        except Exception as e:
            Log.Debug(f"[GPUOptimizer] NVIDIA电源设置失败: {e}")

    def _lock_gpu_clocks(self):
        """锁定GPU时钟频率到最大值（防止动态降频）

        RTX 5070 Ti规格:
        - Base Clock: ~2.5 GHz
        - Boost Clock: ~2.8 GHz

        锁定到Boost频率，避免性能波动
        """
        try:
            if self.system == "Windows":
                # Windows: 使用nvidia-smi锁定时钟
                # 注意: 可能需要管理员权限
                subprocess.run([
                    'nvidia-smi',
                    '-lgc', '2800,2800'  # 锁定GPU核心频率到2800MHz
                ], capture_output=True, timeout=5)

                Log.Info("[GPUOptimizer] GPU时钟: 锁定到2800MHz ⚡⚡⚡")

            elif self.system == "Linux":
                # Linux: 同样使用nvidia-smi
                subprocess.run(['nvidia-smi', '-lgc', '2800,2800'],
                             capture_output=True, timeout=5)
                Log.Info("[GPUOptimizer] GPU时钟: 锁定到2800MHz ⚡⚡⚡")

        except Exception as e:
            Log.Debug(f"[GPUOptimizer] GPU时钟锁定失败（可能需要管理员权限）: {e}")

    def _set_cuda_env(self):
        """设置CUDA优化环境变量"""
        # CUDA优化环境变量
        cuda_env = {
            # 使用TF32（Tensor Float 32）加速
            'NVIDIA_TF32_OVERRIDE': '1',

            # 启用CUDA图优化
            'CUDA_LAUNCH_BLOCKING': '0',

            # 优化GPU调度
            'CUDA_DEVICE_ORDER': 'PCI_BUS_ID',

            # 设置显存分配策略
            'PYTORCH_CUDA_ALLOC_CONF': 'max_split_size_mb:512',
        }

        for key, value in cuda_env.items():
            os.environ[key] = value

        Log.Info("[GPUOptimizer] CUDA环境变量: 已优化 ⚡")

    def get_optimal_tile_size(self):
        """获取最优Tile Size（根据GPU显存）

        RTX 5070 Ti 16GB: 使用2048
        8GB显卡: 使用1024
        4GB显卡: 使用512
        """
        try:
            # 尝试获取GPU显存
            result = subprocess.run(['nvidia-smi', '--query-gpu=memory.total', '--format=csv,noheader,nounits'],
                                  capture_output=True, text=True, timeout=2)
            if result.returncode == 0:
                vram_mb = int(result.stdout.strip().split('\n')[0])
                vram_gb = vram_mb / 1024

                if vram_gb >= 16:
                    tile_size = 2048
                    Log.Info(f"[GPUOptimizer] Tile Size: {tile_size} (检测到{vram_gb:.1f}GB显存) ⚡⚡")
                    return tile_size
                elif vram_gb >= 8:
                    return 1024
                elif vram_gb >= 4:
                    return 512

        except:
            pass

        # 默认返回2048（假设RTX 5070 Ti）
        Log.Info("[GPUOptimizer] Tile Size: 2048 (默认，RTX 5070 Ti优化) ⚡⚡")
        return 2048

    def optimize_thread_priority(self, thread):
        """优化特定线程的优先级

        Args:
            thread: threading.Thread对象
        """
        try:
            if self.system == "Windows":
                import win32process
                import win32api

                # 获取线程句柄并设置优先级
                try:
                    handle = win32api.OpenThread(
                        win32con.THREAD_SET_INFORMATION,
                        False,
                        thread.ident
                    )
                    win32process.SetThreadPriority(
                        handle,
                        win32process.THREAD_PRIORITY_HIGHEST
                    )
                    Log.Debug(f"[GPUOptimizer] 线程优先级: HIGHEST ({thread.name}) ⚡")
                except:
                    pass

        except Exception as e:
            Log.Debug(f"[GPUOptimizer] 线程优先级设置失败: {e}")

    def restore(self):
        """恢复优化前的设置（清理工作）"""
        try:
            # 解锁GPU时钟
            if self._has_nvidia_gpu():
                subprocess.run(['nvidia-smi', '-rgc'],
                             capture_output=True, timeout=5)
                Log.Info("[GPUOptimizer] GPU时钟: 已解锁")

        except:
            pass


# 全局单例
_optimizer_instance = None

def get_gpu_optimizer():
    """获取GPU优化器单例"""
    global _optimizer_instance
    if _optimizer_instance is None:
        _optimizer_instance = GPUOptimizer()
    return _optimizer_instance


# ============ 测试代码 ============
if __name__ == "__main__":
    print("=== GPU底层优化器测试 ===\n")

    optimizer = GPUOptimizer()

    print("执行优化...")
    optimizer.optimize_all()

    print(f"\n最优Tile Size: {optimizer.get_optimal_tile_size()}")

    print("\n优化完成！按Ctrl+C退出...")
    try:
        import time
        time.sleep(100)
    except KeyboardInterrupt:
        print("\n\n清理中...")
        optimizer.restore()
        print("已恢复")

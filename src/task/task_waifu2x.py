import json
import os
import threading
import time
from zlib import crc32

from config import config
from config.setting import Setting
from task.qt_task import TaskBase
from tools.log import Log
from tools.status import Status
from tools.str import Str
from tools.tool import CTime, ToolUtil
from tools.software_optimizer import get_software_optimizer  # 软件层面优化


class QConvertTask(object):
    def __init__(self, taskId=0):
        self.taskId = taskId
        self.callBack = None       # addData, laveSize
        self.backParam = None
        self.cleanFlag = ""
        self.status = Status.Ok
        self.tick = 0
        self.loadPath = ""  #
        self.preDownPath = ""  #
        self.noSaveCache = False
        self.cachePath = ""  #
        self.savePath = ""  #
        self.imgData = b""
        self.saveData = b""

        self.model = {
            "isForce":0,
            "model": 1,
            "scale": 2,
            "toH": 100,
            "toW": 100,
        }

class TaskWaifu2x(TaskBase):

    def __init__(self):
        TaskBase.__init__(self)
        self.taskObj.convertBack.connect(self.HandlerTask)

        # 🚀 软件优化：进程调度和算法优化（不修改硬件设置）
        Log.Info("[TaskWaifu2x] 🚀 初始化软件优化器...")
        self.sw_optimizer = get_software_optimizer()
        self.sw_optimizer.optimize_all()

        # 算法优化：动态Tile Size（16GB显存 → 2048）
        self.optimal_tile_size = self.sw_optimizer.get_optimal_tile_size()
        Log.Info(f"[TaskWaifu2x] ✅ 优化Tile Size: {self.optimal_tile_size} ⚡⚡⚡")

        # 允许用户覆盖Tile Size，未设置时使用自动值
        self.base_tile_size = Setting.Waifu2xTileSize.value or self.optimal_tile_size

        self.thread.start()

        self.thread2 = threading.Thread(target=self.RunLoad2)
        self.thread2.setName("Task-" + str("Waifu2x"))
        self.thread2.setDaemon(True)

        # 软件优化：提升线程优先级（纯调度优化）
        self.sw_optimizer.optimize_thread_priority(self.thread2)

    def Start(self):
        self.thread2.start()
        return

    def Run(self):
        while True:
            taskId = self._inQueue.get(True)
            self._inQueue.task_done()
            if taskId == "":
                break

            task = self.tasks.get(taskId)
            if not task:
                continue
            assert isinstance(task, QConvertTask)
            try:
                assert isinstance(task, QConvertTask)
                isFind = False

                if task.cachePath:
                    data = ToolUtil.LoadCachePicture(task.cachePath)
                    if data:
                        task.saveData = data
                        self.taskObj.convertBack.emit(taskId)
                        continue

                if task.preDownPath:
                    data = ToolUtil.LoadCachePicture(task.preDownPath)
                    if data:
                        task.saveData = data
                        self.taskObj.convertBack.emit(taskId)
                        continue

                if task.savePath:
                    if ToolUtil.IsHaveFile(task.savePath):
                        self.taskObj.convertBack.emit(taskId)
                        continue

                if task.loadPath:
                    data = ToolUtil.LoadCachePicture(task.loadPath)
                    if data:
                        w, h, mat,_ = ToolUtil.GetPictureSize(data)
                        model = ToolUtil.GetDownloadScaleModel(w, h, mat)
                        if not task.model.get("isForce"):
                            task.model = model
                        task.imgData = data

                if not task.imgData:
                    task.status = Status.FileError
                    self.taskObj.convertBack.emit(taskId)
                    continue

                if isFind:
                    continue

                err = ""
                if config.CanWaifu2x:
                    from sr_vulkan import sr_vulkan as sr
                    # 补全元数据（format/宽高），避免后续调用出现空值
                    src_w = task.model.get("_src_w", 0)
                    src_h = task.model.get("_src_h", 0)
                    mat = task.model.get("format", "")
                    if src_w <= 0 or src_h <= 0 or not mat:
                        try:
                            src_w, src_h, mat2, _ = ToolUtil.GetPictureSize(task.imgData)
                            task.model["_src_w"] = src_w
                            task.model["_src_h"] = src_h
                            if not mat:
                                mat = mat2
                                task.model["format"] = mat
                        except Exception as info_es:
                            Log.Warn(f"[Waifu2x] parse meta failed: {info_es}")

                    try:
                        scale = float(task.model.get("scale", 0) or 0)
                    except Exception:
                        scale = 0
                    target_w = task.model.get("width", 0)
                    target_h = task.model.get("high", 0)
                    # 3x黑屏修复：强制走宽高模式，减少tileSize防止显存溢出
                    use_scale = scale
                    if scale >= 2.9:
                        if src_w and src_h:
                            target_w = int(src_w * scale)
                            target_h = int(src_h * scale)
                            task.model["width"] = target_w
                            task.model["high"] = target_h
                        use_scale = 0
                    if use_scale <= 0 and (not target_w or not target_h):
                        # 没有宽高信息时退回倍率模式，避免传入0导致任务失败
                        use_scale = scale
                        target_w = target_w or src_w
                        target_h = target_h or src_h

                    tileSize = self._calc_tile_size(use_scale, target_w, target_h)
                    mat = mat or "png"

                    if use_scale <= 0:
                        sts = sr.add(task.imgData, task.model.get("model", 0), task.taskId, target_w, target_h, format=mat, tileSize=tileSize)
                    else:
                        sts = sr.add(task.imgData, task.model.get("model", 0), task.taskId, use_scale, format=mat, tileSize=tileSize)

                    if sts <= 0:
                        err = sr.getLastError()

                else:
                    sts = -1
                if sts <= 0:
                    task.status = Status.AddError
                    self.taskObj.convertBack.emit(taskId)
                    Log.Warn("Waifu2x convert error, taskId: {}, model:{}, err:{}".format(str(task.taskId), task.model,
                                                                                     str(err)))
                    continue
            except Exception as es:
                Log.Error(es)
                task.status = Status.PathError
                self.taskObj.convertBack.emit(taskId)
                continue

    def _calc_tile_size(self, scale, target_w, target_h):
        """
        根据倍率和目标尺寸动态调整tile size：
        - 根据目标图片大小动态降低tile size，避免显存溢出导致黑屏
        - 使用更激进的策略防止vkAllocateMemory失败
        - 保底200，避免传0
        """
        tile_size = self.base_tile_size if self.base_tile_size else self.optimal_tile_size
        try:
            max_side = max(target_w or 0, target_h or 0)
            # 更激进的降级策略，防止显存溢出
            if max_side >= 6000:
                # 6000x4000+: 使用极小tile size防止16GB显存溢出
                tile_size = min(tile_size, 256)
                Log.Info(f"[Waifu2x] 超大图片检测: {target_w}x{target_h}, 降低tile_size至{tile_size}防止显存溢出")
            elif max_side >= 5000:
                # 5000x3000+: 使用小tile size
                tile_size = min(tile_size, 400)
                Log.Info(f"[Waifu2x] 大图片检测: {target_w}x{target_h}, 降低tile_size至{tile_size}")
            elif max_side >= 4000:
                # 4000x3000+: 使用中等tile size
                tile_size = min(tile_size, 512)
            elif scale >= 2.9:
                # 3x放大也要降低
                tile_size = min(tile_size, 768)

            Log.Debug(f"[Waifu2x] calc tile size: scale={scale}, target={target_w}x{target_h}, max_side={max_side}, tile_size={tile_size}")
        except Exception as es:
            Log.Debug(f"[Waifu2x] calc tile size failed: {es}")
        return max(tile_size, 200)

    def LoadData(self):
        if not config.CanWaifu2x:
            time.sleep(100)
            return None
        from sr_vulkan import sr_vulkan as sr
        return sr.load(0)

    def RunLoad2(self):
        while True:
            info = self.LoadData()
            if not info:
                break
            t1 = CTime()
            data, format, taskId, tick = info
            info = self.tasks.get(taskId)
            tick = round(tick, 2)
            if not info:
                continue
            if not data:
                lenData = 0
            else:
                lenData = len(data)
            if lenData <= 0:
                info.status = Status.FileFormatError
                Log.Warn("convert error, taskId: {}, dataLen:{}, sts:{} tick:{}, skip:{}".format(str(taskId), lenData,
                                                                                          str(format),
                                                                                          str(tick), str(Setting.IsSkipPic.value)))
                if info.savePath and Setting.IsSkipPic.value:
                    info.status = Status.Ok
                    data = info.imgData

            assert isinstance(info, QConvertTask)
            info.saveData = data
            info.tick = tick
            try:
                if not info.noSaveCache:
                    for path in [info.cachePath, info.savePath]:
                        if path and not os.path.isdir(os.path.dirname(path)):
                            os.makedirs(os.path.dirname(path))

                        if path and data:
                            with open(path, "wb+") as f:
                                f.write(data)
            except Exception as es:
                info.status = Status.SaveError
                Log.Error(es)

            self.taskObj.convertBack.emit(taskId)
            t1.Refresh("RunLoad")

    def AddConvertTaskByData(self, path, imgData, model, callBack, backParam=None, preDownPath=None, noSaveCache=False, cleanFlag=None):
        info = QConvertTask()
        info.callBack = callBack
        info.backParam = backParam
        self.taskId += 1
        self.tasks[self.taskId] = info
        info.taskId = self.taskId
        info.imgData = imgData
        info.model = model
        info.preDownPath = preDownPath
        info.noSaveCache = noSaveCache
        if not noSaveCache and path and Setting.SavePath.value:
            info.cachePath = os.path.join(os.path.join(Setting.SavePath.value, config.CachePathDir), os.path.join("waifu2x", path))

        if cleanFlag:
            info.cleanFlag = cleanFlag
            taskIds = self.flagToIds.setdefault(cleanFlag, set())
            taskIds.add(self.taskId)
        Log.Debug("add convert info, taskId:{}, cachePath:{}".format(info.taskId, info.cachePath))
        self._inQueue.put(self.taskId)
        return self.taskId

    def AddConvertTaskByPath(self, loadPath, savePath, callBack, backParam=None, cleanFlag=None):
        info = QConvertTask()
        info.loadPath = loadPath
        info.savePath = savePath
        info.callBack = callBack
        info.backParam = backParam
        self.taskId += 1
        self.tasks[self.taskId] = info
        info.taskId = self.taskId
        if cleanFlag:
            info.cleanFlag = cleanFlag
            taskIds = self.flagToIds.setdefault(cleanFlag, set())
            taskIds.add(self.taskId)
        Log.Debug("add convert info, loadPath:{}, savePath:{}".format(info.loadPath, info.savePath))
        self._inQueue.put(self.taskId)
        return self.taskId

    def AddConvertTaskByPathSetModel(self, loadPath, savePath, callBack, backParam=None, model=None, cleanFlag=None):
        info = QConvertTask()
        info.loadPath = loadPath
        info.savePath = savePath
        info.callBack = callBack
        info.backParam = backParam
        info.model = model
        self.taskId += 1
        self.tasks[self.taskId] = info
        info.taskId = self.taskId
        if cleanFlag:
            info.cleanFlag = cleanFlag
            taskIds = self.flagToIds.setdefault(cleanFlag, set())
            taskIds.add(self.taskId)
        Log.Debug("add convert info, loadPath:{}, savePath:{}".format(info.loadPath, info.savePath))
        self._inQueue.put(self.taskId)
        return self.taskId

    def HandlerTask(self, taskId, isCallBack=True):
        try:
            info = self.tasks.get(taskId)
            if not info:
                return

            assert isinstance(info, QConvertTask)
            info.callBack(info.saveData, info.status, info.backParam, info.tick)
            if info.cleanFlag:
                taskIds = self.flagToIds.get(info.cleanFlag, set())
                taskIds.discard(info.taskId)
            del self.tasks[taskId]
        except Exception as es:
            Log.Error(es)

    def ClearWaitConvertIds(self, taskIds):
        if not taskIds:
            return
        for taskId in taskIds:
            if taskId in self.tasks:
                del self.tasks[taskId]
        Log.Info("cancel wait convert taskId, {}".format(taskIds))
        if config.CanWaifu2x:
            from sr_vulkan import sr_vulkan as sr
            sr.removeWaitProc(list(taskIds))

    def Cancel(self, cleanFlag):
        taskIds = self.flagToIds.get(cleanFlag, set())
        if not taskIds:
            return
        removeIds = []
        for taskId in taskIds:
            if taskId in self.tasks:
                del self.tasks[taskId]
                removeIds.append(taskId)
        Log.Info("cancel convert taskId, {}".format(removeIds))
        self.flagToIds.pop(cleanFlag)
        if config.CanWaifu2x:
            from sr_vulkan import sr_vulkan as sr
            sr.remove(removeIds)


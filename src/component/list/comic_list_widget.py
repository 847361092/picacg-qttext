from functools import partial

from PySide6.QtCore import Qt
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QListWidgetItem, QMenu, QApplication,QListView

from component.list.base_list_widget import BaseListWidget
from component.widget.comic_item_widget import ComicItemWidget
from config import config
from config.setting import Setting
from qt_owner import QtOwner
from tools.status import Status
from tools.str import Str
from tools.tool import ToolUtil


class ComicListWidget(BaseListWidget):
    def __init__(self, parent):
        BaseListWidget.__init__(self, parent)
        self.resize(800, 600)
        # self.setMinimumHeight(400)
        self.setFrameShape(QListView.NoFrame)  # 无边框
        self.setFlow(QListView.LeftToRight)  # 从左到右
        self.setWrapping(True)
        self.setResizeMode(QListView.Adjust)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.SelectMenuBook)
        # self.doubleClicked.connect(self.OpenBookInfo)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.itemClicked.connect(self.SelectItem)
        self.isDelMenu = False
        self.isGame = False
        self.isLocal = False
        self.isLocalEps = False
        self.isMoveMenu = False
        self.openMenu = False

        # 🚀 优化：智能封面加载 - 优先加载可见区域
        self._pending_loads = set()  # 待加载的索引
        self._loading_items = set()  # 正在加载的索引
        self._buffer_size = 10  # 缓冲区大小（可见区域前后N个item）

        # 连接滚动事件
        self.verticalScrollBar().valueChanged.connect(self._on_scroll_changed)

    def _get_visible_indices(self):
        """
        获取当前可见的item索引

        优化说明：
        - 只加载可见区域的封面，避免浪费带宽
        - 改善首屏加载速度
        """
        visible_indices = []
        viewport_rect = self.viewport().rect()

        for i in range(self.count()):
            item = self.item(i)
            if not item:
                continue

            item_rect = self.visualItemRect(item)
            # 检查item是否与viewport相交（即可见）
            if viewport_rect.intersects(item_rect):
                visible_indices.append(i)

        return visible_indices

    def _get_priority_indices(self):
        """
        获取优先加载的索引（可见区域 + 缓冲区）

        优化说明：
        - 可见区域：立即加载（用户正在看）
        - 缓冲区：预加载（用户可能即将看到）
        - 其他：暂不加载（等滚动到附近时再加载）
        """
        visible_indices = self._get_visible_indices()
        priority_indices = set(visible_indices)

        # 添加缓冲区（可见item前后N个）
        for idx in visible_indices:
            for offset in range(-self._buffer_size, self._buffer_size + 1):
                buffer_idx = idx + offset
                if 0 <= buffer_idx < self.count():
                    priority_indices.add(buffer_idx)

        return priority_indices

    def _on_scroll_changed(self):
        """
        滚动事件处理

        优化说明：
        - 滚动时触发可见item的加载
        - 避免paintEvent的无序加载（按绘制顺序）
        - 改为有序加载（按可见优先级）
        """
        self._trigger_visible_loads()

    def _trigger_visible_loads(self):
        """
        触发可见区域的封面加载

        优化说明：
        - 主动触发加载，而不是等待paintEvent
        - 优先加载可见item，提升首屏速度
        """
        priority_indices = self._get_priority_indices()

        # 遍历优先索引，触发未加载的item
        for index in sorted(priority_indices):  # 排序保证从上到下加载
            if index in self._loading_items:
                continue  # 已在加载中

            item = self.item(index)
            if not item:
                continue

            widget = self.itemWidget(item)
            if not isinstance(widget, ComicItemWidget):
                continue

            # 检查是否需要加载
            if not widget.isLoadPicture and widget.url and config.IsLoadingPicture:
                widget.isLoadPicture = True
                self._loading_items.add(index)
                self.LoadingPicture(index)

    def showEvent(self, event):
        """
        Widget显示事件

        优化说明：
        - 列表首次显示时，立即加载首屏封面
        - 避免等待用户滚动或paintEvent触发
        """
        super().showEvent(event)
        # 延迟触发，确保布局完成
        from PySide6.QtCore import QTimer
        QTimer.singleShot(100, self._trigger_visible_loads)

    def SelectMenuBook(self, pos):
        index = self.indexAt(pos)
        widget = self.indexWidget(index)
        if index.isValid() and widget:
            assert isinstance(widget, ComicItemWidget)
            popMenu = QMenu(self)

            if not self.isLocal:
                action = popMenu.addAction(Str.GetStr(Str.Open))
                action.triggered.connect(partial(self.OpenBookInfoHandler, index))
                nas = QMenu(Str.GetStr(Str.NetNas))
                nasDict = QtOwner().owner.nasView.nasDict
                if not nasDict:
                    action = nas.addAction(Str.GetStr(Str.CvSpace))
                    action.setEnabled(False)
                else:
                    for k, v in nasDict.items():
                        action = nas.addAction(v.showTitle)
                        if QtOwner().nasView.IsInUpload(k, widget.id):
                            action.setEnabled(False)
                        action.triggered.connect(partial(self.NasUploadHandler, k, index))
                popMenu.addMenu(nas)
                
            action = popMenu.addAction(Str.GetStr(Str.LookCover))
            action.triggered.connect(partial(self.OpenPicture, index))
            action = popMenu.addAction(Str.GetStr(Str.ReDownloadCover))
            action.triggered.connect(partial(self.ReDownloadPicture, index))
            if config.CanWaifu2x and widget.picData:
                if not widget.isWaifu2x:
                    action = popMenu.addAction(Str.GetStr(Str.Waifu2xConvert))
                    action.triggered.connect(partial(self.Waifu2xPicture, index))
                    if widget.isWaifu2xLoading or not config.CanWaifu2x:
                        action.setEnabled(False)
                else:
                    action = popMenu.addAction(Str.GetStr(Str.DelWaifu2xConvert))
                    action.triggered.connect(partial(self.CancleWaifu2xPicture, index))
            action = popMenu.addAction(Str.GetStr(Str.CopyTitle))
            action.triggered.connect(partial(self.CopyHandler, index))

            if not self.isLocal:
                action = popMenu.addAction(Str.GetStr(Str.Download))
                action.triggered.connect(partial(self.DownloadHandler, index))

                if not self.isGame:
                    action = popMenu.addAction(Str.GetStr(Str.DownloadAll))
                    action.triggered.connect(self.OpenBookDownloadAll)
            
            if self.isDelMenu:
                action = popMenu.addAction(Str.GetStr(Str.Delete))
                action.triggered.connect(partial(self.DelHandler, index))
            if self.isMoveMenu:
                action = popMenu.addAction(Str.GetStr(Str.Move))
                action.triggered.connect(partial(self.MoveHandler, index))
            if self.openMenu:
                action = popMenu.addAction(Str.GetStr(Str.OpenDir))
                action.triggered.connect(partial(self.OpenDirHandler, index))

            popMenu.exec_(QCursor.pos())
        return

    def AddBookByDict(self, v):
        _id = v.get("_id")
        title = v.get("title")
        categories = v.get("categories", [])
        if "thumb" in v:
            url = v.get("thumb", {}).get("fileServer")
            path = v.get("thumb", {}).get("path")
        elif "icon" in v:
            url = v.get("icon", {}).get("fileServer")
            path = v.get("icon", {}).get("path")
        else:
            url = ""
            path = ""
        categoryStr = "，".join(categories)
        likesCount = str(v.get("totalLikes", ""))
        finished = v.get("finished")
        pagesCount = v.get("pagesCount")
        isShiled = QtOwner().IsInFilter(categoryStr, "", title)
        self.AddBookItem(_id, title, categoryStr, url, path, likesCount, "", pagesCount, finished, isShiled=isShiled)

    def AddBookByLocal(self, v, category=""):
        from task.task_local import LocalData
        assert isinstance(v, LocalData)
        index = self.count()
        widget = ComicItemWidget()
        widget.setFocusPolicy(Qt.NoFocus)
        widget.id = v.id
        title = v.title
        widget.index = index
        widget.title = v.title
        widget.picNum = v.picCnt
        widget.url = v.file
        if len(v.eps) > 0:
            fontColor = "<font color=#d5577c>{}</font>".format("(" + str(len(v.eps)) + "E)")
        else:
            fontColor = "<font color=#d5577c>{}</font>".format("(" + str(v.picCnt) + "P)")
        if v.lastReadTime:
            categories = "{} {}".format(ToolUtil.GetUpdateStrByTick(v.lastReadTime), Str.GetStr(Str.Looked))

            widget.timeLabel.setText(categories)
        else:
            widget.timeLabel.setVisible(False)
            widget.starButton.setVisible(False)

        widget.categoryLabel.setVisible(False)
        if category:
            widget.categoryLabel.setText(category)
            widget.categoryLabel.setVisible(True)

        widget.toolButton.setVisible(False)
        # widget.nameLable.setText(title)
        widget.SetTitle(title,fontColor)

        item = QListWidgetItem(self)
        item.setFlags(item.flags() & ~Qt.ItemIsSelectable)
        item.setSizeHint(widget.sizeHint())
        self.setItemWidget(item, widget)
        widget.picLabel.setText(Str.GetStr(Str.LoadingPicture))
        widget.PicLoad.connect(self.LoadingPicture)

    def AddBookItemByBook(self, v, isShowHistory=False, isShowToolButton=False):
        title = v.title
        url = v.fileServer
        path = v.path
        _id = v.id
        finished = v.finished
        pagesCount = v.pages
        likesCount = str(v.likesCount)
        updated_at = v.updated_at
        categories = v.categories
        updated_at = v.updated_at
        if isShowHistory:
            info = QtOwner().owner.historyView.GetHistory(_id)
            if info:
                if v.epsCount-1 > info.epsId:
                    isShowToolButton = True

                categories = Str.GetStr(Str.LastLook) + str(info.epsId + 1) + Str.GetStr(Str.Chapter) + "/" + str(v.epsCount) + Str.GetStr(Str.Chapter)
        if hasattr(v, "tags") and isinstance(v.tags, list):
            tags = ",".join(v.tags)
        elif hasattr(v, "tags") and isinstance(v.tags, str):
            tags = v.tags
        else:
            tags = ""
        isShiled = QtOwner().IsInFilter(categories, tags, title)
        self.AddBookItem(_id, title, categories, url, path, likesCount, updated_at, pagesCount, finished, isShowToolButton=isShowToolButton, isShiled=isShiled, tags=tags)

    def AddBookItemByHistory(self, v):
        _id = v.bookId
        title = v.name
        path = v.path
        url = v.url
        categories = "{} {}".format(ToolUtil.GetUpdateStrByTick(v.tick), Str.GetStr(Str.Looked))
        self.AddBookItem(_id, title, categories, url, path)

    def AddBookItem(self, _id, title, categoryStr="", url="", path="", likesCount="", updated_at="", pagesCount="", finished="", isShowToolButton=False, isShiled=False, tags=""):
        index = self.count()
        widget = ComicItemWidget(isShiled=isShiled)
        widget.setFocusPolicy(Qt.NoFocus)
        widget.id = _id
        widget.title = title
        widget.picNum = pagesCount
        widget.category = categoryStr
        widget.tags = tags

        widget.url = ToolUtil.GetRealUrl(url, path)
        if self.isGame:
            widget.path = ToolUtil.GetRealPath(_id, "game/cover")
        else:
            widget.path = ToolUtil.GetRealPath(_id, "cover")

        widget.index = index
        if not isShowToolButton:
            widget.toolButton.hide()
        widget.categoryLabel.setText(categoryStr)
        if updated_at:
            dayStr = ToolUtil.GetUpdateStr(updated_at)
            updateStr = dayStr + Str.GetStr(Str.Update)
            widget.timeLabel.setText(updateStr)
            widget.timeLabel.setVisible(True)
        else:
            widget.timeLabel.setVisible(False)

        if likesCount:
            widget.starButton.setText(str(likesCount))
            widget.starButton.setVisible(True)
        else:
            widget.starButton.setVisible(False)
        fontColor = ""
        if pagesCount:
            fontColor += "<font color=#d5577c>{}</font>".format("("+str(pagesCount)+"P)")
        # if finished:
        #     fontColor += "<font color=#d5577c>{}</font>".format("({})".format(Str.GetStr(Str.ComicFinished)))

        # widget.nameLable.setText(title)

        widget.SetTitle(title,fontColor)
        item = QListWidgetItem(self)
        item.setFlags(item.flags() & ~Qt.ItemIsSelectable)
        item.setSizeHint(widget.sizeHint())
        self.setItemWidget(item, widget)
        if not isShiled:
            widget.picLabel.setText(Str.GetStr(Str.LoadingPicture))
        widget.PicLoad.connect(self.LoadingPicture)
        # if url and config.IsLoadingPicture:
        #     self.AddDownloadTask(url, path, completeCallBack=self.LoadingPictureComplete, backParam=index)
        #     pass

    def DelBookID(self, bookID):
        for row in range(0, self.count()):
            item = self.item(row)
            w = self.itemWidget(item)
            if w.id == bookID:
                item.setHidden(True)
                break

    def LoadingPicture(self, index):
        item = self.item(index)
        widget = self.itemWidget(item)
        assert isinstance(widget, ComicItemWidget)
        self.AddDownloadTask(widget.url, widget.path, completeCallBack=self.LoadingPictureComplete, backParam=index)

    def LoadingPictureComplete(self, data, status, index):
        # 🚀 优化：标记加载完成，允许重试或后续操作
        self._loading_items.discard(index)

        if status == Status.Ok:
            item = self.item(index)
            widget = self.itemWidget(item)
            if not widget:
                return
            assert isinstance(widget, ComicItemWidget)
            widget.SetPicture(data)
            if Setting.CoverIsOpenWaifu.value:
                item = self.item(index)
                indexModel = self.indexFromItem(item)
                self.Waifu2xPicture(indexModel, True)
            pass
        else:
            item = self.item(index)
            widget = self.itemWidget(item)
            if not widget:
                return
            assert isinstance(widget, ComicItemWidget)
            widget.SetPictureErr(status)
        return

    def SelectItem(self, item):
        assert isinstance(item, QListWidgetItem)
        widget = self.itemWidget(item)
        assert isinstance(widget, ComicItemWidget)
        if widget.isShiled:
            QtOwner().ShowError(Str.GetStr(Str.Hidden))
            return
        if self.isGame:
            QtOwner().OpenGameInfo(widget.id)
        elif self.isLocalEps:
            QtOwner().OpenLocalEpsBook(widget.id)
        elif self.isLocal:
            QtOwner().OpenLocalBook(widget.id)
        else:
            QtOwner().OpenBookInfo(widget.id)
        return

    def OpenBookInfoHandler(self, index):
        widget = self.indexWidget(index)
        if widget:
            assert isinstance(widget, ComicItemWidget)
            QtOwner().OpenBookInfo(widget.id)
            return

    def OpenPicture(self, index):
        widget = self.indexWidget(index)
        if widget:
            assert isinstance(widget, ComicItemWidget)
            QtOwner().OpenWaifu2xTool(widget.picData)
            return

    def ReDownloadPicture(self, index):
        widget = self.indexWidget(index)
        if widget:
            assert isinstance(widget, ComicItemWidget)
            if widget.url and config.IsLoadingPicture:
                widget.SetPicture("")
                item = self.itemFromIndex(index)
                count = self.row(item)
                widget.picLabel.setText(Str.GetStr(Str.LoadingPicture))
                self.AddDownloadTask(widget.url, widget.path, completeCallBack=self.LoadingPictureComplete, backParam=count, isReload=True)
                pass

    def Waifu2xPicture(self, index, isIfSize=False):
        widget = self.indexWidget(index)
        assert isinstance(widget, ComicItemWidget)
        if widget and widget.picData:
            w, h, mat,_ = ToolUtil.GetPictureSize(widget.picData)
            if max(w, h) <= Setting.CoverMaxNum.value or not isIfSize:
                model = ToolUtil.GetModelByIndex(Setting.CoverLookModelName.value, Setting.CoverLookScale.value, mat)
                widget.isWaifu2xLoading = True
                if self.isLocal:
                    self.AddConvertTask(widget.path, widget.picData, model, self.Waifu2xPictureBack, index, noSaveCache=True)
                else:
                    self.AddConvertTask(widget.path, widget.picData, model, self.Waifu2xPictureBack, index)

    def CancleWaifu2xPicture(self, index):
        widget = self.indexWidget(index)
        assert isinstance(widget, ComicItemWidget)
        if widget.isWaifu2x and widget.picData:
            widget.SetPicture(widget.picData)

    def Waifu2xPictureBack(self, data, waifuId, index, tick):
        widget = self.indexWidget(index)
        if data and widget:
            assert isinstance(widget, ComicItemWidget)
            widget.SetWaifu2xData(data)
        return

    def CopyHandler(self, index):
        widget = self.indexWidget(index)
        if widget:
            assert isinstance(widget, ComicItemWidget)
            data = widget.GetTitle() + str("\r\n")
            clipboard = QApplication.clipboard()
            data = data.strip("\r\n")
            clipboard.setText(data)
        pass

    def OpenBookDownloadAll(self):
        from view.download.download_all_item import DownloadAllItem
        allData = DownloadAllItem.MakeAllItem(self)
        QtOwner().OpenDownloadAll(allData)

    def DelHandler(self, index):
        widget = self.indexWidget(index)
        if widget:
            self.DelCallBack(widget.id)

    def DelCallBack(self, cfgId):
        return

    def DownloadHandler(self, index):
        widget = self.indexWidget(index)
        if widget:
            QtOwner().OpenEpsInfo(widget.id)
        pass

    def MoveHandler(self, index):
        return

    def NasUploadHandler(self, nasId, index):
        widget = self.indexWidget(index)
        if widget:
            QtOwner().nasView.AddNasUpload(nasId, widget.id)
        pass
    
    def OpenDirHandler(self, index):
        return
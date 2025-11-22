# -*- coding: utf-8 -*-
"""第一个程序"""
import os
import sys
# macOS 修复
import time
import traceback
import signal

from config import config
from config.setting import Setting, SettingValue
from qt_error import showError, showError2
from qt_owner import QtOwner
from tools.log import Log
from tools.str import Str

if sys.platform == 'darwin':
    # 确保工作区为当前可执行文件所在目录
    current_path = os.path.abspath(__file__)
    current_dir = os.path.abspath(os.path.dirname(current_path) + os.path.sep + '.')
    os.chdir(current_dir)

# 🚀 优化：Waifu2x延迟加载（只延迟模型，不延迟sr模块）
# 🔧 修复：先同步检查sr模块是否可用，避免sr=None导致的错误
try:
    from sr_vulkan import sr_vulkan as sr
    config.CanWaifu2x = True
    config.CloseWaifu2x = False
except ModuleNotFoundError as es:
    sr = None
    config.CanWaifu2x = False
    config.CloseWaifu2x = True
    if hasattr(es, "msg"):
        config.ErrorMsg = es.msg
except Exception as es:
    sr = None
    config.CanWaifu2x = False
    if hasattr(es, "msg"):
        config.ErrorMsg = es.msg

def lazy_load_waifu2x_models():
    """
    延迟加载Waifu2x模型文件（在后台线程进行）

    优化说明：
    - sr模块导入很快，立即同步导入（避免sr=None错误）
    - 模型文件加载慢（1-2秒），后台加载不阻塞启动
    - 用户通常不会立即使用Waifu2x功能
    """
    if not config.CanWaifu2x:
        return  # sr模块不可用，无需加载模型

    start_time = time.time()
    Log.Info("[Startup] Waifu2x models loading started in background...")

    try:
        # 加载模型文件（耗时操作）
        import sr_vulkan_model_waifu2x
        Log.Info("[Startup] Loaded sr_vulkan_model_waifu2x")
        import sr_vulkan_model_realcugan
        Log.Info("[Startup] Loaded sr_vulkan_model_realcugan")
        import sr_vulkan_model_realesrgan
        Log.Info("[Startup] Loaded sr_vulkan_model_realesrgan")

        elapsed = time.time() - start_time
        Log.Info("[Startup] ✅ Waifu2x models loaded in {:.2f}s (background)".format(elapsed))

    except Exception as model_error:
        Log.Warn("[Startup] Waifu2x model loading error: {}".format(model_error))
        # 注意：即使模型加载失败，sr模块仍然可用


from PySide6.QtGui import QFont, QPixmap, QPainter, QColor
from PySide6 import QtWidgets, QtGui  # 导入PySide6部件
from PySide6.QtNetwork import QLocalSocket, QLocalServer
from PySide6.QtWidgets import QSplashScreen
from PySide6.QtCore import Qt
# 此处不能删除
import images_rc
from server.sql_server import DbBook as DbBook
DbBook()

if __name__ == "__main__":
    try:
        Log.Init()
        Setting.Init()
        Setting.InitLoadSetting()
        os.environ['QT_IMAGEIO_MAXALLOC'] = "10000000000000000000000000000000000000000000000000000000000000000"
        QtGui.QImageReader.setAllocationLimit(0)
        if Setting.IsUseScaleFactor.value > 0:
            indexV = Setting.ScaleFactor.value
            # os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "0"
            os.environ["QT_SCALE_FACTOR"] = str(indexV / 100)

    except Exception as es:
        Log.Error(es)
        app = QtWidgets.QApplication(sys.argv)
        showError(traceback.format_exc(), app)
        if config.CanWaifu2x:
            sr.stop()
        sys.exit(-111)

    app = QtWidgets.QApplication(sys.argv)  # 建立application对象

    # 🚀 优化：创建Splash Screen（改善启动体验）
    splash = None
    try:
        # 创建一个简单的启动画面
        splash_pixmap = QPixmap(400, 300)
        splash_pixmap.fill(QColor(45, 45, 48))  # 深色背景

        # 绘制文字
        painter = QPainter(splash_pixmap)
        painter.setPen(QColor(255, 255, 255))
        font = QFont("Arial", 24, QFont.Bold)
        painter.setFont(font)
        painter.drawText(splash_pixmap.rect(), Qt.AlignCenter, "PicACG\n\nLoading...")
        painter.end()

        splash = QSplashScreen(splash_pixmap, Qt.WindowStaysOnTopHint)
        splash.show()
        app.processEvents()  # 立即显示splash screen
        Log.Info("[Startup] Splash screen displayed")
    except Exception as splash_error:
        Log.Warn("[Startup] Splash screen creation failed: {}".format(splash_error))

    serverName = 'Picacg-qt'
    socket = QLocalSocket()
    socket.connectToServer(serverName)
    if socket.waitForConnected(500):
        socket.write(b"restart")
        socket.flush()
        socket.close()
        app.quit()
        Log.Warn("server already star")
        if splash:
            splash.close()
        sys.exit(1)

    localServer = QLocalServer()  # 没有实例运行，创建服务器
    localServer.listen(serverName)

    Log.Warn("init scene ratio: {}".format(app.devicePixelRatio()))
    try:
        Str.Reload()
        QtOwner().SetApp(app)
        QtOwner().SetLocalServer(localServer)
        QtOwner().SetFont()
        from view.main.main_view import MainView

        # 记录启动时间
        startup_begin = time.time()

        # 在splash screen上显示进度信息
        if splash:
            splash.showMessage("Initializing...", Qt.AlignBottom | Qt.AlignCenter, QColor(255, 255, 255))
            app.processEvents()

        main = MainView()

        if splash:
            splash.showMessage("Loading UI...", Qt.AlignBottom | Qt.AlignCenter, QColor(255, 255, 255))
            app.processEvents()

        main.show()  # 显示窗体

        if splash:
            splash.showMessage("Starting...", Qt.AlignBottom | Qt.AlignCenter, QColor(255, 255, 255))
            app.processEvents()

        main.Init()
        localServer.newConnection.connect(main.OnNewConnection)

        # 🚀 优化：启动后台线程加载Waifu2x模型（不阻塞UI）
        import threading
        waifu2x_thread = threading.Thread(target=lazy_load_waifu2x_models, daemon=True, name="Waifu2xLoader")
        waifu2x_thread.start()

        # 关闭splash screen
        if splash:
            splash.finish(main)
            Log.Info("[Startup] Splash screen closed")

        # 记录启动完成时间
        startup_elapsed = time.time() - startup_begin
        Log.Info("[Startup] ✅ Application started in {:.2f}s (UI ready, Waifu2x loading in background)".format(startup_elapsed))
    except Exception as es:
        Log.Error(es)
        # 🔧 修复：异常时关闭splash screen
        if splash:
            splash.close()
        showError(traceback.format_exc(), app)
        if config.CanWaifu2x:
            sr.stop()
        sys.exit(-111)

    oldHook = sys.excepthook


    def excepthook(exc_type, exc_value, exc_tb):
        tb = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        Log.Error(tb)
        showError2(tb, app)


    sys.excepthook = excepthook
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    sts = app.exec()
    sys.excepthook = oldHook
    socket.close()
    main.Close()
    if config.CanWaifu2x:
        sr.stop()
    time.sleep(2)
    print(sts)
    sys.exit(sts)

# Windows安装libjpeg-turbo指南

## 方法一：通过官方安装程序（推荐）

### 步骤1：下载
访问官方GitHub Release页面：
https://github.com/libjpeg-turbo/libjpeg-turbo/releases

下载最新版本（例如3.0.4）：
- **64位系统**: `libjpeg-turbo-3.0.4-vc64.exe`
- **32位系统**: `libjpeg-turbo-3.0.4-vc.exe`

### 步骤2：安装
1. 双击运行安装程序
2. 选择安装路径（推荐默认：`C:\libjpeg-turbo64`）
3. 勾选 "Add to PATH"（重要！）
4. 完成安装

### 步骤3：验证安装
打开PowerShell，运行：
```powershell
cd C:\libjpeg-turbo64\bin
dir *.dll
```

应该看到：
- `turbojpeg.dll` ✅

### 步骤4：添加到PATH（如果安装时未勾选）
```powershell
# 临时添加（本次会话有效）
$env:PATH += ";C:\libjpeg-turbo64\bin"

# 永久添加（需要管理员权限）
[System.Environment]::SetEnvironmentVariable("PATH", $env:PATH + ";C:\libjpeg-turbo64\bin", [System.EnvironmentVariableTarget]::Machine)
```

---

## 方法二：通过Conda安装（如果使用Anaconda/Miniconda）

```bash
conda install -c conda-forge libjpeg-turbo
```

---

## 方法三：手动复制DLL到项目目录（快速方法）

### 步骤1：下载预编译DLL
从官方Release下载zip包：
https://github.com/libjpeg-turbo/libjpeg-turbo/releases

解压后找到 `bin\turbojpeg.dll`

### 步骤2：复制到项目
将 `turbojpeg.dll` 复制到以下任一位置：
1. `picacg-qttext\src\` 目录（推荐）
2. `C:\Windows\System32\` （需要管理员权限）
3. Python安装目录（例如 `C:\Python312\`）

---

## 验证安装是否成功

运行验证脚本：
```bash
cd src
python tools/io_optimizer.py
```

**成功标志**：
```
[IOOptimizer] ✅ libjpeg-turbo加速: 已启用（3-5倍编解码提升）⚡⚡⚡
```

**失败标志**：
```
[IOOptimizer] ⚠️  libjpeg-turbo未安装，使用标准编解码
```

---

## 常见问题

### Q1: 提示"找不到turbojpeg.dll"
**解决方案**：
1. 确认安装路径正确
2. 检查PATH环境变量：`echo $env:PATH`
3. 重启PowerShell或IDE

### Q2: Python能import turbojpeg但报错
**解决方案**：
检查Python位数和libjpeg-turbo位数是否匹配：
```powershell
python -c "import platform; print(platform.architecture())"
# 输出 ('64bit', ...) → 需要64位libjpeg-turbo
# 输出 ('32bit', ...) → 需要32位libjpeg-turbo
```

### Q3: 在虚拟环境中无法使用
**解决方案**：
将 `turbojpeg.dll` 复制到虚拟环境的 `Scripts\` 目录

---

## 性能对比

安装前后性能对比（1500x1200图像）：

| 操作 | 无TurboJPEG | 有TurboJPEG | 提升 |
|------|-------------|-------------|------|
| JPEG编码 | ~90ms | ~20-30ms | **3-4倍** ⚡⚡⚡ |
| JPEG解码 | ~10-15ms | ~3-5ms | **2-3倍** ⚡⚡ |

漫画阅读体验提升：
- 翻页响应更快
- CPU占用降低
- 电池续航增加

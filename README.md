# Bilibili KDE Plasma / Breeze 桌面客户端

[English Documentation](README_EN.md) | [中文说明](README.md)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.13](https://img.shields.io/badge/Python-3.13-brightgreen.svg)](https://www.python.org/)
[![Qt6 / PySide6](https://img.shields.io/badge/Qt-6.11-blueviolet.svg)](https://www.qt.io/)
[![KDE Breeze](https://img.shields.io/badge/UI-KDE%20Breeze%20Dark-informational.svg)](https://kde.org/)

基于 Python 3.13 与 Qt6 (PySide6) 构建的专业级 Bilibili 桌面客户端。界面与交互严格对齐 **KDE Plasma 6 / Breeze** 视觉风格，具备**全键盘操作优先 (Keyboard-First)**、**多身份上下文状态继承**、**被动式零开销本地数据归档 (Passive Archiving)**、**健壮容错评论树**、**真实视频流硬件加速解码**、以及**双向拖拽视口与独立画中画弹窗**。

---

## 📸 运行界面预览 (Screenshots)

### 1. 主播放视口与推荐列表 (Main Window & Recommendations)
> 遵循 KDE Breeze Dark 调色板，支持原生硬件加速视频解码、高性能弹幕图层渲染、标准 40 项推荐卡片、以及健壮评论树。

![主播放器与界面总览](assets/screenshots/01_main_player_breeze.png)

### 2. 独立弹窗 / 画中画播放模式 (Detached Pop-out Window & PiP)
> 点击控制条上的 `⧉ 独立窗口` 即可将播放器瞬间脱离为主窗口，支持自由拖动拉伸尺寸、副屏放置、以及 `📌 窗口置顶 (Always on Top)`。

![独立弹窗与画中画模式](assets/screenshots/02_detached_pip_window.png)

### 3. UP 主主页深度视图：本地多身份关注矩阵 (Multi-Identity Follow Matrix)
> 聚合展示本地所有登录身份对该 UP 主的关注状态与精确到秒的关注时间戳，支持各身份独立切换关注。

![本地多身份关注深度矩阵](assets/screenshots/03_multi_identity_matrix.png)

### 4. 被动式本地数据归档检查器 (Passive Archive SQLite Inspector)
> 零额外网络请求原则：被动嗅探网络响应并异步入库 SQLite，实时记录视频元数据、时序动态变动（点赞/投币/收藏）与全量评论。

![被动数据归档库检查器](assets/screenshots/04_passive_archive_inspector.png)

### 5. 多账号身份管理器与 Cookie 导入 (Account Manager Dialog)
> 严格遵循“默认值语义”，支持通过 `SESSDATA` / Cookie 快速导入，实现操作身份隔离与页面路由身份继承。

![多账号管理与SESSDATA导入](assets/screenshots/05_account_manager_dialog.png)

### 6. 全键盘快捷键帮助手册 (Keyboard Navigation Reference)
> 随时按 `?` 或 `F1` 呼出完整的 Vim-like 键位与 Tab 网格焦点导航指南。

![全键盘快捷键指南](assets/screenshots/06_keyboard_shortcuts_help.png)

---

## ✨ 核心特性

1. **原生音视频硬解与防盗链流代理 (`LocalStreamProxy`)**
   - 集成 Qt6 原生 `QMediaPlayer` + `QAudioOutput` + `QVideoWidget`，依托内置 **FFmpeg 7.1.5** 引擎，支持 H.264、HEVC、AAC 硬解与立体声音频输出。
   - 内置轻量级本地流媒体反向代理，自动注入 `Referer: https://www.bilibili.com` 彻底解决 B 站 CDN 的 HTTP 403 防盗链风控问题，并支持 HTTP 206 断点续传拖拽无感加载。

2. **视口双向自由拖拽与独立弹窗播放**
   - **水平分割线 (QSplitter)**：可左右拖拽调整播放视口与 40 项推荐列表的宽度分配。
   - **垂直分割线 (QSplitter)**：可上下拉伸调节视频画面高度，兼顾沉浸观影与评论浏览。
   - **`⧉ 独立窗口`**：一键生成独立桌面原生弹窗，支持窗口置顶、跨屏移动，关闭后自动无缝回嵌主窗口，播放完全不中断。

3. **被动式零开销本地数据归档 (Passive Archiving)**
   - **零额外网络请求原则**：所有数据落盘均在客户端响应拦截层被动截获，严禁为了归档单独发起重复请求。
   - 支持通过 `config.yaml` 灵活配置路径模板：`{aid}`, `{bvid}`, `{cid}`, `{upid}`, `{title}`, `{timestamp}` 等。
   - 包含视频元数据库、时序变动 log 表（点赞/投币/收藏随时间变动曲线）、全量评论流、以及被动视频流分片存储。

4. **多身份与上下文状态继承 (Context Identity Inheritance)**
   - 页面路由跳转时，新页面默认自动继承前一页面的活跃操作身份。
   - 支持独立操作身份隔离：发送评论、弹幕、点赞投币或关注时，可独立指定特定账户执行。
   - 实时关注监听：关注 UP 主后自动触发问候留言弹窗，遵循默认值语义预设焦点。

5. **健壮容错评论树 (Robust Comment Tree)**
   - 扁平数据重构为深层嵌套树形视图。
   - **孤儿节点优雅 Fallback**：若父评论被删除或屏蔽，系统自动挂载占位保护父节点并展示 `[原评论已失效]` 徽标，杜绝界面崩溃或渲染中断。

6. **多层弹幕渲染引擎**
   - 支持滚动弹幕、顶端固定、底端固定弹幕，具备高对比度描边抗锯齿渲染。
   - 完整支持 Mode 7 高级 2D/3D 代码弹幕空间插值运算与旋转透明度变化。
   - 完整解析 BAS (Bilibili Advanced Script) 动态脚本弹幕。

---

## ⌨ 全键盘导航速查表 (随时按 `?` 或 `F1` 呼出)

| 按键 | 模式 / 作用域 | 功能说明 |
| :--- | :--- | :--- |
| `j` / `Down` | 列表 / 视口 | 向下滚动评论或推荐视频列表 |
| `k` / `Up` | 列表 / 视口 | 向上滚动评论或推荐视频列表 |
| `h` / `Left` | 主面板网格 | 向左切换网格焦点 (播放器 / 侧边) |
| `l` / `Right` | 主面板网格 | 向右切换网格焦点 (播放器 / 推荐与评论) |
| `g` | 滚动区域 | 一键跳转至顶部 (Home) |
| `G` (Shift+g) | 滚动区域 | 一键跳转至底部 (End) |
| `Space` | 播放器 | 播放 / 暂停视频 |
| `f` | 播放器 | 切换全屏状态 |
| `d` | 弹幕引擎 | 开启 / 关闭弹幕渲染 (包含普通/高级/BAS) |
| `c` | 交互系统 | **立即跳转至评论输入框并进入编辑态** |
| `u` | 身份上下文 | **跳转至当前 UP 主空间 (查看多身份关注矩阵)** |
| `a` | 多身份系统 | 弹出多账号管理弹窗 (Cookie 快速导入) |
| `p` | 归档系统 | 打开本地被动数据归档库 (SQLite Inspector) |
| `/` 或 `Ctrl+K` | 全局指令 | 呼出 KRunner 风格快速指令面板 |
| `Esc` | 全局 | 退出编辑模式、关闭弹窗、或返回上一层级 |

---

## 📦 快速开始与运行

### 方式 A：直接运行打包好的 Windows 可执行文件 (推荐)

仓库 `dist/` 目录下提供了预编译的 Windows 可执行二进制：
- **单文件独立便携版**：`dist/BilibiliPlasma-Standalone.exe` (双击即开即用，内嵌所有解码依赖)
- **目录解包极速版**：`dist/BilibiliPlasma/BilibiliPlasma.exe` (同级包含外部 `config.yaml` 配置文件)

### 方式 B：从源码运行

```powershell
# 1. 克隆项目
git clone https://github.com/<your-username>/bilibili-plasma-desktop.git
cd bilibili-plasma-desktop

# 2. 安装依赖
pip install -r requirements.txt

# 3. 启动应用
python main.py

# 可选参数
python main.py --bvid BV1xx411c7mD   # 指定初始视频
python main.py --offline             # 离线容灾模拟模式
python main.py --test-run            # CI 自动化健康测试
```

---

## 🧪 单元测试

项目内置完整的单元测试集（覆盖评论树孤儿容错、被动网络拦截 SQLite 存储、多身份状态机继承、BAS 弹幕解析）：

```powershell
python -m unittest discover tests
```

*测试输出：12 项测试全部通过 (OK)。*

---

## 📄 开源许可协议 (License)

本项目采用宽松的 [MIT License](LICENSE) 许可协议开源。您可以自由修改、商业使用、分发和再许可。

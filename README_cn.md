Vibe-coded with deepseek-v4-pro.

# Frameless — Krita Plugin

> [English version](README.md)

**不止是无边框——标题栏完全可自定义，还能把 Krita 原生工具栏直接塞进标题栏。** 去掉 Windows 原生标题栏后，你可以自由组合任意组件来构建自己的紧凑标题栏：文档名、菜单、弹性空白、窗口控制按钮，甚至 Krita 的 QToolBar——全部挤在同一行。标题栏空白区域可拖动窗口，双击切换最大化。

布局通过 `config.json` 驱动。首次运行时（或文件缺失/损坏时）会自动写盘一份模板 `config.json`，编辑后重启 Krita 即可。组件模块化——在 `components/` 下放一个新的 `.py` 文件并注册即可添加自定义组件。

**仅支持 Windows 10 / 11。** 其他操作系统不受影响（插件在加载时会静默跳过非 Windows 消息）。

![](image.png)

## 安装

参考 <https://github.com/naer-lily/krita-shortcut-fix>。**安装后需要手动重启**。

---

## 效果

```
原生 Krita：
┌─────────────────────────────────────────────┐
│  未命名.kra  —  Krita           ─  □  ✕  │  ← 原生标题栏
├─────────────────────────────────────────────┤
│  File  Edit  View  ...                      │  ← 菜单栏
├─────────────────────────────────────────────┤
│  画布内容                                    │
└─────────────────────────────────────────────┘

Frameless：
┌──────────────────────────────────────────────────┐
│  文档.kra  ☰  [画笔大小 ████]  [工具按钮]  ─  □  ✕  │  ← 自定义标题栏
├──────────────────────────────────────────────────┤
│  画布内容                                         │
└──────────────────────────────────────────────────┘
```

- 左侧显示当前文档名：从未保存过的文档显示 `Untitled`，有未保存修改时追加 `*`，无文档时整项隐藏
- 菜单可完整展示或缩为单个图标按钮（下拉展开），两种模式均保留 Alt+字母快捷键
- **Photoshop 式工具槽**——一个工具组一个按钮；单击激活，双击/右键换掉这个槽里的工具
- **Krita 原生工具栏可直接嵌入标题栏**——通过 `CustomToolBar` 组件，回收纵向屏幕空间
- 标题栏空白区域可拖动窗口，贴边时触发 Aero Snap（半屏/四分之一屏）
- 双击标题栏空白区域切换最大化/还原
- 标题栏高度随内容动态调整（如工具栏比菜单高时自动撑开）
- 布局可通过 `config.json` 配置——自由排序、增删组件

### 配置

编辑 `frameless/config.json` 自定义标题栏布局。
文件被删除或损坏后，下次启动会自动写回模板。

首次运行自动写入的模板如下（这里紧凑排版）：

```json
{
    "layout": [
        {"name": "Separator",       "config": {"width": 4}},
        {"name": "OriginalMenuBar", "config": {"compact": true}},
        {"name": "CurrentFileName", "config": {"poll_ms": 200}},
        {"name": "ToolSlot", "config": {"id": "brush",  "tools": ["KritaShape/KisToolBrush"]}},
        {"name": "ToolSlot", "config": {"id": "select", "tools": ["KisToolSelectOutline", "KisToolSelectElliptical", "KisToolSelectRectangular", "KisToolSelectPolygonal", "KisToolSelectSimilar", "KisToolSelectMagnetic"]}},
        {"name": "ToolSlot", "config": {"id": "shape",  "tools": ["KisToolPolyline", "KritaShape/KisToolLine", "KritaShape/KisToolRectangle", "KritaShape/KisToolEllipse"]}},
        {"name": "ToolSlot", "config": {"id": "fill",   "tools": ["KritaFill/KisToolFill", "KritaFill/KisToolGradient", "KritaShape/KisToolLazyBrush"]}},
        {"name": "ToolSlot", "config": {"id": "misc",   "tools": ["ToolReferenceImages", "KisToolCrop", "KritaShape/KisToolMeasure", "KisAssistantTool", "SvgTextTool", "KritaSelected/KisToolColorSampler"]}},
        {"name": "Spacer",          "config": {"scale": 1}},
        {"name": "CustomToolBar",   "config": {"toolbar_name": "customToolBar2"}},
        {"name": "Spacer",          "config": {"scale": 1}},
        {"name": "WindowControl",   "config": {"button_width": 60, "close_hover_bg": "#E81123"}}
    ]
}
```

每一项必须有 `name`；`config` 可选，未知或非法值会回退到组件的默认值。
`name` 写错、`config` 类型不对或 JSON 语法错误，都会导致加载器用上面的模板
覆盖原文件——也就是说一个拼写错误就会丢掉你的自定义布局。

#### 内置组件

| 组件 | 用途 | 配置项 |
|------|------|--------|
| `CurrentFileName` | 显示当前文档路径；从未保存的文档显示 `Untitled`；有未保存修改时追加 `*`（取自 `Document.modified()`）；无文档时整项隐藏 | `poll_ms`（int，默认 200） |
| `OriginalMenuBar` | 迁移的原生 QMenuBar | `compact`（bool，默认 false）——缩为图标按钮下拉；`menu_label`（str）——按钮文字覆盖 |
| `Separator` | 固定宽度视觉分割 | `width`（int，像素，默认 8） |
| `Spacer` | 弹性空白，填满剩余空间 | `scale`（int，≥1，默认 1）——相对其他 Spacer 的比例 |
| `ToolSlot` | **Photoshop 式工具槽**——单击激活槽内工具，双击/右键更换；无文档时隐藏 | `tools`（**必填**，Krita 工具 id 列表）；`id`（str，持久化键）；`size`（int，像素）；`poll_ms`（int，默认 66）；`show_marker`（bool，默认 true）；`tooltip_hint`（str） |
| `CustomToolBar` | **将 Krita 原生 QToolBar 嵌入标题栏**——无文档时隐藏，重新打开文档后自动恢复 | `toolbar_name`（str，默认 `"customToolBar2"`）——任意 Krita 工具栏的 objectName |
| `WindowControl` | 最小化/最大化/关闭按钮 | `button_width`（int，像素，默认 60），`close_hover_bg`（CSS 颜色，默认 `"#E81123"`） |

#### 工具槽（`ToolSlot`）

一条 `ToolSlot` 配置 = 一个按钮 + 一组工具。背后没有任何分组魔法——
把几条 `ToolSlot` 挨着放，就是一个 Photoshop 式的堆叠工具栏（标题栏是横向的，
所以是一排）。

- 槽会**记住**自己当前持有的工具，列表里的第一个是初始工具。
- **单击**：激活它记住的工具。
- **双击**或**右键**：在鼠标位置弹出菜单，列出该槽的全部工具；选中某个会激活它，
  并且此后这个槽就一直是这个工具。（因此双击会先激活一次记住的工具再弹菜单，
  这是可接受的行为。）
- **只放一个工具的槽**等同于普通工具按钮：不弹菜单，也不显示三角。
- 没有打开任何文档时，整排槽（连同文档名）一起隐藏。
- 当前工具属于某个槽的列表时，该槽**高亮**并显示当前工具的图标。
  也就是说用键盘快捷键切工具，对应的槽会自动跟着变，与 Photoshop 一致。
- 右下角小三角表示该槽还藏着别的工具（`show_marker: false` 可关掉；
  只有一个工具的槽不会显示）。
- 选择结果持久化在 Krita 自己的配置里（`kritarc` 的 `[frameless]` 组，
  键名 `toolslot/<id>`），重启不丢，也绝不会改写 `config.json`。

Krita 的 Python API 没有"工具已切换"的信号，所以每个槽按 `poll_ms`
（默认 66ms）轮询当前工具。

**如何查工具 id。** 工具 id 就是 Krita 工具箱里那些按钮的 `objectName()`，
例如 `KritaShape/KisToolBrush`、`KritaFill/KisToolFill`、`KisToolSelectOutline`、
`SvgTextTool`。在 Krita 的 Scripter（工具 → 脚本 → Scripter）里粘贴：

```python
from PyQt5.QtWidgets import QToolButton
from krita import Krita

win = Krita.instance().activeWindow().qwindow()
for obj in win.findChildren(object):
    if obj.metaObject().className() == 'KoToolBox':
        for btn in obj.findChildren(QToolButton):
            if btn.objectName():
                print(repr(btn.objectName()), '|', btn.text())
```

`tools` 列表相同的两个槽会共用同一份记忆，想各自独立就显式写 `id`；
调整过列表顺序后也建议固定 `id`，否则记忆会重置。

#### 添加自己的组件

1. 新建 `components/your_component.py`，暴露
   `create(window, bar_h, config, ctx) -> QWidget`。
2. 在 `components/__init__.py` 的 `COMPONENT_REGISTRY` 中注册。
3. 在 `config.json` 里使用 `{"name": "YourComponent", "config": {...}}`。

在 `create` 中可以订阅 `ctx.palette_changed`、`ctx.window_state_changed`
和 `ctx.teardown`。定时器、事件过滤器、快捷键一定要在 `teardown` 里释放——
窗口重新打开时标题栏会被销毁重建。

---

## 技术实现概述

### 为什么不能用 `Qt.FramelessWindowHint`

Krita 使用 PyQt5。最"显然"的去标题栏方式是在 QMainWindow 上设置 `Qt.FramelessWindowHint`。

但在 Windows 上，这个标志会把底层 HWND 的窗口样式改成 `WS_POPUP`——这意味着 Windows **完全不再发送 `WM_NCHITTEST` 消息**。没有 `WM_NCHITTEST`，就无法在窗口边缘提供缩放光标，也无法实现边缘拖拽缩放。

### 正确做法：手动操作 Win32 窗口样式

我们的方案与 VS Code / Chrome / Electron 等应用的底层实现等价：

| 步骤 | 做什么 | 为什么 |
|------|--------|--------|
| 1. Win32 样式修改 | 去掉 `WS_CAPTION`（标题栏），保留 `WS_THICKFRAME`（边框） | `WS_THICKFRAME` 存在时 Windows 仍会发送 `WM_NCHITTEST`，边缘缩放和 Aero Snap 才能工作 |
| 2. DWM 框架扩展 | `DwmExtendFrameIntoClientArea(0, 1, 0, 0)` | 告诉桌面窗口管理器"我们在自定义窗口 chrome"，DWM 自动渲染阴影 |
| 3. `WM_NCCALCSIZE` | 返回 0 → 客户区 = 整个窗口 | `WS_THICKFRAME` 的边框变为不可见（0px 宽），窗口看起来无边框 |
| 4. `WM_NCHITTEST` | 窗口边缘 6px 返回 `HTLEFT`/`HTRIGHT` 等 | Windows 显示正确的缩放光标，并处理边缘拖拽 |
| 5. `WM_GETMINMAXINFO` | 设置最大化边界为显示器工作区（不含任务栏） | 最大化时不会覆盖任务栏 |

窗口处于最大化状态时 `WM_NCHITTEST` 直接返回 `False` / `0`，
那条不可见的缩放边框不会抢走最大化窗口上的点击。

### 拖动

在自定义 `_TitleBar` 控件上通过 `mousePressEvent`/`mouseMoveEvent` 处理拖拽。鼠标按下后**移动超过 5px** 才启动拖动（不在 press 时启动，以保留双击检测）。拖动本身通过 Qt 的 `QWindow.startSystemMove()` 实现，内部调用 `DefWindowProc(WM_SYSCOMMAND, SC_MOVE | HTCAPTION)`，自动触发 Aero Snap。

如果按下位置最深的子控件是 `QToolButton`（窗口控制按钮、紧凑模式的菜单按钮、
以及每一个 `ToolSlot`），则视为交互区域，不启动拖动。

### 标题栏架构

自定义标题栏作为原 QMenuBar 的 **TopLeftCorner 控件**，通过 Resize 事件过滤器强制撑满整个菜单栏宽度。在清空原菜单栏前，所有 QMenu 对象被提取并迁移到标题栏内的真正 `QMenuBar` 中——Alt+字母快捷键、hover 切换菜单、键盘导航全部保留。

由于标题栏是菜单栏的子控件，菜单栏会被设成相同的最小高度——否则比
（已被清空的）菜单栏更高的组件（例如默认 32px 的 `ToolSlot`）会被裁掉。

有两道保险维持这个位置：100ms 轮询会在 Krita 的 MDI 区域抢走 corner widget
时把它装回去（并隐藏可能被注入的 TopRightCorner 控件）；`windowClosed` 时
统一清理——移除事件过滤器、卸载原生事件过滤器、通过 `teardown` 通知组件。

组件通过共享的 `_ComponentContext`（信号总线）与标题栏通信：
`palette_changed`、`window_state_changed`、`teardown`。

### Krita 特定注意事项

Krita 的 Python API 中，`Window`、`View`、`Document` 等对象是**即用即弃的薄封装**——引用它们的 Python 对象随时可能被垃圾回收。不要在信号回调或异步代码里持有这些引用，而是缓存 `qwin.objectName()` 这类稳定的标识，需要时再通过 `Krita.instance().windows()` 重新取。菜单栏修改通过 `QTimer.singleShot(0)` 延迟执行以避免段错误，而 Win32 / DWM 样式修改必须同步执行，否则窗口会先闪一下原生标题栏。

另外注意 `Document.fileName()` 返回的是**完整路径**，不是文件名。

### 文件结构

```
frameless/
├── frameless.desktop                     # Krita 插件描述文件
├── frameless/
│   ├── __init__.py                       # Python 包入口
│   ├── FramelessExtension.py             # 主逻辑（Win32/DWM + 标题栏 + 入口）
│   ├── config.json                       # 布局配置（首次运行时自动生成）
│   ├── components/
│   │   ├── __init__.py                   # 组件注册表 + 配置加载器
│   │   ├── filename.py                   # CurrentFileName
│   │   ├── menubar.py                    # OriginalMenuBar
│   │   ├── separator.py                  # Separator（固定宽度分割）
│   │   ├── spacer.py                     # Spacer（比例弹性空白）
│   │   ├── tool_slot.py                  # ToolSlot（Photoshop 式工具槽）
│   │   ├── tool_source.py                # 工具查找 / 激活辅助
│   │   ├── toolbar.py                    # CustomToolBar
│   │   └── window_control.py             # WindowControl
│   ├── krita.pyi                         # Krita Python API 类型桩
│   └── Manual.html                       # Krita 插件帮助页
├── image.png                             # 截图
├── README.md                             # English version
└── README_cn.md                          # 本文件（中文）
```

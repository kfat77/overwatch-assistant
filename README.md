# 守望先锋辅助插件 Overwatch Assistant v2.1

一个为《守望先锋》设计的游戏辅助工具，**不注入游戏进程，使用屏幕截图+OCR+透明叠加层**，完全安全无封号风险。

## 功能亮点

### 1. 实时聊天翻译
- 自动识别聊天框中的 **英文** 和 **韩文** 消息
- 实时翻译为 **中文** 显示在叠加层上
- **Timeline 对齐去重** - 基于消息顺序位置去重，避免 OCR 抖动导致的重复翻译
- **多帧共识** - 新消息需连续两帧一致才确认，提高准确率
- **韩语 Jamo 级相似度** - 专门处理韩语 OCR 抖动和空格缺失问题

### 2. 智能捕获系统
- **像素差分巡逻** - 画面稳定时不跑 OCR，节省 70% CPU
- **文字存在检测门** - 快速边缘检测判断是否有文字
- **突发 OCR 模式** - 检测到聊天变化后进入高频捕获，结束后自动降频

### 3. 英雄推荐系统
- 根据队友已选英雄推荐最适合的阵容搭配
- 分析阵容完整性（重装/输出/支援数量）
- 基于英雄协同关系给出推荐（如 法老之鹰+天使）
- 支持克制关系分析

### 4. OW 聊天代码（参考 MapleOAO/chat-editor）
- **预设模板快速发送** - GG、感谢、需要治疗、集合等一键发送
- **颜色代码支持** - `<FGRRGGBBAA>` 格式的 OW 聊天颜色代码
- **渐变效果** - 可生成渐变色聊天文本
- 模板代码自动复制到剪贴板，游戏中直接粘贴

### 5. 回话功能
- 中文 → 英/韩/日 翻译
- 自动复制到剪贴板
- 支持 OW 颜色代码增强

### 6. 增强型叠加层
- **历史消息滚动** - 鼠标滚轮查看历史翻译
- **鼠标穿透** - 点击穿透到游戏，不遮挡操作
- **拖动缩放** - 标题栏拖拽移动窗口
- **回话输入栏** - 底部快速输入并翻译
- **模板按钮** - 一键发送常用 OW 聊天模板

## 技术方案

```
┌─────────────────────────────────────────────────────────┐
│                      守望先锋游戏画面                       │
│  ┌─────────────────┐                                    │
│  │   聊天框区域     │  ←── 智能捕获 ──→ OCR ──→ Timeline │
│  └─────────────────┘           │          对齐 ──→ 翻译  │
│  ┌──────────────────────────────┐                      │
│  │        英雄选择界面            │  ←── 模板匹配/手动输入   │
│  └──────────────────────────────┘                      │
└─────────────────────────────────────────────────────────┘
                           │
                    ┌──────▼──────┐
                    │  透明叠加层   │  ←── 显示翻译 + 回话 + 模板
                    └─────────────┘
```

### 为什么安全？
- **零注入**：不读取游戏内存，不使用 DLL 注入
- **纯截图**：仅使用 Windows API 截取屏幕画面
- **透明窗口**：使用操作系统标准窗口 API 显示叠加层
- **不修改游戏**：不修改任何游戏文件或数据

## 安装

### 前置要求
- Python 3.11+（推荐 3.11.9，已测试）
- Windows 10/11
- [Tesseract-OCR](https://github.com/UB-Mannheim/tesseract/releases)（OCR 识别引擎）

### 安装依赖

```bash
# 克隆或下载项目
cd overwatch-assistant

# 创建虚拟环境（推荐）
python -m venv venv
venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 安装 Tesseract-OCR（必须）
# 下载地址: https://github.com/UB-Mannheim/tesseract/releases
# 下载 tesseract-ocr-w64-setup-5.5.0.20241217.exe
# 双击安装，默认路径即可
```

### 依赖列表

| 包 | 用途 |
|------|------|
| Pillow | 图像处理 |
| numpy | 数值计算 |
| opencv-python | 图像识别 |
| pytesseract | OCR 接口 |
| easyocr | 备选 OCR 引擎（韩文更好） |
| translators | 翻译引擎 |
| keyboard | 全局热键 |
| pyperclip | 剪贴板操作 |

## 使用指南

### 启动程序

```bash
python main.py
```

### 首次使用步骤

1. **启动守望先锋**，进入训练靶场或等待大厅
2. **按 F11**，拖拽选择聊天框区域
3. **按 F10**，开始聊天翻译
4. **按 F9**，显示/隐藏叠加层

### 英雄推荐使用

1. 进入英雄选择界面
2. **按 F12** 选择英雄选择区域（或手动输入阵容）
3. 程序会自动分析队友阵容并显示推荐

### 回话功能

1. 在叠加层底部输入中文
2. 选择目标语言（英/韩/日）
3. 按回车发送，译文自动复制到剪贴板
4. 游戏中按 Ctrl+V 粘贴

### 模板快速发送

点击叠加层标题栏的 📝 按钮，选择预设模板：
- **GG** - 绿色 "GG WP!"
- **感谢** - 绿色 "Thanks! You're awesome!"
- **需要治疗** - 红色 "Need healing!"
- **集合** - 黄色 "Group up!"
- **大招好了** - 绿色 "My ULT is ready!"
- **推进** - 蓝色 "Push!"
- **集火** - 红色+黄色 "Focus fire!"
- **漂亮** - 绿色 "Nice! Great play!"
- **后退** - 红色 "Fall back!"
- **祝好运** - 绿色 "GL HF!"

模板自动转换为 OW 颜色代码并复制到剪贴板，游戏中直接粘贴即可。

### 热键列表

| 热键 | 功能 |
|------|------|
| `F9` | 显示/隐藏叠加层 |
| `F10` | 开始/停止聊天翻译 |
| `F11` | 选择聊天框区域 |
| `F12` | 选择英雄选择区域 |
| `Ctrl+Shift+Q` | 退出程序 |

## 配置

编辑 `config.py` 调整以下设置：

```python
# 翻译设置
target_language = "zh"      # 目标语言
translation_engine = "bing"  # 翻译引擎（国内可用）

# 叠加层设置
overlay_opacity = 0.85      # 透明度
overlay_position = (50, 50) # 窗口位置
message_ttl = 15.0          # 消息停留时间（秒）

# OCR设置
ocr_engine = "tesseract"    # OCR引擎（tesseract/easyocr）
ocr_languages = ['en', 'ko'] # 识别语言

# 智能捕获
idle_interval = 2.0         # 空闲期检查间隔（秒）
burst_interval = 0.2          # 突发期 OCR 间隔（秒）
```

## 项目结构

```
overwatch-assistant/
├── main.py                    # 主程序入口
├── config.py                  # 配置文件 + 英雄数据
├── requirements.txt           # 依赖列表
├── README.md                  # 本文件
├── core/                      # 核心模块
│   ├── capture.py            # 屏幕截图
│   ├── smart_capture.py     # 智能捕获（像素差分+文字检测）
│   ├── ocr_engine.py         # OCR文字识别
│   ├── translator.py         # 翻译引擎
│   ├── timeline.py           # Timeline对齐 + OW解析器 + 多帧共识
│   ├── korean_jamo.py        # 韩语 Jamo 级相似度匹配
│   ├── overlay.py            # 透明叠加层（滚动+穿透+回话+模板）
│   ├── hero_recommender.py   # 英雄推荐系统
│   ├── hero_detector.py      # 英雄检测
│   ├── glossary_service.py   # 游戏术语表服务
│   ├── reply_assistant.py    # 回话翻译 + OW颜色代码
│   └── chat_codes.py         # OW 聊天代码生成器（参考 MapleOAO）
├── utils/                     # 工具模块
│   └── region_selector.py    # 区域选择器
├── assets/                    # 资源文件
│   ├── heroes/              # 英雄头像模板
│   └── glossary.json         # 游戏术语表（300+条）
└── .github/                   # GitHub 配置
    ├── workflows/            # CI 工作流
    ├── ISSUE_TEMPLATE/       # Issue 模板
    └── pull_request_template.md
```

## 参考项目

本项目参考了以下开源项目的核心设计：

| 项目 | 技术栈 | 贡献 |
|------|--------|------|
| [reverieach/ow-translate-lite](https://github.com/reverieach/ow-translate-lite) | C# .NET 9 + WPF | Timeline 对齐去重、像素差分巡逻、韩语 Jamo 匹配、多帧共识 |
| [MapleOAO/overwatch-chat-editor](https://github.com/MapleOAO/overwatch-chat-editor) | Next.js + React + TS | OW 聊天颜色代码格式 `<FGRRGGBBAA>`、纹理代码 `<TXC...>`、模板系统 |

## 常见问题

### Q: 为什么识别不出文字？
A: 请确保：
1. 正确选择了聊天框区域（F11）
2. 聊天框文字清晰可见
3. Tesseract-OCR 已正确安装

### Q: 翻译速度很慢？
A: 
- 降低截图频率：修改 `idle_interval = 2.0`
- 使用更快的翻译引擎
- 确保网络连接正常

### Q: 叠加层被游戏覆盖？
A: 
- 尝试以管理员身份运行程序
- 在游戏设置中使用"窗口化全屏"模式
- 右键点击叠加层选择"置顶"

### Q: 如何添加更多语言？
A: 修改 `config.py` 中的 `ocr_languages`：
```python
# 日文
ocr_languages = ['en', 'ko', 'ja']
```

### Q: 模板发送后游戏中显示乱码？
A: OW 颜色代码需要游戏支持。如果游戏中不支持，叠加层会显示纯文本版本。

## 注意事项

1. **本工具仅读取屏幕像素，不注入游戏进程**
2. **建议在非排位模式中先测试功能**
3. **叠加层窗口可能被某些全屏游戏覆盖**，建议使用窗口化全屏模式
4. **OCR 识别率受分辨率、字体、背景影响**，可能需要调整截图区域

## 更新日志

### v2.1 (2025-07)
- 集成 [MapleOAO/overwatch-chat-editor](https://github.com/MapleOAO/overwatch-chat-editor) 的 OW 聊天代码格式
- 添加预设模板快速发送功能（10 个常用模板）
- 回话功能支持 OW 颜色代码
- 修复 timeline 导入循环问题

### v2.0 (2025-07)
- 集成 [reverieach/ow-translate-lite](https://github.com/reverieach/ow-translate-lite) 核心算法
- 添加 Timeline 对齐去重系统
- 添加像素差分巡逻 + 文字存在检测（节省 70% CPU）
- 添加韩语 Jamo 级相似度匹配
- 添加多帧共识机制
- 添加 OW 术语表（300+ 条）
- 添加回话功能（中文→英/韩/日）
- 叠加层支持历史滚动、鼠标穿透、回话栏

### v1.0 (2025-07)
- 初始版本：实时聊天翻译 + 英雄推荐

## License

MIT License

## 免责声明

本工具仅供学习交流使用。请遵守暴雪最终用户许可协议(EULA)。开发者不对因使用本工具导致的任何账号问题负责。

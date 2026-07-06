"""
Overwatch Assistant - Configuration Module
守望先锋辅助插件 - 配置文件

@author: Overwatch Assistant Team
@date: 2025
"""

import os
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional


# ============================================================
# 核心配置
# ============================================================

@dataclass
class AppConfig:
    """应用主配置"""
    app_name: str = "守望先锋辅助插件 Overwatch Assistant"
    version: str = "2.1.0"
    debug: bool = False
    
    # 热键配置
    hotkey_toggle_overlay: str = "f9"           # 显示/隐藏叠加层
    hotkey_toggle_capture: str = "f10"          # 开始/停止捕获
    hotkey_select_chat_region: str = "f11"      # 选择聊天框区域
    hotkey_select_hero_region: str = "f12"      # 选择英雄选择区域
    hotkey_exit: str = "ctrl+shift+q"           # 退出程序


@dataclass
class CaptureConfig:
    """屏幕捕获配置"""
    # 聊天框默认区域 (1920x1080 分辨率下的默认位置)
    # 用户可以通过 F11 重新选择
    chat_region: Optional[Tuple[int, int, int, int]] = None
    
    # 英雄选择区域 (队伍面板)
    hero_select_region: Optional[Tuple[int, int, int, int]] = None
    
    # 截图帧率 (FPS)
    capture_fps: float = 5.0
    
    # 捕获间隔 (秒)
    capture_interval: float = 0.2
    
    # 图像质量
    image_quality: int = 85
    
    # 默认分辨率参考 (用于区域缩放)
    base_resolution: Tuple[int, int] = (1920, 1080)


@dataclass
class OCRConfig:
    """OCR 文字识别配置"""
    # OCR 引擎选择: "easyocr" (推荐) 或 "tesseract"
    engine: str = "tesseract"
    
    # 识别的语言: 英文 + 韩文
    # EasyOCR: ['en', 'ko']
    # Tesseract: 'eng+kor'
    languages: List[str] = field(default_factory=lambda: ['en', 'ko'])
    tesseract_lang: str = 'eng+kor'
    
    # 置信度阈值 (低于此值的识别结果将被忽略)
    confidence_threshold: float = 0.3
    
    # 预处理增强
    enable_preprocessing: bool = True
    
    # 对比度增强系数
    contrast_alpha: float = 1.5
    
    # 二值化阈值
    binary_threshold: int = 150
    
    # 缓存最大大小
    cache_max_size: int = 500


@dataclass
class TranslateConfig:
    """翻译配置"""
    # 目标语言
    target_language: str = "zh"  # 中文
    
    # 源语言自动检测
    auto_detect: bool = True
    
    # 翻译引擎: "google", "bing", "baidu"
    engine: str = "bing"
    
    # 翻译结果最大长度
    max_translation_length: int = 200
    
    # 缓存翻译结果 (避免重复翻译)
    enable_cache: bool = True
    cache_max_size: int = 500


@dataclass  
class OverlayConfig:
    """叠加层显示配置"""
    # 窗口位置
    position_x: int = 50
    position_y: int = 50
    
    # 窗口尺寸
    width: int = 500
    height: int = 300
    
    # 背景透明度 (0-1)
    opacity: float = 0.85
    
    # 背景颜色 (RGBA)
    bg_color: Tuple[int, int, int, int] = (20, 20, 30, 220)
    
    # 文字颜色
    text_color: str = "#00ff88"       # 翻译结果
    original_color: str = "#aaaaaa"   # 原文
    header_color: str = "#ffaa00"     # 标题
    
    # 字体
    font_family: str = "Microsoft YaHei"
    font_size: int = 12
    
    # 最大显示消息数
    max_messages: int = 20
    
    # 消息停留时间 (秒), 0 = 永久
    message_ttl: float = 15.0
    
    # 始终置顶
    always_on_top: bool = True
    
    # 允许拖拽移动
    draggable: bool = True


# ============================================================
# 英雄数据
# ============================================================

# 守望先锋英雄列表 (按职责分类)
HEROES_BY_ROLE = {
    "tank": [
        "D.Va", "Doomfist", "Hazard", "Junker Queen", "Mauga",
        "Orisa", "Ramattra", "Reinhardt", "Roadhog", "Sigma",
        "Winston", "Wrecking Ball", "Zarya"
    ],
    "damage": [
        "Ashe", "Bastion", "Cassidy", "Echo", "Freja", "Genji",
        "Hanzo", "Junkrat", "Mei", "Pharah", "Reaper", "Sojourn",
        "Soldier: 76", "Sombra", "Symmetra", "Torbjörn", "Tracer",
        "Venture", "Widowmaker"
    ],
    "support": [
        "Ana", "Baptiste", "Brigitte", "Illari", "Juno", "Kiriko",
        "Lifeweaver", "Lúcio", "Mercy", "Moira", "Zenyatta"
    ]
}

# 扁平化英雄列表
ALL_HEROES = []
for role, heroes in HEROES_BY_ROLE.items():
    ALL_HEROES.extend(heroes)

# 英雄中文名映射
HERO_NAME_CN = {
    # 重装
    "D.Va": "D.Va", "Doomfist": "末日铁拳", "Hazard": "哈扎德",
    "Junker Queen": "渣客女王", "Mauga": "毛加", "Orisa": "奥丽莎",
    "Ramattra": "拉玛刹", "Reinhardt": "莱因哈特", "Roadhog": "路霸",
    "Sigma": "西格玛", "Winston": "温斯顿", "Wrecking Ball": "破坏球",
    "Zarya": "查莉娅",
    # 输出
    "Ashe": "艾什", "Bastion": "堡垒", "Cassidy": "卡西迪",
    "Echo": "回声", "Freja": "弗蕾娅", "Genji": "源氏",
    "Hanzo": "半藏", "Junkrat": "狂鼠", "Mei": "美",
    "Pharah": "法老之鹰", "Reaper": "死神", "Sojourn": "索杰恩",
    "Soldier: 76": "士兵:76", "Sombra": "黑影", "Symmetra": "秩序之光",
    "Torbjörn": "托比昂", "Tracer": "猎空", "Venture": "探奇",
    "Widowmaker": "黑百合",
    # 支援
    "Ana": "安娜", "Baptiste": "巴蒂斯特", "Brigitte": "布丽吉塔",
    "Illari": "伊拉锐", "Juno": "朱诺", "Kiriko": "雾子",
    "Lifeweaver": "生命之梭", "Lúcio": "卢西奥", "Mercy": "天使",
    "Moira": "莫伊拉", "Zenyatta": "禅雅塔"
}

# ============================================================
# 英雄推荐策略数据
# ============================================================

@dataclass
class TeamComp:
    """团队阵容配置"""
    name: str
    name_cn: str
    description: str
    required_tank: List[str] = field(default_factory=list)
    required_dps: List[str] = field(default_factory=list)
    required_support: List[str] = field(default_factory=list)
    synergies: List[str] = field(default_factory=list)  # 协同英雄
    counters: List[str] = field(default_factory=list)   # 克制英雄


# 常见阵容推荐
TEAM_COMPOSITIONS = [
    TeamComp(
        name="Dive",
        name_cn="放狗阵",
        description="高机动性阵容，快速切入击杀后排",
        required_tank=["Winston", "D.Va", "Wrecking Ball"],
        required_dps=["Genji", "Tracer", "Sombra", "Echo"],
        required_support=["Lúcio", "Kiriko", "Mercy", "Zenyatta"],
        synergies=["Genji+Zenyatta", "Tracer+Winston", "Echo+Mercy"],
        counters=["Brigitte", "Moira", "Reaper", "Mei"]
    ),
    TeamComp(
        name="Brawl",
        name_cn="地推阵", 
        description="近距离作战阵容，正面推进",
        required_tank=["Reinhardt", "Roadhog", "Junker Queen", "Ramattra"],
        required_dps=["Reaper", "Mei", "Cassidy", "Torbjörn", "Soldier: 76"],
        required_support=["Lúcio", "Brigitte", "Baptiste", "Moira"],
        synergies=["Reinhardt+Reaper", "Roadhog+Ana", "Junker Queen+Kiriko"],
        counters=["Pharah", "Echo", "Widowmaker", "Ashe"]
    ),
    TeamComp(
        name="Poke",
        name_cn="消耗阵",
        description="长距离消耗阵容，控制高地和视野",
        required_tank=["Sigma", "Orisa", "Hazard"],
        required_dps=["Widowmaker", "Ashe", "Hanzo", "Sojourn", "Soldier: 76"],
        required_support=["Ana", "Baptiste", "Zenyatta", "Mercy"],
        synergies=["Sigma+Ana", "Orisa+Sojourn", "Widowmaker+Mercy"],
        counters=["Genji", "Tracer", "Winston", "D.Va"]
    ),
    TeamComp(
        name="Spam",
        name_cn=" poke/Spam",
        description="持续火力压制，逼迫敌人位移",
        required_tank=["Sigma", "Orisa", "Zarya"],
        required_dps=["Junkrat", "Pharah", "Torbjörn", "Symmetra"],
        required_support=["Baptiste", "Mercy", "Ana"],
        synergies=["Pharah+Mercy", "Junkrat+Orisa"],
        counters=["Widowmaker", "Ashe", "Soldier: 76"]
    ),
    TeamComp(
        name="Rush",
        name_cn="冲脸阵",
        description="极速突进，打乱敌方阵型",
        required_tank=["Winston", "D.Va", "Wrecking Ball"],
        required_dps=["Reaper", "Mei", "Genji", "Tracer"],
        required_support=["Lúcio", "Kiriko", "Moira"],
        synergies=["Winston+Reaper", "Lúcio+任何突进"],
        counters=["Brigitte", "Cassidy", "Roadhog"]
    ),
]

# 英雄协同关系 (英雄 -> 推荐搭配的队友)
HERO_SYNERGIES: Dict[str, List[str]] = {
    "Pharah": ["Mercy", "Zenyatta", "Ana"],
    "Genji": ["Zenyatta", "Ana", "Lúcio", "Kiriko"],
    "Tracer": ["Winston", "D.Va", "Zenyatta", "Lúcio"],
    "Echo": ["Mercy", "Zenyatta", "Ana"],
    "Reaper": ["Lúcio", "Ana", "Winston", "Kiriko"],
    "Widowmaker": ["Mercy", "Zenyatta", "Sigma", "Orisa"],
    "Ashe": ["Mercy", "Zenyatta", "Sigma"],
    "Hanzo": ["Zenyatta", "Sigma", "Orisa"],
    "Sojourn": ["Mercy", "Kiriko", "Ana"],
    "Junkrat": ["Orisa", "Zarya", "Baptiste"],
    "Mei": ["Lúcio", "Ana", "Reinhardt"],
    "Cassidy": ["Ana", "Brigitte", "Baptiste"],
    "Soldier: 76": ["Ana", "Mercy", "Baptiste"],
    "Sombra": ["Tracer", "Genji", "Winston"],
    "Torbjörn": ["Sigma", "Orisa", "Brigitte"],
    "Symmetra": ["Sigma", "Winston", "Lúcio"],
    "Bastion": ["Mercy", "Baptiste", "Orisa"],
    
    "Winston": ["Genji", "Tracer", "Sombra", "Reaper", "Lúcio", "Kiriko"],
    "D.Va": ["Tracer", "Genji", "Sombra", "Mercy", "Kiriko"],
    "Reinhardt": ["Reaper", "Mei", "Lúcio", "Brigitte", "Baptiste"],
    "Orisa": ["Sojourn", "Junkrat", "Baptiste", "Mercy"],
    "Sigma": ["Widowmaker", "Ashe", "Ana", "Baptiste", "Soldier: 76"],
    "Roadhog": ["Ana", "Kiriko", "Baptiste", "Sojourn"],
    "Zarya": ["Genji", "Reaper", "Tracer", "Lúcio", "Kiriko"],
    "Wrecking Ball": ["Tracer", "Sombra", "Widowmaker", "Mercy"],
    "Junker Queen": ["Kiriko", "Lúcio", "Ana", "Reaper"],
    "Ramattra": ["Lúcio", "Kiriko", "Baptiste", "Reaper", "Mei"],
    "Doomfist": ["Ana", "Kiriko", "Sombra", "Echo"],
    "Mauga": ["Baptiste", "Kiriko", "Ana", "Reaper"],
    
    "Mercy": ["Pharah", "Echo", "Ashe", "Widowmaker", "Sojourn", "Soldier: 76"],
    "Zenyatta": ["Genji", "Tracer", "Hanzo", "Widowmaker", "Ashe"],
    "Ana": ["Genji", "Reaper", "Roadhog", "Sigma", "Cassidy", "Soldier: 76"],
    "Lúcio": ["Winston", "Reinhardt", "Reaper", "Genji", "Tracer", "Ramattra"],
    "Kiriko": ["Genji", "Reaper", "Sojourn", "Junker Queen", "Ramattra", "Roadhog"],
    "Brigitte": ["Reinhardt", "Tracer", "Genji", "Cassidy", "Torbjörn"],
    "Baptiste": ["Orisa", "Sigma", "Junkrat", "Roadhog", "Cassidy", "Bastion"],
    "Moira": ["Winston", "Reaper", "Genji", "Tracer"],
    "Illari": ["Orisa", "Sigma", "Soldier: 76", "Cassidy"],
    "Juno": ["D.Va", "Winston", "Pharah", "Echo"],
    "Lifeweaver": ["Genji", "Tracer", "Pharah", "Winston"],
}

# 英雄克制关系 (英雄 -> 被谁克制)
HERO_COUNTERS: Dict[str, List[str]] = {
    "Pharah": ["Widowmaker", "Ashe", "Soldier: 76", "Sojourn", "D.Va", "Cassidy"],
    "Genji": ["Winston", "Zarya", "Symmetra", "Moira", "Brigitte"],
    "Tracer": ["Winston", "Brigitte", "Torbjörn", "Symmetra", "Mei"],
    "Widowmaker": ["Winston", "D.Va", "Genji", "Tracer", "Sombra", "Hazard"],
    "Mercy": ["Winston", "D.Va", "Genji", "Tracer", "Sombra"],
    "Reinhardt": ["Orisa", "Sigma", "Junkrat", "Pharah", "Mei", "Symmetra"],
    "Winston": ["Roadhog", "Reaper", "Bastion", "Brigitte", "Mei"],
    "Ana": ["Genji", "Tracer", "Sombra", "Winston", "Doomfist"],
    "Zenyatta": ["Genji", "Tracer", "Sombra", "Winston"],
    "Bastion": ["Genji", "Tracer", "Sombra", "Doomfist", "Hanzo"],
    "Reaper": ["Pharah", "Echo", "Ashe", "Widowmaker", "Mei"],
    "Hanzo": ["Winston", "D.Va", "Genji", "Tracer"],
    "Junkrat": ["Pharah", "Echo", "Widowmaker", "Ashe"],
    "Mei": ["Pharah", "Echo", "Widowmaker", "Ashe", "Reaper"],
    "Symmetra": ["Pharah", "Junkrat", "Widowmaker", "Ashe"],
    "Torbjörn": ["Pharah", "Junkrat", "Hanzo", "Sigma"],
    "Sombra": ["Winston", "Brigitte", "Torbjörn", "Hanzo"],
    "Doomfist": ["Orisa", "Roadhog", "Sigma", "Sombra", "Cassidy"],
}


# ============================================================
# 全局配置实例
# ============================================================

app_config = AppConfig()
capture_config = CaptureConfig()
ocr_config = OCRConfig()
translate_config = TranslateConfig()
overlay_config = OverlayConfig()


# 项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(PROJECT_ROOT, "assets")
HEROES_DIR = os.path.join(ASSETS_DIR, "heroes")

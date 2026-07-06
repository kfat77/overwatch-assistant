"""
Overwatch Assistant - Hero Detector Module
英雄检测模块

通过图像识别检测英雄选择界面中队友/敌方选择的英雄。
由于无法直接读取游戏内存，使用模板匹配和图像识别方案。
"""

import os
import time
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

try:
    import numpy as np
    import cv2
except ImportError:
    raise ImportError("请先安装 opencv-python: pip install opencv-python")

try:
    from PIL import Image
except ImportError:
    raise ImportError("请先安装 Pillow: pip install Pillow")

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import ALL_HEROES, HERO_NAME_CN, HEROES_DIR


@dataclass
class DetectedHero:
    """检测到的英雄"""
    name: str
    name_cn: str
    confidence: float
    position: Tuple[int, int, int, int]  # x, y, w, h
    is_friendly: bool = True  # True=队友, False=敌方


class HeroDetector:
    """英雄检测器"""
    
    # 守望先锋英雄选择界面布局参数 (基于 1920x1080)
    # 这些坐标需要根据实际游戏分辨率调整
    LAYOUT = {
        '1920x1080': {
            'friendly_slots': [
                (650, 180, 750, 280),   # 队友1
                (850, 180, 950, 280),   # 队友2
                (1050, 180, 1150, 280), # 队友3
                (1250, 180, 1350, 280), # 队友4
                (1450, 180, 1550, 280), # 队友5
            ],
            'enemy_slots': [
                (650, 500, 750, 600),
                (850, 500, 950, 600),
                (1050, 500, 1150, 600),
                (1250, 500, 1350, 600),
                (1450, 500, 1550, 600),
            ],
            'hero_select_icons': (50, 600, 1870, 1000),  # 底部英雄选择栏
        },
        '2560x1440': {
            'friendly_slots': [
                (860, 240, 1000, 360),
                (1130, 240, 1270, 360),
                (1400, 240, 1540, 360),
                (1670, 240, 1810, 360),
                (1940, 240, 2080, 360),
            ],
            'enemy_slots': [
                (860, 660, 1000, 780),
                (1130, 660, 1270, 780),
                (1400, 660, 1540, 780),
                (1670, 660, 1810, 780),
                (1940, 660, 2080, 780),
            ],
            'hero_select_icons': (70, 800, 2490, 1320),
        }
    }
    
    def __init__(self):
        self._templates: Dict[str, np.ndarray] = {}
        self._resolution: Tuple[int, int] = (1920, 1080)
        self._scale_factor: float = 1.0
        self._load_templates()
    
    def _load_templates(self) -> None:
        """加载英雄模板图像"""
        print("[英雄检测] 加载模板...")
        
        # 如果没有模板文件，创建占位符
        if not os.path.exists(HEROES_DIR):
            os.makedirs(HEROES_DIR)
            print(f"[英雄检测] 模板目录创建: {HEROES_DIR}")
            print("[英雄检测] 请将英雄头像截图放入该目录，文件名为英雄英文名.png")
        
        loaded = 0
        for hero in ALL_HEROES:
            # 尝试多种文件名格式
            possible_names = [
                f"{hero}.png",
                f"{hero}.jpg",
                f"{hero.replace(' ', '_')}.png",
                f"{hero.replace(':', '')}.png",
                f"{hero.lower()}.png",
            ]
            
            found = False
            for filename in possible_names:
                path = os.path.join(HEROES_DIR, filename)
                if os.path.exists(path):
                    try:
                        img = cv2.imread(path)
                        if img is not None:
                            self._templates[hero] = img
                            loaded += 1
                            found = True
                            break
                    except Exception as e:
                        print(f"[英雄检测] 加载模板失败 {filename}: {e}")
            
            if not found:
                # 尝试从英雄英文名提取
                pass
        
        print(f"[英雄检测] 已加载 {loaded}/{len(ALL_HEROES)} 个英雄模板")
        
        if loaded == 0:
            print("[英雄检测警告] 未加载任何模板，将使用颜色特征检测")
    
    def set_resolution(self, width: int, height: int) -> None:
        """设置游戏分辨率"""
        self._resolution = (width, height)
        base_w, base_h = 1920, 1080
        self._scale_factor = min(width / base_w, height / base_h)
    
    def _get_layout(self) -> Dict:
        """获取当前分辨率的布局配置"""
        key = f"{self._resolution[0]}x{self._resolution[1]}"
        if key in self.LAYOUT:
            return self.LAYOUT[key]
        
        # 使用 1920x1080 并缩放
        base = self.LAYOUT['1920x1080']
        scaled = {}
        for k, v in base.items():
            if isinstance(v, list):
                scaled[k] = [
                    tuple(int(c * self._scale_factor) for c in slot)
                    for slot in v
                ]
            else:
                scaled[k] = tuple(int(c * self._scale_factor) for c in v)
        return scaled
    
    def detect_from_screenshot(self, screenshot: np.ndarray, 
                               detect_friendly: bool = True,
                               detect_enemy: bool = True) -> List[DetectedHero]:
        """
        从截图中检测英雄
        
        Args:
            screenshot: OpenCV 格式的截图 (BGR)
            detect_friendly: 是否检测队友
            detect_enemy: 是否检测敌方
            
        Returns:
            检测到的英雄列表
        """
        detected = []
        layout = self._get_layout()
        
        # 检测队友
        if detect_friendly:
            for i, slot in enumerate(layout.get('friendly_slots', [])):
                x1, y1, x2, y2 = slot
                if y2 > screenshot.shape[0] or x2 > screenshot.shape[1]:
                    continue
                    
                slot_img = screenshot[y1:y2, x1:x2]
                hero = self._match_hero(slot_img)
                
                if hero:
                    detected.append(DetectedHero(
                        name=hero,
                        name_cn=HERO_NAME_CN.get(hero, hero),
                        confidence=0.7,  # 简化版固定置信度
                        position=slot,
                        is_friendly=True
                    ))
        
        # 检测敌方
        if detect_enemy:
            for i, slot in enumerate(layout.get('enemy_slots', [])):
                x1, y1, x2, y2 = slot
                if y2 > screenshot.shape[0] or x2 > screenshot.shape[1]:
                    continue
                    
                slot_img = screenshot[y1:y2, x1:x2]
                hero = self._match_hero(slot_img)
                
                if hero:
                    detected.append(DetectedHero(
                        name=hero,
                        name_cn=HERO_NAME_CN.get(hero, hero),
                        confidence=0.7,
                        position=slot,
                        is_friendly=False
                    ))
        
        return detected
    
    def _match_hero(self, slot_img: np.ndarray) -> Optional[str]:
        """
        匹配英雄头像
        
        如果加载了模板，使用模板匹配；
        否则返回 None（需要用户手动输入）
        """
        if not self._templates:
            return None
        
        best_match = None
        best_score = 0.3  # 最小匹配阈值
        
        for hero_name, template in self._templates.items():
            try:
                # 缩放模板以匹配 slot 尺寸
                h, w = slot_img.shape[:2]
                template_resized = cv2.resize(template, (w, h))
                
                # 模板匹配
                result = cv2.matchTemplate(slot_img, template_resized, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, _ = cv2.minMaxLoc(result)
                
                if max_val > best_score:
                    best_score = max_val
                    best_match = hero_name
                    
            except Exception as e:
                continue
        
        return best_match
    
    def detect_hero_select_screen(self, screenshot: np.ndarray) -> bool:
        """
        检测当前是否在英雄选择界面
        
        通过检测界面特征（如英雄选择栏的存在）判断
        """
        layout = self._get_layout()
        icons_region = layout.get('hero_select_icons')
        
        if icons_region:
            x1, y1, x2, y2 = icons_region
            if y2 <= screenshot.shape[0] and x2 <= screenshot.shape[1]:
                region = screenshot[y1:y2, x1:x2]
                
                # 简单判断：底部区域是否有足够丰富的颜色（英雄图标）
                gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
                std = np.std(gray)
                
                # 标准差大于阈值说明有足够多样的颜色
                if std > 30:
                    return True
        
        return False
    
    def manual_input_heroes(self, prompt: str = "输入英雄名（逗号分隔）") -> List[str]:
        """
        手动输入英雄列表（模板不可用时使用）
        
        ⚠️ 警告：此方法调用阻塞式 input()，在 GUI 程序中会导致界面冻结。
        建议在控制台模式或调试时使用。
        """
        print(f"\n{prompt}")
        print(f"可用英雄: {', '.join([HERO_NAME_CN.get(h, h) for h in ALL_HEROES[:10]])}...")
        
        try:
            user_input = input("> ").strip()
            if not user_input:
                return []
            
            heroes = []
            for name in user_input.split(","):
                name = name.strip()
                # 尝试匹配中文名
                for hero, cn in HERO_NAME_CN.items():
                    if name == cn or name.lower() == hero.lower():
                        heroes.append(hero)
                        break
            
            return heroes
        except Exception as e:
            print(f"输入错误: {e}")
            return []
    
    def capture_hero_templates(self, screenshot: np.ndarray, 
                               hero_positions: List[Tuple[int, int, int, int]],
                               hero_names: List[str]) -> None:
        """
        从截图中截取英雄头像并保存为模板
        
        用于初次使用时创建模板库
        """
        os.makedirs(HEROES_DIR, exist_ok=True)
        
        for pos, name in zip(hero_positions, hero_names):
            x1, y1, x2, y2 = pos
            if y2 > screenshot.shape[0] or x2 > screenshot.shape[1]:
                continue
            
            hero_img = screenshot[y1:y2, x1:x2]
            save_path = os.path.join(HEROES_DIR, f"{name}.png")
            cv2.imwrite(save_path, hero_img)
            print(f"[英雄检测] 已保存模板: {name} -> {save_path}")


class SimpleHeroTracker:
    """简易英雄追踪器 - 通过热键手动记录"""
    
    def __init__(self):
        self.friendly_team: List[str] = []
        self.enemy_team: List[str] = []
        self._callbacks: List[callable] = []
    
    def set_friendly(self, heroes: List[str]) -> None:
        """设置队友英雄"""
        self.friendly_team = heroes
        self._notify()
    
    def set_enemy(self, heroes: List[str]) -> None:
        """设置敌方英雄"""
        self.enemy_team = heroes
        self._notify()
    
    def add_friendly(self, hero: str) -> None:
        """添加队友英雄"""
        if hero not in self.friendly_team and len(self.friendly_team) < 5:
            self.friendly_team.append(hero)
            self._notify()
    
    def remove_friendly(self, hero: str) -> None:
        """移除队友英雄"""
        if hero in self.friendly_team:
            self.friendly_team.remove(hero)
            self._notify()
    
    def clear(self) -> None:
        """清空所有记录"""
        self.friendly_team.clear()
        self.enemy_team.clear()
        self._notify()
    
    def on_change(self, callback: callable) -> None:
        """注册变更回调"""
        self._callbacks.append(callback)
    
    def _notify(self) -> None:
        """通知所有监听器"""
        for cb in self._callbacks:
            try:
                cb(self.friendly_team, self.enemy_team)
            except Exception as e:
                print(f"[追踪器] 回调错误: {e}")
    
    def get_summary(self) -> str:
        """获取当前阵容摘要"""
        friendly_cn = [HERO_NAME_CN.get(h, h) for h in self.friendly_team]
        enemy_cn = [HERO_NAME_CN.get(h, h) for h in self.enemy_team]
        
        lines = []
        lines.append(f"队友: {' / '.join(friendly_cn) if friendly_cn else '无'}")
        lines.append(f"敌方: {' / '.join(enemy_cn) if enemy_cn else '无'}")
        return "\n".join(lines)


# 测试代码
if __name__ == "__main__":
    print("测试英雄检测模块...")
    
    detector = HeroDetector()
    
    # 测试分辨率设置
    detector.set_resolution(1920, 1080)
    print(f"当前分辨率: {detector._resolution}, 缩放: {detector._scale_factor}")
    
    # 测试布局
    layout = detector._get_layout()
    print(f"队友槽位: {layout.get('friendly_slots', [])}")
    
    # 测试手动追踪
    tracker = SimpleHeroTracker()
    tracker.add_friendly("Winston")
    tracker.add_friendly("Genji")
    print(f"\n阵容摘要:\n{tracker.get_summary()}")

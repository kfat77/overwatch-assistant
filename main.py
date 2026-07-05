"""
Overwatch Assistant - Main Application
守望先锋辅助插件 - 主程序

功能:
1. 实时翻译聊天框文字（支持英文、韩文 -> 中文）
2. 英雄选择时根据队友阵容推荐英雄
3. 透明叠加层显示

使用方式:
    python main.py

热键:
    F9  - 显示/隐藏叠加层
    F10 - 开始/停止聊天捕获
    F11 - 选择聊天框区域
    F12 - 选择英雄选择区域
    Ctrl+Shift+Q - 退出程序

作者: Overwatch Assistant Team
版本: 1.0.0
"""

import os
import sys
import time
import threading
import traceback
from typing import Optional, List

# 添加项目根目录到路径
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from config import (
    app_config, capture_config, ocr_config, 
    translate_config, overlay_config
)
from core.capture import ScreenCapture, RegionSelector
from core.ocr_engine import create_ocr_engine, TextDeduplicator
from core.translator import Translator, ChatMessageTranslator
from core.overlay import OverlayWindow, CompactOverlay
from core.hero_recommender import HeroRecommender
from core.hero_detector import HeroDetector, SimpleHeroTracker


class OverwatchAssistant:
    """守望先锋辅助主程序"""
    
    def __init__(self):
        print(f"\n{'='*50}")
        print(f"  {app_config.app_name} v{app_config.version}")
        print(f"{'='*50}\n")
        
        # 初始化模块
        self.capture = ScreenCapture()
        self.translator = Translator(translate_config)
        self.chat_translator = ChatMessageTranslator(self.translator)
        self.overlay: Optional[OverlayWindow] = None
        self.recommender = HeroRecommender()
        self.detector = HeroDetector()
        self.hero_tracker = SimpleHeroTracker()
        
        # 状态
        self._running = False
        self._capturing_chat = False
        self._ocr_engine = None
        self._text_dedup = TextDeduplicator()
        self._hotkey_thread: Optional[threading.Thread] = None
        
        # 统计
        self._stats = {
            'messages_translated': 0,
            'screenshots_processed': 0,
            'start_time': 0
        }
        
        # 绑定回调
        self.hero_tracker.on_change(self._on_team_changed)
    
    def initialize(self) -> bool:
        """初始化所有模块"""
        try:
            print("[初始化] 正在加载模块...")
            
            # 1. 初始化 OCR
            print("[初始化] 加载 OCR 引擎...")
            self._ocr_engine = create_ocr_engine(ocr_config)
            print("[初始化] OCR 引擎就绪")
            
            # 2. 启动叠加层
            print("[初始化] 启动叠加层...")
            self.overlay = OverlayWindow(overlay_config)
            self.overlay.start()
            time.sleep(1)  # 等待窗口启动
            print("[初始化] 叠加层已启动")
            
            # 3. 注册热键
            print("[初始化] 注册热键...")
            self._register_hotkeys()
            
            # 4. 获取屏幕分辨率
            resolution = self.capture.get_screen_resolution()
            print(f"[初始化] 检测到屏幕分辨率: {resolution[0]}x{resolution[1]}")
            self.detector.set_resolution(resolution[0], resolution[1])
            
            print("\n[初始化] 所有模块加载完成！")
            print(f"\n热键指南:")
            print(f"  {app_config.hotkey_select_chat_region.upper():10} - 选择聊天框区域")
            print(f"  {app_config.hotkey_toggle_capture.upper():10} - 开始/停止聊天翻译")
            print(f"  {app_config.hotkey_toggle_overlay.upper():10} - 显示/隐藏叠加层")
            print(f"  {app_config.hotkey_select_hero_region.upper():10} - 选择英雄选择区域")
            print(f"  {app_config.hotkey_exit.upper():15} - 退出程序")
            print()
            
            return True
            
        except Exception as e:
            print(f"[初始化错误] {e}")
            traceback.print_exc()
            return False
    
    def _register_hotkeys(self) -> None:
        """注册全局热键"""
        try:
            import keyboard
            
            # F11 - 选择聊天框区域
            keyboard.add_hotkey(
                app_config.hotkey_select_chat_region,
                self._on_select_chat_region
            )
            
            # F10 - 切换聊天捕获
            keyboard.add_hotkey(
                app_config.hotkey_toggle_capture,
                self._on_toggle_capture
            )
            
            # F9 - 切换叠加层显示
            keyboard.add_hotkey(
                app_config.hotkey_toggle_overlay,
                self._on_toggle_overlay
            )
            
            # F12 - 选择英雄选择区域
            keyboard.add_hotkey(
                app_config.hotkey_select_hero_region,
                self._on_select_hero_region
            )
            
            # Ctrl+Shift+Q - 退出
            keyboard.add_hotkey(
                app_config.hotkey_exit,
                self.stop
            )
            
            print("[热键] 热键注册完成")
            
        except ImportError:
            print("[热键警告] 未安装 keyboard 库，热键功能将不可用")
            print("[热键警告] 请运行: pip install keyboard")
            self._start_hotkey_poll_thread()
    
    def _start_hotkey_poll_thread(self) -> None:
        """备用：轮询方式检测热键"""
        def poll_hotkeys():
            while self._running:
                try:
                    import keyboard
                    if keyboard.is_pressed(app_config.hotkey_toggle_capture):
                        self._on_toggle_capture()
                        time.sleep(0.5)
                    elif keyboard.is_pressed(app_config.hotkey_select_chat_region):
                        self._on_select_chat_region()
                        time.sleep(0.5)
                    elif keyboard.is_pressed(app_config.hotkey_exit):
                        self.stop()
                        break
                except:
                    pass
                time.sleep(0.1)
        
        self._hotkey_thread = threading.Thread(target=poll_hotkeys, daemon=True)
        self._hotkey_thread.start()
    
    def _on_select_chat_region(self) -> None:
        """选择聊天框区域"""
        print("\n[操作] 请选择聊天框区域...")
        if self.overlay:
            self.overlay.add_system_message("请点击聊天框区域并拖拽选择")
        
        selector = RegionSelector()
        region = selector.select_region("选择守望先锋聊天框区域")
        
        if region:
            self.capture.set_region(region)
            capture_config.chat_region = region
            print(f"[操作] 聊天框区域已设置: {region}")
            if self.overlay:
                self.overlay.add_system_message(f"聊天框区域已设置")
        else:
            print("[操作] 取消选择")
    
    def _on_select_hero_region(self) -> None:
        """选择英雄选择区域"""
        print("\n[操作] 请选择英雄选择界面区域...")
        if self.overlay:
            self.overlay.add_system_message("请选择英雄选择界面区域")
        
        selector = RegionSelector()
        region = selector.select_region("选择英雄选择界面区域（包含所有队友头像）")
        
        if region:
            capture_config.hero_select_region = region
            print(f"[操作] 英雄选择区域已设置: {region}")
            if self.overlay:
                self.overlay.add_system_message("英雄选择区域已设置")
        else:
            print("[操作] 取消选择")
    
    def _on_toggle_capture(self) -> None:
        """切换聊天捕获"""
        if self._capturing_chat:
            self._stop_chat_capture()
        else:
            self._start_chat_capture()
    
    def _start_chat_capture(self) -> None:
        """开始聊天捕获"""
        if self.capture.get_region() is None:
            print("[错误] 请先选择聊天框区域 (F11)")
            if self.overlay:
                self.overlay.add_system_message("请先按 F11 选择聊天框区域")
            return
        
        self._capturing_chat = True
        self._text_dedup.clear()
        print("[捕获] 开始聊天翻译...")
        if self.overlay:
            self.overlay.add_system_message("开始聊天翻译")
        
        self.capture.start_continuous(
            interval=capture_config.capture_interval,
            callback=self._process_chat_frame
        )
    
    def _stop_chat_capture(self) -> None:
        """停止聊天捕获"""
        self._capturing_chat = False
        self.capture.stop_continuous()
        print("[捕获] 停止聊天翻译")
        if self.overlay:
            self.overlay.add_system_message("停止聊天翻译")
    
    def _process_chat_frame(self, img) -> None:
        """处理聊天帧"""
        try:
            self._stats['screenshots_processed'] += 1
            
            # OCR 识别
            results = self._ocr_engine.recognize(img)
            
            for result in results:
                text = result.text.strip()
                if not text or len(text) < 2:
                    continue
                
                # 去重检查
                if self._text_dedup.is_duplicate(text):
                    continue
                
                # 翻译
                translation = self.chat_translator.translate_chat(text)
                
                if not translation.is_empty and translation.source_language != translate_config.target_language:
                    self._text_dedup.add(text)
                    self._stats['messages_translated'] += 1
                    
                    # 显示到叠加层
                    if self.overlay:
                        self.overlay.add_translation(
                            original=translation.original,
                            translated=translation.translated
                        )
                    
                    # 控制台输出
                    print(f"\n[翻译] {translation.original}")
                    print(f"       -> {translation.translated}")
                    
        except Exception as e:
            print(f"[处理错误] {e}")
    
    def _on_toggle_overlay(self) -> None:
        """切换叠加层显示"""
        if self.overlay:
            self.overlay.toggle()
            state = "显示" if self.overlay.is_visible else "隐藏"
            print(f"[叠加层] 已{state}")
    
    def _on_team_changed(self, friendly: List[str], enemy: List[str]) -> None:
        """队伍变更回调"""
        print(f"\n[阵容] 队友: {friendly}")
        print(f"[阵容] 敌方: {enemy}")
        
        # 生成推荐
        if friendly:
            recommendation = self.recommender.get_quick_recommendation(friendly, enemy)
            print(f"[推荐] {recommendation}")
            
            if self.overlay:
                self.overlay.add_recommendation(recommendation)
    
    def run(self) -> None:
        """运行主程序"""
        if not self.initialize():
            print("[错误] 初始化失败，程序退出")
            return
        
        self._running = True
        self._stats['start_time'] = time.time()
        
        print("\n[运行] 程序正在运行，按 Ctrl+Shift+Q 退出\n")
        
        if self.overlay:
            self.overlay.add_system_message("守望先锋辅助已启动！按 F11 选择聊天框区域")
        
        try:
            while self._running:
                time.sleep(1)
                
                # 定期显示统计
                elapsed = time.time() - self._stats['start_time']
                if int(elapsed) % 60 == 0 and self._stats['messages_translated'] > 0:
                    rate = self._stats['messages_translated'] / max(elapsed / 60, 1)
                    print(f"[统计] 运行 {int(elapsed/60)} 分钟，翻译 {self._stats['messages_translated']} 条消息，"
                          f"平均 {rate:.1f} 条/分钟")
                
        except KeyboardInterrupt:
            print("\n[信号] 收到中断信号")
        finally:
            self.stop()
    
    def stop(self) -> None:
        """停止程序"""
        print("\n[退出] 正在关闭程序...")
        self._running = False
        
        # 停止捕获
        if self._capturing_chat:
            self._stop_chat_capture()
        
        # 关闭叠加层
        if self.overlay:
            self.overlay.stop()
        
        # 显示最终统计
        elapsed = time.time() - self._stats['start_time']
        print(f"\n{'='*50}")
        print(f"  运行时间: {int(elapsed)} 秒")
        print(f"  处理截图: {self._stats['screenshots_processed']}")
        print(f"  翻译消息: {self._stats['messages_translated']}")
        print(f"{'='*50}\n")
        
        print("[退出] 程序已退出")
        os._exit(0)


def check_dependencies() -> bool:
    """检查依赖是否安装"""
    required = {
        'PIL': 'Pillow',
        'numpy': 'numpy',
        'cv2': 'opencv-python',
        'translators': 'translators',
    }
    
    missing = []
    for module, package in required.items():
        try:
            __import__(module)
        except ImportError:
            missing.append(package)
    
    if missing:
        print("[错误] 缺少以下依赖包:")
        for pkg in missing:
            print(f"  - {pkg}")
        print(f"\n请运行: pip install {' '.join(missing)}")
        return False
    
    return True


def main():
    """主入口"""
    # 检查依赖
    if not check_dependencies():
        return 1
    
    # 创建并运行
    app = OverwatchAssistant()
    app.run()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

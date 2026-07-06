"""
Overwatch Assistant - Main Application (Enhanced v2.0)
守望先锋辅助插件 - 主程序（增强版）

功能:
1. 实时翻译聊天框文字（EN/KO -> CN）- 支持 Timeline 对齐去重
2. 英雄选择时根据队友阵容推荐英雄
3. 透明叠加层显示 - 支持历史滚动、鼠标穿透、回话输入
4. 智能捕获 - 像素差分巡逻 + 文字存在检测，大幅降低 CPU 占用
5. 韩语优化 - Jamo 级相似度匹配，OCR 抖动容错
6. OW 术语表 - 独立 JSON 文件，快速游戏术语翻译

热键:
    F9  - 显示/隐藏叠加层
    F10 - 开始/停止聊天捕获
    F11 - 选择聊天框区域
    F12 - 选择英雄选择区域
    Ctrl+Shift+Q - 退出程序

版本: 2.1.0 (参考 ow-translate-lite 核心设计)
"""

import os
import sys
import time
import threading
import traceback
from typing import Optional, List

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from config import (
    app_config, capture_config, ocr_config,
    translate_config, overlay_config
)

# 新模块
from core.smart_capture import SmartCapture
from core.timeline import TimelineAlignmentDetector, MultiFrameConsensus, OwChatParser
from core.ocr_engine import create_ocr_engine, TextDeduplicator
from core.translator import Translator, ChatMessageTranslator
from core.overlay import OverlayWindow
from core.hero_recommender import HeroRecommender
from core.hero_detector import HeroDetector, SimpleHeroTracker
from core.glossary_service import glossary_service, quick_translate
from core.korean_jamo import KoreanJamoMatcher
from core.reply_assistant import ReplyAssistant
from core.chat_codes import OwChatTemplate, PRESET_COLORS, parse_ow_code


class OverwatchAssistant:
    """守望先锋辅助主程序（完善优化版 v2.1）"""

    def __init__(self):
        print(f"\n{'='*50}")
        print(f"  {app_config.app_name} v{app_config.version}")
        print(f"  集成 reverieach/ow-translate-lite + MapleOAO/chat-editor")
        print(f"{'='*50}\n")

        # 初始化模块
        self.capture = SmartCapture()
        self.translator = Translator(translate_config)
        self.chat_translator = ChatMessageTranslator(self.translator)
        self.overlay: Optional[OverlayWindow] = None
        self.recommender = HeroRecommender()
        self.detector = HeroDetector()
        self.hero_tracker = SimpleHeroTracker()

        # 新模块
        self.timeline = TimelineAlignmentDetector(max_history=50)
        self.consensus = MultiFrameConsensus(required_frames=2)
        self.korean_matcher = KoreanJamoMatcher()
        self.reply_assistant = ReplyAssistant(self.translator)

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
            'ocr_skipped': 0,        # 因像素差分跳过的 OCR
            'timeline_matched': 0,    # Timeline 对齐匹配的旧消息
            'start_time': 0
        }

        # 绑定回调
        self.hero_tracker.on_change(self._on_team_changed)
        self.capture.set_region(capture_config.chat_region)

    def initialize(self) -> bool:
        """初始化所有模块"""
        try:
            print("[初始化] 正在加载模块...")

            # 1. 初始化 OCR
            print("[初始化] 加载 OCR 引擎...")
            try:
                self._ocr_engine = create_ocr_engine(ocr_config)
                print(f"[初始化] OCR 引擎就绪: {ocr_config.engine}")
            except Exception as e:
                print(f"[初始化警告] OCR 引擎加载失败: {e}")
                print("[初始化警告] 聊天翻译功能将不可用，请安装 Tesseract-OCR")
                self._ocr_engine = None

            # 2. 加载术语表
            print("[初始化] 加载游戏术语表...")
            glossary_count = len(glossary_service.get_all())
            print(f"[初始化] 已加载 {glossary_count} 条游戏术语")

            # 3. 启动叠加层
            print("[初始化] 启动叠加层...")
            self.overlay = OverlayWindow(overlay_config)
            self.overlay.start()
            time.sleep(1)
            print("[初始化] 叠加层已启动")

            # 4. 设置回话回调
            self.overlay.set_reply_callback(self._on_reply_input)

            # 5. 注册热键
            print("[初始化] 注册热键...")
            self._register_hotkeys()

            # 6. 获取屏幕分辨率
            resolution = self._get_screen_resolution()
            print(f"[初始化] 检测到屏幕分辨率: {resolution[0]}x{resolution[1]}")
            self.detector.set_resolution(resolution[0], resolution[1])

            # OCR 未就绪提示
            if self._ocr_engine is None:
                self.overlay.add_system_message("⚠️ OCR 未就绪 - 聊天翻译不可用")
                self.overlay.add_system_message("请安装 Tesseract-OCR，详见 README")

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

    def _get_screen_resolution(self) -> tuple:
        """获取屏幕分辨率"""
        try:
            from PIL import ImageGrab
            img = ImageGrab.grab()
            return img.size
        except Exception:
            return (1920, 1080)

    def _register_hotkeys(self) -> None:
        """注册全局热键"""
        try:
            import keyboard
            keyboard.add_hotkey(app_config.hotkey_select_chat_region, self._on_select_chat_region)
            keyboard.add_hotkey(app_config.hotkey_toggle_capture, self._on_toggle_capture)
            keyboard.add_hotkey(app_config.hotkey_toggle_overlay, self._on_toggle_overlay)
            keyboard.add_hotkey(app_config.hotkey_select_hero_region, self._on_select_hero_region)
            keyboard.add_hotkey(app_config.hotkey_exit, self.stop)
            print("[热键] 热键注册完成")
        except ImportError:
            print("[热键警告] 未安装 keyboard 库，热键功能将不可用")
            print("[热键警告] 请运行: pip install keyboard")

    def _on_select_chat_region(self) -> None:
        """选择聊天框区域"""
        print("\n[操作] 请选择聊天框区域...")
        if self.overlay:
            self.overlay.add_system_message("请点击聊天框区域并拖拽选择")

        from core.capture import RegionSelector
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

        from core.capture import RegionSelector
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
        if self._ocr_engine is None:
            print("[错误] OCR 引擎未就绪，无法开始翻译")
            if self.overlay:
                self.overlay.add_system_message("OCR 未就绪，请安装 Tesseract-OCR")
            return

        if self.capture._region is None:
            print("[错误] 请先选择聊天框区域 (F11)")
            if self.overlay:
                self.overlay.add_system_message("请先按 F11 选择聊天框区域")
            return

        self._capturing_chat = True
        self._text_dedup.clear()
        self.timeline.clear()
        self.consensus.reset()
        print("[捕获] 开始聊天翻译...")
        if self.overlay:
            self.overlay.add_system_message("开始聊天翻译")
            self.overlay.show_reply_bar(True)

        self.capture.start(callback=self._process_chat_frame)

    def _stop_chat_capture(self) -> None:
        """停止聊天捕获"""
        self._capturing_chat = False
        self.capture.stop()
        print("[捕获] 停止聊天翻译")
        if self.overlay:
            self.overlay.add_system_message("停止聊天翻译")
            self.overlay.show_reply_bar(False)

    def _process_chat_frame(self, img) -> None:
        """处理聊天帧（核心逻辑）"""
        if self._ocr_engine is None:
            return

        try:
            self._stats['screenshots_processed'] += 1

            # 1. OCR 识别
            results = self._ocr_engine.recognize(img)
            raw_texts = [r.text for r in results if r.confidence >= ocr_config.confidence_threshold]

            if not raw_texts:
                return

            # 2. Timeline 对齐处理
            confirmed_new, visible_messages = self.timeline.process_frame(raw_texts)

            # 统计对齐
            self._stats['timeline_matched'] += len(visible_messages) - len(confirmed_new)

            # 3. 处理新消息（多帧共识 + 翻译）
            for msg in confirmed_new:
                # 多帧共识
                if not self.consensus.observe(msg):
                    continue  # 未达到共识，跳过

                # 术语替换
                glossary_result = quick_translate(msg.text)
                if glossary_result:
                    msg.translated = glossary_result
                    print(f"\n[术语] {msg.raw}")
                    print(f"       -> {msg.translated}")
                else:
                    # 翻译
                    translation = self.chat_translator.translate_chat(msg.text)
                    if not translation.is_empty:
                        msg.translated = translation.translated
                        print(f"\n[翻译] {msg.raw}")
                        print(f"       -> {msg.translated}")

                self._stats['messages_translated'] += 1

                # 显示到叠加层
                if self.overlay:
                    self.overlay.add_translation(
                        original=msg.raw,
                        translated=msg.translated,
                        player=msg.player
                    )

            # 4. 更新可见消息（显示旧消息的翻译）
            for msg in visible_messages:
                if msg.translated and not msg.confirmed:
                    # 旧消息已翻译，确保显示在叠加层
                    pass

        except Exception as e:
            print(f"[处理错误] {e}")

    def _on_reply_input(self, text: str, lang: str) -> None:
        """处理回话输入"""
        # 检查是否是模板发送
        if text.startswith("__TEMPLATE__:"):
            template_key = text.split(":", 1)[1]
            result = self.reply_assistant.send_template(template_key)
            if result and result.ow_code:
                print(f"\n[模板] {result.original}")
                print(f"[模板] 代码: {result.ow_code}")
                if self.overlay:
                    self.overlay.add_reply_result(
                        original=result.original,
                        translated=result.ow_code,
                        target_lang="ow_code"
                    )
                    if result.copied:
                        self.overlay.add_system_message("模板代码已复制到剪贴板")
            return
        
        print(f"\n[回话] 中文: {text}")
        self.reply_assistant.set_target_language(lang)
        result = self.reply_assistant.translate_reply(text)

        if result.translated:
            print(f"[回话] {result.target_language}: {result.translated}")
            if self.overlay:
                self.overlay.add_reply_result(
                    original=text,
                    translated=result.translated,
                    target_lang=result.target_language
                )
                if result.copied:
                    self.overlay.add_system_message("译文已复制到剪贴板")

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
            self.overlay.add_system_message(f"守望先锋辅助 v{app_config.version} 已启动！")
            self.overlay.add_system_message("按 F11 选择聊天框区域，F10 开始翻译")

        try:
            while self._running:
                time.sleep(1)

                # 定期显示统计
                elapsed = time.time() - self._stats['start_time']
                if int(elapsed) % 60 == 0 and self._stats['messages_translated'] > 0:
                    rate = self._stats['messages_translated'] / max(elapsed / 60, 1)
                    print(f"[统计] 运行 {int(elapsed/60)} 分钟")
                    print(f"       翻译 {self._stats['messages_translated']} 条，平均 {rate:.1f} 条/分钟")
                    print(f"       Timeline 对齐跳过 {self._stats['timeline_matched']} 条旧消息")
                    print(f"       处理截图 {self._stats['screenshots_processed']} 张")

        except KeyboardInterrupt:
            print("\n[信号] 收到中断信号")
        finally:
            self.stop()

    def stop(self) -> None:
        """停止程序"""
        print("\n[退出] 正在关闭程序...")
        self._running = False

        if self._capturing_chat:
            self._stop_chat_capture()

        if self.overlay:
            self.overlay.stop()

        elapsed = time.time() - self._stats['start_time']
        print(f"\n{'='*50}")
        print(f"  运行时间: {int(elapsed)} 秒")
        print(f"  处理截图: {self._stats['screenshots_processed']}")
        print(f"  翻译消息: {self._stats['messages_translated']}")
        print(f"  Timeline 对齐跳过: {self._stats['timeline_matched']}")
        print(f"{'='*50}\n")

        print("[退出] 程序已退出")
        os._exit(0)


def check_dependencies() -> bool:
    """检查依赖是否安装"""
    # FIX: 补充 requirements.txt 中所有关键运行时依赖
    required = {
        'PIL': 'Pillow',
        'numpy': 'numpy',
        'cv2': 'opencv-python',
        'translators': 'translators',
        'keyboard': 'keyboard',
        'pytesseract': 'pytesseract',
        'pyperclip': 'pyperclip',
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
    if not check_dependencies():
        return 1

    app = OverwatchAssistant()
    app.run()

    return 0


if __name__ == "__main__":
    sys.exit(main())

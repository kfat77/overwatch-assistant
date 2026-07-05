"""
Reply Assistant - 回话助手

功能：在叠加层底部输入中文，翻译为英/韩/日，自动复制到剪贴板
支持 OW 聊天颜色代码生成（参考 MapleOAO/overwatch-chat-editor）
"""

import time
import threading
from typing import Optional, Callable
from dataclasses import dataclass

from .translator import Translator
from .chat_codes import OwChatTemplate, color_text, PRESET_COLORS


@dataclass
class ReplyTranslation:
    """回话翻译结果"""
    original: str          # 中文原文
    translated: str        # 翻译结果
    target_language: str   # 目标语言
    copied: bool           # 是否已复制到剪贴板
    ow_code: Optional[str] = None  # OW 颜色代码（如果有）


class ReplyAssistant:
    """回话助手"""
    
    TARGET_LANGUAGES = {
        "auto": "自动检测",
        "en": "英语",
        "ko": "韩语",
        "ja": "日语",
    }
    
    def __init__(self, translator: Translator):
        self.translator = translator
        self.target_language: str = "auto"
        self.auto_copy: bool = True
        self.use_ow_color: bool = False  # 是否使用 OW 颜色代码
        self._on_translation: Optional[Callable[[ReplyTranslation], None]] = None
    
    def set_target_language(self, lang: str) -> None:
        """设置目标语言"""
        if lang in self.TARGET_LANGUAGES:
            self.target_language = lang
    
    def set_ow_color(self, enabled: bool) -> None:
        """设置是否使用 OW 颜色代码"""
        self.use_ow_color = enabled
    
    def translate_reply(self, chinese_text: str) -> ReplyTranslation:
        """
        翻译回话
        
        Args:
            chinese_text: 中文输入文本
            
        Returns:
            ReplyTranslation
        """
        if not chinese_text or not chinese_text.strip():
            return ReplyTranslation(
                original="",
                translated="",
                target_language=self.target_language,
                copied=False
            )
        
        # 确定目标语言
        if self.target_language == "auto":
            target = self._detect_target_language()
        else:
            target = self.target_language
        
        # 翻译
        result = self.translator.translate(
            chinese_text,
            source_lang="zh",
            target_lang=target
        )
        
        translated = result.translated
        ow_code = None
        
        # 如果启用 OW 颜色，添加颜色代码
        if self.use_ow_color and translated:
            color = self._select_color_for_text(translated)
            ow_code = color_text(translated, color)
        
        # 复制到剪贴板
        copied = False
        text_to_copy = ow_code if ow_code else translated
        if self.auto_copy and text_to_copy:
            copied = self._copy_to_clipboard(text_to_copy)
        
        reply = ReplyTranslation(
            original=chinese_text,
            translated=translated,
            target_language=target,
            copied=copied,
            ow_code=ow_code
        )
        
        if self._on_translation:
            self._on_translation(reply)
        
        return reply
    
    def send_template(self, template_key: str) -> Optional[ReplyTranslation]:
        """
        发送预设模板
        
        Args:
            template_key: 模板键名
            
        Returns:
            ReplyTranslation 或 None
        """
        code = OwChatTemplate.get(template_key)
        if not code:
            return None
        
        plain = OwChatTemplate.get_plain_text(template_key)
        
        copied = self._copy_to_clipboard(code)
        
        reply = ReplyTranslation(
            original=plain,
            translated=plain,
            target_language="en",
            copied=copied,
            ow_code=code
        )
        
        if self._on_translation:
            self._on_translation(reply)
        
        return reply
    
    def _detect_target_language(self) -> str:
        """自动检测目标语言（基于最近聊天）"""
        # 简化：默认英语
        return "en"
    
    def _select_color_for_text(self, text: str) -> "ColorCode":
        """根据文本内容选择合适颜色"""
        text_lower = text.lower()
        if any(w in text_lower for w in ["heal", "help", "thanks", "gg", "gl", "nice"]):
            return PRESET_COLORS["green"]
        elif any(w in text_lower for w in ["need", "push", "go", "attack"]):
            return PRESET_COLORS["blue"]
        elif any(w in text_lower for w in ["back", "retreat", "danger", "no"]):
            return PRESET_COLORS["red"]
        return PRESET_COLORS["white"]
    
    def _copy_to_clipboard(self, text: str) -> bool:
        """复制文本到剪贴板"""
        try:
            import pyperclip
            pyperclip.copy(text)
            return True
        except ImportError:
            # 备用方案：使用 Windows API
            try:
                import subprocess
                subprocess.run(
                    ["powershell", "-command", f"Set-Clipboard -Value '{text.replace(\"'\", \"''\")}'"],
                    capture_output=True
                )
                return True
            except Exception:
                pass
        
        return False
    
    def on_translation(self, callback: Callable[[ReplyTranslation], None]) -> None:
        """注册翻译完成回调"""
        self._on_translation = callback
    
    def get_available_languages(self) -> dict:
        """获取可用语言列表"""
        return self.TARGET_LANGUAGES.copy()
    
    def get_templates(self) -> list:
        """获取可用模板列表"""
        return OwChatTemplate.list_templates()

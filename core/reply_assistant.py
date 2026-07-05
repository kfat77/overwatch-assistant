"""
Reply Assistant - 回话助手

功能：在叠加层底部输入中文，翻译为英/韩/日，自动复制到剪贴板
移植自 ow-translate-lite 的 Reply Input 功能。
"""

import time
import threading
from typing import Optional, Callable
from dataclasses import dataclass

from .translator import Translator


@dataclass
class ReplyTranslation:
    """回话翻译结果"""
    original: str          # 中文原文
    translated: str        # 翻译结果
    target_language: str   # 目标语言
    copied: bool           # 是否已复制到剪贴板


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
        self._on_translation: Optional[Callable[[ReplyTranslation], None]] = None
    
    def set_target_language(self, lang: str) -> None:
        """设置目标语言"""
        if lang in self.TARGET_LANGUAGES:
            self.target_language = lang
    
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
            # 自动检测：根据最近聊天语言判断
            target = self._detect_target_language()
        else:
            target = self.target_language
        
        # 翻译
        result = self.translator.translate(
            chinese_text,
            source_lang="zh",
            target_lang=target
        )
        
        # 复制到剪贴板
        copied = False
        if self.auto_copy and result.translated:
            copied = self._copy_to_clipboard(result.translated)
        
        reply = ReplyTranslation(
            original=chinese_text,
            translated=result.translated,
            target_language=target,
            copied=copied
        )
        
        if self._on_translation:
            self._on_translation(reply)
        
        return reply
    
    def _detect_target_language(self) -> str:
        """自动检测目标语言（基于最近聊天）"""
        # 简化：默认英语
        return "en"
    
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

"""
Overwatch Assistant - Translator Module
翻译模块

支持多种翻译引擎，提供实时聊天翻译功能。
"""

import re
import time
import threading
from typing import Optional, List, Dict
from dataclasses import dataclass

try:
    import translators as ts
    TRANSLATORS_AVAILABLE = True
except ImportError:
    TRANSLATORS_AVAILABLE = False
    print("[翻译] translators 库未安装，将使用备用翻译方案")


@dataclass
class TranslationResult:
    """翻译结果"""
    original: str
    translated: str
    source_language: str
    target_language: str
    engine: str
    timestamp: float
    
    @property
    def is_empty(self) -> bool:
        return not self.translated or self.translated == self.original
    
    def __repr__(self):
        return f"Translation({self.original[:20]}... -> {self.translated[:20]}...)"


class Translator:
    """翻译器"""
    
    # 语言代码映射
    LANG_MAP = {
        'en': 'english',
        'ko': 'korean', 
        'ja': 'japanese',
        'zh': 'chinese',
        'zh-cn': 'chinese',
        'zh-tw': 'chinese',
        'fr': 'french',
        'de': 'german',
        'es': 'spanish',
        'ru': 'russian',
        'pt': 'portuguese',
        'it': 'italian',
    }
    
    # 语言检测正则
    LANG_PATTERNS = {
        'ko': re.compile(r'[\uac00-\ud7af\u1100-\u11ff]+'),
        'ja': re.compile(r'[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9faf]+'),
        'zh': re.compile(r'[\u4e00-\u9fff]+'),
        'en': re.compile(r'^[a-zA-Z0-9\s\.,!?;:\-\(\)\[\]{}@#$%&*]+$', re.UNICODE),
    }
    
    def __init__(self, config):
        self.config = config
        self._lock = threading.Lock()
        self._request_count = 0
        self._last_request_time = 0
        self._min_interval = 0.1  # 最小请求间隔（秒）
        
        # 检查翻译库可用性
        self._engine_available = self._check_engine()
    
    def _check_engine(self) -> bool:
        """检查翻译引擎是否可用"""
        if not TRANSLATORS_AVAILABLE:
            return False
        try:
            # 测试翻译
            test = ts.translate_text("hello", translator=self.config.engine)
            return True
        except Exception as e:
            print(f"[翻译] 引擎 {self.config.engine} 测试失败: {e}")
            return False
    
    def detect_language(self, text: str) -> str:
        """
        检测文本语言
        
        Args:
            text: 输入文本
            
        Returns:
            语言代码
        """
        text = text.strip()
        if not text:
            return 'en'
        
        # 基于字符范围检测
        char_counts = {}
        for lang, pattern in self.LANG_PATTERNS.items():
            matches = pattern.findall(text)
            if matches:
                char_counts[lang] = sum(len(m) for m in matches)
        
        if char_counts:
            # 返回匹配最多的语言
            detected = max(char_counts, key=char_counts.get)
            if detected != 'en' or char_counts.get('en', 0) > len(text) * 0.5:
                return detected
        
        # 默认英文
        return 'en'
    
    def translate(self, text: str, 
                  source_lang: Optional[str] = None,
                  target_lang: Optional[str] = None) -> TranslationResult:
        """
        翻译文本
        
        Args:
            text: 要翻译的文本
            source_lang: 源语言代码，None 则自动检测
            target_lang: 目标语言代码，None 则使用配置默认值
            
        Returns:
            TranslationResult
        """
        if not text or not text.strip():
            return TranslationResult(
                original="",
                translated="",
                source_language=source_lang or "auto",
                target_language=target_lang or self.config.target_language,
                engine="none",
                timestamp=time.time()
            )
        
        original = text.strip()
        target = target_lang or self.config.target_language
        
        # 自动检测源语言
        if source_lang is None or source_lang == "auto":
            source = self.detect_language(original)
        else:
            source = source_lang
        
        # 如果已经是目标语言，跳过翻译
        if source == target or (source in ('zh', 'zh-cn', 'zh-tw') and target in ('zh', 'zh-cn', 'zh-tw')):
            return TranslationResult(
                original=original,
                translated=original,
                source_language=source,
                target_language=target,
                engine="skip",
                timestamp=time.time()
            )
        
        # 检查缓存
        if self.config.enable_cache:
            # 这里可以通过外部缓存对象检查，简化起见先不实现
            pass
        
        # 执行翻译
        translated = self._do_translate(original, source, target)
        
        return TranslationResult(
            original=original,
            translated=translated or original,
            source_language=source,
            target_language=target,
            engine=self.config.engine if self._engine_available else "fallback",
            timestamp=time.time()
        )
    
    def _do_translate(self, text: str, source: str, target: str) -> str:
        """执行实际翻译"""
        with self._lock:
            # 速率限制
            elapsed = time.time() - self._last_request_time
            if elapsed < self._min_interval:
                time.sleep(self._min_interval - elapsed)
            
            try:
                if self._engine_available:
                    result = ts.translate_text(
                        text,
                        translator=self.config.engine,
                        from_language=source,
                        to_language=target
                    )
                    self._last_request_time = time.time()
                    self._request_count += 1
                    return result
                else:
                    # 备用方案：返回原文 + 提示
                    return f"[翻译不可用] {text}"
                    
            except Exception as e:
                print(f"[翻译错误] 翻译失败: {e}")
                return f"[翻译失败] {text}"
    
    def translate_batch(self, texts: List[str], 
                       source_lang: Optional[str] = None,
                       target_lang: Optional[str] = None) -> List[TranslationResult]:
        """批量翻译"""
        results = []
        for text in texts:
            result = self.translate(text, source_lang, target_lang)
            results.append(result)
        return results
    
    def get_stats(self) -> Dict:
        """获取翻译统计"""
        return {
            'engine': self.config.engine,
            'available': self._engine_available,
            'requests': self._request_count,
            'target_language': self.config.target_language,
        }


class ChatMessageTranslator:
    """聊天消息翻译器 - 专门针对游戏聊天优化"""
    
    # 守望先锋常见聊天模式
    CHAT_PATTERNS = [
        re.compile(r'\[(\w+)\]\s*(.+)'),  # [玩家名] 消息
        re.compile(r'(\w+):\s*(.+)'),      # 玩家名: 消息
        re.compile(r'<(\w+)>\s*(.+)'),    # <玩家名> 消息
    ]
    
    # 游戏常用词汇映射（快速替换，减少 API 调用）
    QUICK_REPLACEMENTS = {
        'gg': '打得好',
        'wp': '玩得漂亮',
        'gl hf': '祝好运，玩得开心',
        'glhf': '祝好运，玩得开心',
        'ty': '谢谢',
        'thx': '谢谢',
        'np': '不客气',
        'gl': '祝好运',
        'hf': '玩得开心',
        'brb': '马上回来',
        'afk': '暂离',
        'lol': '哈哈',
        'heal': '治疗',
        'help': '帮忙',
        'push': '推进',
        'group up': '集合',
        'group': '集合',
        'wait': '等等',
        'go': '上',
        'back': '后退',
        'retreat': '撤退',
        'focus': '集火',
        'swap': '换英雄',
        'switch': '换英雄',
        'tank': '坦克',
        'dps': '输出',
        'damage': '输出',
        'support': '支援',
        'healer': '治疗',
        'ult': '大招',
        'ultimate': '大招',
        'ready': '好了',
        'coming': '来了',
        'here': '在这里',
        'behind': '后面',
        'left': '左边',
        'right': '右边',
        'top': '上面',
        'bottom': '下面',
        'mid': '中间',
        'point': '点位',
        'payload': '运载目标',
        'robot': '机器人',
        'escort': '护送',
        'contest': '占点',
        'cap': '占点',
        'defend': '防守',
        'attack': '进攻',
    }
    
    def __init__(self, translator: Translator):
        self.translator = translator
    
    def parse_message(self, text: str) -> Dict[str, str]:
        """解析聊天消息，分离玩家名和消息内容"""
        for pattern in self.CHAT_PATTERNS:
            match = pattern.match(text)
            if match:
                return {
                    'player': match.group(1),
                    'message': match.group(2).strip()
                }
        
        # 无法解析，返回全部作为消息
        return {
            'player': None,
            'message': text.strip()
        }
    
    def translate_chat(self, text: str) -> TranslationResult:
        """翻译聊天消息"""
        parsed = self.parse_message(text)
        message = parsed['message']
        
        # 先检查快速替换
        lower_msg = message.lower().strip()
        if lower_msg in self.QUICK_REPLACEMENTS:
            translated = self.QUICK_REPLACEMENTS[lower_msg]
            return TranslationResult(
                original=text,
                translated=f"[{parsed['player']}] {translated}" if parsed['player'] else translated,
                source_language="en",
                target_language=self.translator.config.target_language,
                engine="quick_replace",
                timestamp=time.time()
            )
        
        # 正常翻译
        result = self.translator.translate(message)
        
        # 重新组装带玩家名的消息
        if parsed['player']:
            result.original = f"[{parsed['player']}] {message}"
            result.translated = f"[{parsed['player']}] {result.translated}"
        
        return result
    
    def is_game_related(self, text: str) -> bool:
        """判断是否是游戏相关消息（排除菜单文字等）"""
        game_terms = [
            'push', 'heal', 'help', 'ult', 'group', 'focus', 
            'gg', 'wp', 'gl', 'hf', 'ty', 'back', 'go',
            'kill', 'dead', 'spawn', 'point', 'payload',
            'switch', 'swap', 'tank', 'dps', 'support'
        ]
        lower = text.lower()
        return any(term in lower for term in game_terms)


# 测试代码
if __name__ == "__main__":
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from config import translate_config
    
    print("测试翻译模块...")
    
    translator = Translator(translate_config)
    
    # 测试检测语言
    test_texts = [
        "Hello, how are you?",
        "안녕하세요",
        "こんにちは",
        "你好",
        " heals pls",
        "탱커 교체해주세요",
    ]
    
    for text in test_texts:
        lang = translator.detect_language(text)
        print(f"'{text}' -> 检测到语言: {lang}")
    
    # 测试翻译
    if translator._engine_available:
        print("\n测试翻译...")
        for text in test_texts[:2]:
            result = translator.translate(text)
            print(f"{result.original} -> {result.translated}")
    else:
        print("\n翻译引擎不可用，跳过翻译测试")

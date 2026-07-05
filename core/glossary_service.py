"""
OW Glossary Service
OW 游戏术语表服务

从独立 JSON 文件加载游戏术语，支持快速替换和翻译增强。
"""

import json
import os
from typing import Dict, Optional


class OwGlossaryService:
    """OW 术语表服务"""
    
    def __init__(self, glossary_path: Optional[str] = None):
        self._glossary: Dict[str, str] = {}
        self._load(glossary_path)
    
    def _load(self, path: Optional[str]) -> None:
        """加载术语表"""
        if path is None:
            # 默认路径
            base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            path = os.path.join(base, "assets", "glossary.json")
        
        if not os.path.exists(path):
            print(f"[术语表] 文件不存在: {path}")
            return
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self._glossary = data.get("glossary", {})
            print(f"[术语表] 已加载 {len(self._glossary)} 条术语")
        except Exception as e:
            print(f"[术语表] 加载失败: {e}")
    
    def translate(self, text: str) -> Optional[str]:
        """
        术语翻译
        
        Args:
            text: 英文术语（小写，去除多余空格）
            
        Returns:
            中文翻译或 None
        """
        key = text.lower().strip()
        return self._glossary.get(key)
    
    def translate_message(self, text: str) -> str:
        """
        翻译整段消息中的术语
        
        尝试匹配消息中的短语，替换为中文。
        """
        # 先尝试整句匹配
        result = self.translate(text)
        if result:
            return result
        
        # 尝试逐词匹配（简单实现）
        words = text.lower().split()
        translated_words = []
        
        for word in words:
            t = self.translate(word)
            translated_words.append(t if t else word)
        
        # 如果所有词都翻译了，返回翻译结果
        if all(w != word for w, word in zip(translated_words, words)):
            return ' '.join(translated_words)
        
        # 否则返回原文
        return text
    
    def get_all(self) -> Dict[str, str]:
        """获取完整术语表"""
        return self._glossary.copy()
    
    def add(self, en: str, zh: str) -> None:
        """添加新术语"""
        self._glossary[en.lower().strip()] = zh.strip()
    
    def save(self, path: Optional[str] = None) -> None:
        """保存术语表"""
        if path is None:
            base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            path = os.path.join(base, "assets", "glossary.json")
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump({"glossary": self._glossary}, f, ensure_ascii=False, indent=2)


# 单例
glossary_service = OwGlossaryService()


def quick_translate(text: str) -> Optional[str]:
    """快速术语翻译（便捷函数）"""
    return glossary_service.translate(text)

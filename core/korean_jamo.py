"""
Korean Jamo Similarity Matcher
韩语 Jamo 级相似度匹配器

核心思路（移植自 ow-translate-lite）：
- 韩文 Hangul 由 Jamo（字母）组合而成
- OCR 对韩语的识别容易出错：空格缺失、相似字符混淆
- 将韩文拆解为 Jamo，在 Jamo 级别比较相似度
- 结合去空格比较、短消息评分、混淆容错
"""

import re
from typing import List, Tuple


class KoreanJamoNormalizer:
    """韩语 Jamo 归一化器"""
    
    # 常用 Jamo 混淆对（OCR 容易认错的字符）
    JAMO_CONFUSION_PAIRS = {
        # 视觉相似但不同的 Jamo
        '\u1100': '\u1101',  # ㄱ ↔ ㄲ
        '\u1103': '\u1104',  # ㄷ ↔ ㄸ
        '\u1105': '\u1106',  # ㄹ ↔ ㅁ
        '\u1107': '\u1108',  # ㅂ ↔ ㅃ
        '\u1109': '\u110a',  # ㅅ ↔ ㅆ
        '\u110c': '\u110d',  # ㅈ ↔ ㅉ
        '\u110f': '\u1110',  # ㅋ ↔ ㅌ
        '\u1161': '\u1162',  # ㅏ ↔ ㅐ
        '\u1165': '\u1166',  # ㅓ ↔ ㅔ
        '\u1169': '\u116a',  # ㅗ ↔ ㅘ
        '\u1175': '\u1161',  # ㅣ ↔ ㅏ（有时混淆）
    }
    
    # 正反向映射
    CONFUSION_COST = {
        ('\u1100', '\u1101'): 0.5,
        ('\u1103', '\u1104'): 0.5,
        ('\u1107', '\u1108'): 0.5,
        ('\u1109', '\u110a'): 0.5,
        ('\u110c', '\u110d'): 0.5,
        ('\u1161', '\u1162'): 0.3,
        ('\u1165', '\u1166'): 0.3,
    }
    
    @staticmethod
    def decompose_hangul(char: str) -> List[str]:
        """
        将韩文字符拆解为 Jamo
        
        例如: '가' -> ['ㄱ', 'ㅏ']
              '강' -> ['ㄱ', 'ㅏ', 'ㅇ']
        """
        code = ord(char)
        
        # 现代韩文音节范围
        if '\uac00' <= char <= '\ud7a3':
            # 使用 Unicode 韩文组合算法
            base = code - 0xAC00
            
            # 分解为 初声(leading), 中声(vowel), 终声(trailing)
            trailing = base % 28
            vowel = (base // 28) % 21
            leading = base // (28 * 21)
            
            jamos = []
            # 初声 (0x1100-0x1112)
            jamos.append(chr(0x1100 + leading))
            # 中声 (0x1161-0x1175)
            jamos.append(chr(0x1161 + vowel))
            # 终声 (0x11A8-0x11C2)，0 表示没有终声
            if trailing > 0:
                jamos.append(chr(0x11A7 + trailing))
            
            return jamos
        
        # 已经是 Jamo 字符
        if '\u1100' <= char <= '\u11ff':
            return [char]
        
        # 兼容 Jamo (0x3130-0x318F)
        if '\u3130' <= char <= '\u318f':
            return [char]
        
        # 非韩文字符
        return [char]
    
    @classmethod
    def normalize(cls, text: str) -> List[str]:
        """
        将文本归一化为 Jamo 序列
        
        例如: "안녕하세요" -> ['ㅇ', 'ㅏ', 'ㄴ', 'ㄴ', 'ㅕ', 'ㅇ', ...]
        """
        jamos = []
        for char in text:
            jamos.extend(cls.decompose_hangul(char))
        return jamos
    
    @classmethod
    def remove_whitespace(cls, text: str) -> str:
        """移除所有空白"""
        return ''.join(text.split())
    
    @classmethod
    def is_hangul(cls, char: str) -> bool:
        """判断字符是否是韩文"""
        return ('\uac00' <= char <= '\ud7a3' or 
                '\u1100' <= char <= '\u11ff' or
                '\u3130' <= char <= '\u318f')
    
    @classmethod
    def is_mostly_hangul(cls, text: str, threshold: float = 0.5) -> bool:
        """判断文本是否主要由韩文组成"""
        if not text:
            return False
        
        hangul_count = sum(1 for c in text if cls.is_hangul(c))
        return hangul_count / len(text) >= threshold


class KoreanJamoMatcher:
    """韩语 Jamo 匹配器"""
    
    def __init__(self):
        self.normalizer = KoreanJamoNormalizer()
    
    def jamo_distance(self, a: str, b: str) -> float:
        """
        计算两个韩文字符串的 Jamo 编辑距离
        
        Returns:
            距离分数 (0.0 = 完全相同, 1.0 = 完全不同)
        """
        jamos_a = self.normalizer.normalize(a)
        jamos_b = self.normalizer.normalize(b)
        
        # 简单的编辑距离
        m, n = len(jamos_a), len(jamos_b)
        
        # 如果长度差异太大，快速返回
        if abs(m - n) > max(m, n) * 0.5:
            return 1.0
        
        # 动态规划计算编辑距离
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        
        for i in range(m + 1):
            dp[i][0] = i
        for j in range(n + 1):
            dp[0][j] = j
        
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                cost = 0 if jamos_a[i-1] == jamos_b[j-1] else self._substitution_cost(jamos_a[i-1], jamos_b[j-1])
                dp[i][j] = min(
                    dp[i-1][j] + 1,      # 删除
                    dp[i][j-1] + 1,      # 插入
                    dp[i-1][j-1] + cost   # 替换
                )
        
        max_len = max(m, n)
        if max_len == 0:
            return 0.0
        
        return dp[m][n] / max_len
    
    def _substitution_cost(self, a: str, b: str) -> float:
        """替换代价（考虑 Jamo 混淆）"""
        if a == b:
            return 0.0
        
        # 检查是否是已知混淆对
        pair = tuple(sorted([a, b]))
        if pair in KoreanJamoNormalizer.CONFUSION_COST:
            return KoreanJamoNormalizer.CONFUSION_COST[pair]
        
        # 默认替换代价
        return 1.0
    
    def is_similar(self, a: str, b: str, threshold: float = 0.3) -> bool:
        """
        判断两个韩文字符串是否相似
        
        Args:
            a, b: 要比较的字符串
            threshold: 相似度阈值（Jamo 距离 < threshold 视为相似）
            
        Returns:
            True if 相似
        """
        # 先尝试完全匹配（包括去空格）
        if a == b:
            return True
        
        # 去空格比较
        a_nows = KoreanJamoNormalizer.remove_whitespace(a)
        b_nows = KoreanJamoNormalizer.remove_whitespace(b)
        if a_nows == b_nows:
            return True
        
        # 检查是否主要由韩文
        if not (KoreanJamoNormalizer.is_mostly_hangul(a) or 
                KoreanJamoNormalizer.is_mostly_hangul(b)):
            # 非韩文文本，用普通比较
            return a.lower().strip() == b.lower().strip()
        
        # Jamo 距离
        dist = self.jamo_distance(a, b)
        return dist < threshold
    
    def score_korean_message(self, text: str) -> float:
        """
        给韩语消息评分（用于短韩语消息特殊处理）
        
        短韩语消息（1-3 个字符）OCR 抖动更大，需要更宽容的匹配。
        
        Returns:
            分数 (0.0-1.0)，越高越可能是有效消息
        """
        if not text:
            return 0.0
        
        # 长度评分
        length_score = min(len(text) / 5.0, 1.0)
        
        # 韩文比例评分
        hangul_ratio = sum(1 for c in text if KoreanJamoNormalizer.is_hangul(c)) / len(text)
        
        # 短消息特殊加分
        short_bonus = 1.0 if len(text) <= 3 else 0.0
        
        return (length_score * 0.3 + hangul_ratio * 0.5 + short_bonus * 0.2)


# 测试
if __name__ == "__main__":
    matcher = KoreanJamoMatcher()
    
    # 测试相同文本
    assert matcher.is_similar("안녕하세요", "안녕하세요")
    print("✓ 相同文本匹配")
    
    # 测试去空格
    assert matcher.is_similar("안녕 하세요", "안녕하세요")
    print("✓ 去空格匹配")
    
    # 测试 Jamo 距离
    dist = matcher.jamo_distance("안녕", "안년")
    print(f"✓ Jamo 距离: 안녕 vs 안년 = {dist:.2f}")
    
    # 测试短消息
    score = matcher.score_korean_message("ㅎㅇ")
    print(f"✓ 短消息评分: ㅎㅇ = {score:.2f}")
    
    print("\n所有测试通过！")

"""
Timeline-based Chat Message Alignment System
基于时间线的聊天消息对齐系统

核心思路（移植自 ow-translate-lite）：
- 不用文本相似度去重，而是用消息在聊天框中的"顺序位置"去重
- 维护一个权威时间线，OCR 看到的当前区域作为时间线的"可见后缀"来对齐
- 对齐上的就是旧消息，对齐不上的才是新消息
- 解决：OCR 抖动、多人连续发言、打开聊天历史时的重复和乱序
"""

import re
from typing import List, Optional, Tuple, Dict
from dataclasses import dataclass, field
from collections import deque


@dataclass
class ChatMessage:
    """聊天消息"""
    seq: int              # 时间线序号（0-based）
    player: Optional[str] # 玩家名
    text: str             # 消息正文
    raw: str              # 原始完整文本
    language: str = "en"  # 检测到的语言
    translated: str = ""  # 翻译结果
    confirmed: bool = False  # 是否经过多帧共识确认
    
    def __hash__(self):
        return hash((self.player, self.text))
    
    def __eq__(self, other):
        if not isinstance(other, ChatMessage):
            return False
        return self.player == other.player and self.text == other.text


@dataclass
class TimelineSnapshot:
    """时间线快照 - 某一帧 OCR 看到的内容"""
    messages: List[ChatMessage]
    timestamp: float


class OwChatParser:
    """OW 专用聊天解析器
    
    专门解析守望先锋聊天格式：
    - [玩家名]: 消息正文
    - 玩家名: 消息正文
    - <玩家名> 消息正文
    """
    
    # OW 聊天模式
    CHAT_PATTERNS = [
        re.compile(r'\[([^\]]+)\]:\s*(.+)'),      # [玩家名]: 消息
        re.compile(r'([^:]+):\s*(.+)'),            # 玩家名: 消息（注意：要排除 URL）
        re.compile(r'<([^>]+)>\s*(.+)'),          # <玩家名> 消息
    ]
    
    # 系统消息过滤（不翻译这些）
    SYSTEM_PATTERNS = [
        re.compile(r'^(正在加入|已加入|离开|成就|获得|奖励|等级|经验|竞技|排位)', re.I),
        re.compile(r'^\d+/\d+'),  # 像 3/6 这样的数字
        re.compile(r'^\d{1,2}:\d{2}'),  # 时间格式
    ]
    
    @classmethod
    def parse(cls, raw_text: str) -> Optional[ChatMessage]:
        """解析单条聊天消息
        
        Args:
            raw_text: OCR 识别出的原始文本
            
        Returns:
            ChatMessage 或 None（如果不是玩家消息）
        """
        text = raw_text.strip()
        if not text or len(text) < 2:
            return None
        
        # 过滤系统消息
        for pattern in cls.SYSTEM_PATTERNS:
            if pattern.match(text):
                return None
        
        # 尝试匹配玩家消息格式
        for pattern in cls.CHAT_PATTERNS:
            match = pattern.match(text)
            if match:
                player = match.group(1).strip()
                message = match.group(2).strip()
                
                # 过滤太短的消息
                if len(message) < 1:
                    return None
                
                return ChatMessage(
                    seq=-1,  # 稍后由 Timeline 分配
                    player=player,
                    text=message,
                    raw=text
                )
        
        # 没有匹配到格式，可能是不带玩家名的纯消息
        # 也可能不是玩家聊天（如 UI 文字）
        return None
    
    @classmethod
    def parse_multi(cls, raw_texts: List[str]) -> List[ChatMessage]:
        """批量解析"""
        messages = []
        for text in raw_texts:
            msg = cls.parse(text)
            if msg:
                messages.append(msg)
        return messages


class TimelineAlignmentDetector:
    """时间线对齐检测器
    
    核心算法：
    1. 维护一个权威时间线（已确认的消息序列）
    2. 每次 OCR 结果作为"可见后缀"，尝试与权威时间线对齐
    3. 对齐上的就是旧消息（已有翻译），对齐不上的是新候选
    4. 新候选需要多帧共识才能入时间线
    """
    
    def __init__(self, max_history: int = 50):
        self.timeline: deque = deque(maxlen=max_history)  # 权威时间线
        self.next_seq: int = 0  # 下一个序号
        self._parser = OwChatParser()
    
    def _align(self, new_messages: List[ChatMessage]) -> Tuple[List[ChatMessage], List[ChatMessage]]:
        """
        将新消息与权威时间线对齐
        
        返回: (matched_old, unmatched_candidates)
        - matched_old: 对齐上的旧消息（已有翻译）
        - unmatched_candidates: 对齐不上的新候选
        
        对齐策略：
        1. 从时间线末尾开始，向前匹配
        2. 要求连续匹配（不能跳过）
        3. 一旦匹配断裂，剩余的就是新候选
        """
        if not new_messages:
            return [], []
        
        timeline_list = list(self.timeline)
        if not timeline_list:
            # 时间线为空，所有都是新候选
            return [], new_messages
        
        # 从时间线末尾向前匹配
        # 新消息是"可见后缀"，应该匹配时间线的最后部分
        matched = []
        unmatched = []
        
        # 简单实现：从时间线末尾开始，逐个匹配
        ti = len(timeline_list) - 1  # timeline index
        ni = len(new_messages) - 1    # new message index
        
        match_map = {}  # new_index -> timeline_msg
        
        while ti >= 0 and ni >= 0:
            t_msg = timeline_list[ti]
            n_msg = new_messages[ni]
            
            if self._message_matches(t_msg, n_msg):
                match_map[ni] = t_msg
                ti -= 1
                ni -= 1
            else:
                # 不匹配，可能是新消息插入了，或者 OCR 漏了
                # 向前继续尝试（OCR 可能漏了中间的消息）
                ti -= 1
        
        # 分类
        for i, msg in enumerate(new_messages):
            if i in match_map:
                matched.append(match_map[i])
            else:
                unmatched.append(msg)
        
        return matched, unmatched
    
    def _message_matches(self, a: ChatMessage, b: ChatMessage) -> bool:
        """判断两条消息是否是同一条
        
        匹配策略：
        1. 玩家名相同 + 文本相同 → 匹配
        2. 玩家名相同 + 文本高度相似 → 匹配（OCR 抖动容错）
        3. 文本相同（玩家名为空）→ 匹配
        """
        # 玩家名匹配
        player_match = (a.player == b.player) or (a.player is None and b.player is None)
        
        # 文本匹配
        text_match = (a.text == b.text)
        
        if player_match and text_match:
            return True
        
        # 容错：玩家名相同，文本相似度高
        if player_match and a.player is not None:
            sim = self._text_similarity(a.text, b.text)
            if sim >= 0.85:
                return True
        
        return False
    
    def _text_similarity(self, a: str, b: str) -> float:
        """计算两个字符串的相似度"""
        if a == b:
            return 1.0
        
        a_lower = a.lower().strip()
        b_lower = b.lower().strip()
        
        if a_lower == b_lower:
            return 0.95
        
        # 集合相似度
        set_a = set(a_lower)
        set_b = set(b_lower)
        if not set_a or not set_b:
            return 0.0
        
        intersection = len(set_a & set_b)
        union = len(set_a | set_b)
        return intersection / union if union > 0 else 0.0
    
    def process_frame(self, raw_texts: List[str]) -> Tuple[List[ChatMessage], List[ChatMessage]]:
        """
        处理一帧 OCR 结果
        
        Args:
            raw_texts: OCR 识别出的原始文本列表（从上到下）
            
        Returns:
            (confirmed_new_messages, all_visible_messages)
            - confirmed_new_messages: 新确认的消息（需要翻译）
            - all_visible_messages: 当前可见的所有消息（用于显示）
        """
        # 1. 解析
        new_messages = self._parser.parse_multi(raw_texts)
        
        # 2. 对齐
        matched, candidates = self._align(new_messages)
        
        # 3. 确认新消息
        confirmed = []
        for msg in candidates:
            msg.seq = self.next_seq
            self.next_seq += 1
            self.timeline.append(msg)
            confirmed.append(msg)
        
        # 4. 构建完整可见消息列表
        visible = []
        for msg in new_messages:
            # 如果是新确认的，用新版本
            # 如果是旧消息，用时间线中的版本（保留翻译）
            found_in_timeline = None
            for t_msg in self.timeline:
                if self._message_matches(t_msg, msg):
                    found_in_timeline = t_msg
                    break
            
            if found_in_timeline:
                visible.append(found_in_timeline)
            else:
                visible.append(msg)
        
        return confirmed, visible
    
    def get_timeline(self) -> List[ChatMessage]:
        """获取完整时间线"""
        return list(self.timeline)
    
    def clear(self) -> None:
        """清空时间线"""
        self.timeline.clear()
        self.next_seq = 0


class MultiFrameConsensus:
    """多帧共识器
    
    新消息不立刻翻译，而是经过多帧观察：
    - 连续两帧一致 → 确认
    - 韩语消息：Jamo 距离足够近 → 确认
    
    这样可以吸收 OCR 对短文本、空格、相近字符的轻微抖动。
    """
    
    def __init__(self, required_frames: int = 2):
        self.required_frames = required_frames
        self._candidates: Dict[int, List[ChatMessage]] = {}  # seq -> 帧历史
        self._confirmed: set = set()  # 已确认的 seq
    
    def observe(self, msg: ChatMessage) -> bool:
        """
        观察一条消息
        
        Returns:
            True if 该消息已达成共识，可以翻译
        """
        if msg.seq in self._confirmed:
            return True
        
        if msg.seq not in self._candidates:
            self._candidates[msg.seq] = []
        
        self._candidates[msg.seq].append(msg)
        
        # 检查是否达到共识
        history = self._candidates[msg.seq]
        if len(history) >= self.required_frames:
            # 检查最近两帧是否一致
            if self._frames_agree(history[-2], history[-1]):
                self._confirmed.add(msg.seq)
                msg.confirmed = True
                return True
        
        return False
    
    def _frames_agree(self, a: ChatMessage, b: ChatMessage) -> bool:
        """检查两帧的消息是否一致"""
        # 玩家名和文本都相同
        if a.player == b.player and a.text == b.text:
            return True
        
        # 韩语特殊处理：Jamo 相似度
        if self._is_korean(a.text) or self._is_korean(b.text):
            from .korean_jamo import KoreanJamoMatcher
            matcher = KoreanJamoMatcher()
            if matcher.is_similar(a.text, b.text):
                return True
        
        return False
    
    def _is_korean(self, text: str) -> bool:
        """判断文本是否包含韩文"""
        for ch in text:
            if '\uac00' <= ch <= '\ud7af' or '\u1100' <= ch <= '\u11ff':
                return True
        return False
    
    def reset(self) -> None:
        """重置共识状态"""
        self._candidates.clear()
        self._confirmed.clear()

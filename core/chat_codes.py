"""
OW Chat Code Generator
守望先锋聊天代码生成器

参考 MapleOAO/overwatch-chat-editor 的代码格式：
- 颜色代码: <FGRRGGBBAA> (Foreground color, 8位十六进制)
- 纹理代码: <TXC...> (Texture code)
- 渐变代码: <FGRRGGBBAA>...<FGRRGGBBAA> (连续颜色标签实现渐变效果)

用途：
1. 让回话消息可以带上 OW 颜色/纹理效果
2. 生成预设模板（如 GG、 thanks、回复等）
"""

import re
from typing import List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class ColorCode:
    """颜色代码"""
    r: int
    g: int
    b: int
    a: int = 255
    
    @property
    def hex_code(self) -> str:
        """生成 OW 颜色代码 <FGRRGGBBAA>"""
        return f"<FG{self.r:02X}{self.g:02X}{self.b:02X}{self.a:02X}>"
    
    @classmethod
    def from_hex(cls, hex_str: str) -> "ColorCode":
        """从十六进制字符串解析"""
        hex_str = hex_str.lstrip('#').lstrip('<FG').rstrip('>')
        if len(hex_str) >= 6:
            r = int(hex_str[0:2], 16)
            g = int(hex_str[2:4], 16)
            b = int(hex_str[4:6], 16)
            a = int(hex_str[6:8], 16) if len(hex_str) >= 8 else 255
            return cls(r, g, b, a)
        return cls(255, 255, 255)
    
    @classmethod
    def from_rgb(cls, r: int, g: int, b: int, a: int = 255) -> "ColorCode":
        return cls(r, g, b, a)


# 预设颜色（常用 OW 聊天颜色）
PRESET_COLORS = {
    "green": ColorCode(0, 255, 0),      # 绿色 - 友好
    "red": ColorCode(255, 0, 0),        # 红色 - 警告/敌对
    "blue": ColorCode(0, 128, 255),     # 蓝色 - 信息
    "yellow": ColorCode(255, 255, 0),   # 黄色 - 注意
    "white": ColorCode(255, 255, 255),  # 白色
    "orange": ColorCode(255, 165, 0),   # 橙色
    "purple": ColorCode(128, 0, 128),   # 紫色
    "cyan": ColorCode(0, 255, 255),     # 青色
    "pink": ColorCode(255, 105, 180),   # 粉色
    "gold": ColorCode(255, 215, 0),     # 金色
}


def color_text(text: str, color: ColorCode) -> str:
    """
    给文本添加颜色代码
    
    Args:
        text: 原文本
        color: 颜色
        
    Returns:
        带颜色代码的文本
    """
    return f"{color.hex_code}{text}"


def gradient_text(text: str, colors: List[ColorCode]) -> str:
    """
    生成渐变色文本
    
    将文本分段，每段应用不同的颜色。
    
    Args:
        text: 原文本
        colors: 颜色列表（至少2个）
        
    Returns:
        带渐变颜色代码的文本
    """
    if len(colors) < 2 or not text:
        return text
    
    segments = len(colors)
    segment_length = max(1, len(text) // segments)
    
    result = []
    for i, color in enumerate(colors):
        start = i * segment_length
        end = start + segment_length if i < segments - 1 else len(text)
        segment = text[start:end]
        if segment:
            result.append(f"{color.hex_code}{segment}")
    
    return "".join(result)


def rainbow_text(text: str) -> str:
    """生成彩虹色文本"""
    colors = [
        ColorCode(255, 0, 0),      # 红
        ColorCode(255, 127, 0),    # 橙
        ColorCode(255, 255, 0),    # 黄
        ColorCode(0, 255, 0),      # 绿
        ColorCode(0, 0, 255),      # 蓝
        ColorCode(75, 0, 130),     # 靛
        ColorCode(148, 0, 211),    # 紫
    ]
    return gradient_text(text, colors)


def parse_ow_code(code: str) -> str:
    """
    解析 OW 聊天代码，提取纯文本内容
    
    Args:
        code: 带 OW 代码的文本
        
    Returns:
        纯文本（去除所有代码标签）
    """
    # 移除颜色代码 <FGRRGGBBAA>
    text = re.sub(r'<FG[0-9A-Fa-f]{8}>', '', code)
    # 移除纹理代码 <TXC...>
    text = re.sub(r'<TXC[0-9A-Fa-f]+>', '', text)
    # 移除其他标签
    text = re.sub(r'<[^>]+>', '', text)
    return text.strip()


def contains_ow_code(text: str) -> bool:
    """检查文本是否包含 OW 代码"""
    return bool(re.search(r'<(FG|TXC)[0-9A-Fa-f]+>', text))


class OwChatTemplate:
    """OW 聊天模板"""
    
    TEMPLATES = {
        "gg": {
            "name": "GG",
            "description": "打得不错",
            "code": "<FG00FF00FF>GG <FGFFFFFF00>WP!",
        },
        "thanks": {
            "name": "感谢",
            "description": "感谢队友",
            "code": "<FG00FF00FF>Thanks! <FG00FFFFFF>You're awesome!",
        },
        "heal": {
            "name": "需要治疗",
            "description": "请求治疗",
            "code": "<FGFF0000FF>Need <FG00FF00FF>healing!",
        },
        "group": {
            "name": "集合",
            "description": "请求集合",
            "code": "<FGFFFF00FF>Group up!",
        },
        "ult_ready": {
            "name": "大招好了",
            "description": "大招已就绪",
            "code": "<FG00FF00FF>My <FGFFFF00FF>ULT <FG00FF00FF>is ready!",
        },
        "push": {
            "name": "推进",
            "description": "请求推进",
            "code": "<FG00FF00FF>Push!",
        },
        "focus": {
            "name": "集火",
            "description": "请求集火",
            "code": "<FGFF0000FF>Focus <FGFFFF00FF>fire!",
        },
        "nice": {
            "name": "漂亮",
            "description": "称赞队友",
            "code": "<FG00FF00FF>Nice! <FG00FFFFFF>Great play!",
        },
        "back": {
            "name": "后退",
            "description": "请求撤退",
            "code": "<FGFF0000FF>Fall back!",
        },
        "good_luck": {
            "name": "祝好运",
            "description": "开局祝福",
            "code": "<FG00FF00FF>GL <FG00FFFFFF>HF!",
        },
    }
    
    @classmethod
    def get(cls, key: str) -> Optional[str]:
        """获取模板代码"""
        template = cls.TEMPLATES.get(key)
        return template["code"] if template else None
    
    @classmethod
    def list_templates(cls) -> List[Tuple[str, str, str]]:
        """列出所有模板"""
        return [
            (key, t["name"], t["description"])
            for key, t in cls.TEMPLATES.items()
        ]
    
    @classmethod
    def get_plain_text(cls, key: str) -> str:
        """获取模板的纯文本"""
        code = cls.get(key)
        return parse_ow_code(code) if code else ""


# 快捷函数
def gg() -> str: return OwChatTemplate.get("gg")
def thanks() -> str: return OwChatTemplate.get("thanks")
def heal() -> str: return OwChatTemplate.get("heal")
def group_up() -> str: return OwChatTemplate.get("group")


# 测试
if __name__ == "__main__":
    print("=== OW 聊天代码测试 ===")
    
    # 测试颜色
    print("\n1. 颜色文本:")
    print(f"  绿色: {color_text('Hello', PRESET_COLORS['green'])}")
    print(f"  红色: {color_text('Warning', PRESET_COLORS['red'])}")
    
    # 测试渐变
    print("\n2. 渐变文本:")
    gradient_colors = [ColorCode(255, 0, 0), ColorCode(255, 255, 0), ColorCode(0, 255, 0)]
    print(f"  {gradient_text('Rainbow', gradient_colors)}")
    
    # 测试彩虹
    print("\n3. 彩虹文本:")
    print(f"  {rainbow_text('Overwatch')}")
    
    # 测试模板
    print("\n4. 预设模板:")
    for key, name, desc in OwChatTemplate.list_templates():
        code = OwChatTemplate.get(key)
        plain = OwChatTemplate.get_plain_text(key)
        print(f"  [{name}] {plain}")
        print(f"    代码: {code}")
    
    # 测试解析
    print("\n5. 解析测试:")
    test_code = "<FG00FF00FF>GG <FGFFFFFF00>WP!"
    print(f"  原文: {test_code}")
    print(f"  解析: {parse_ow_code(test_code)}")
    
    print("\n=== 测试完成 ===")

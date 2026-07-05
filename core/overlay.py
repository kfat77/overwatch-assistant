"""
Overwatch Assistant - Overlay Module
透明叠加层显示模块

在游戏画面上方显示翻译结果和英雄推荐。
"""

import time
import threading
from typing import List, Optional, Callable
from dataclasses import dataclass, field
from collections import deque

try:
    import tkinter as tk
    from tkinter import ttk
except ImportError:
    raise ImportError("tkinter 不可用，请安装 Python 的 tkinter 支持")


@dataclass
class OverlayMessage:
    """叠加层消息"""
    text: str
    original: str = ""
    message_type: str = "translation"  # translation, recommendation, system
    timestamp: float = field(default_factory=time.time)
    color: str = "#00ff88"
    ttl: float = 15.0  # 0 = 永久显示
    
    def is_expired(self) -> bool:
        if self.ttl <= 0:
            return False
        return time.time() - self.timestamp > self.ttl


class OverlayWindow:
    """透明叠加层窗口"""
    
    def __init__(self, config):
        self.config = config
        self._root: Optional[tk.Tk] = None
        self._canvas: Optional[tk.Canvas] = None
        self._text_items: List[int] = []
        self._messages: deque = deque(maxlen=config.max_messages)
        self._lock = threading.Lock()
        self._visible = False
        self._running = False
        self._ui_thread: Optional[threading.Thread] = None
        self._drag_data = {"x": 0, "y": 0, "dragging": False}
        
    def start(self) -> None:
        """启动叠加层窗口（在独立线程中）"""
        if self._running:
            return
        
        self._running = True
        self._ui_thread = threading.Thread(target=self._run_ui, daemon=True)
        self._ui_thread.start()
        
        # 等待窗口创建
        import time
        for _ in range(50):
            if self._root is not None:
                break
            time.sleep(0.1)
    
    def _run_ui(self) -> None:
        """UI 主循环"""
        self._root = tk.Tk()
        self._root.title("OW 辅助")
        
        # 窗口设置
        self._root.geometry(f"{self.config.width}x{self.config.height}+{self.config.position_x}+{self.config.position_y}")
        self._root.overrideredirect(True)  # 无边框
        self._root.attributes('-topmost', self.config.always_on_top)
        self._root.attributes('-alpha', self.config.opacity)
        
        # 背景
        r, g, b, a = self.config.bg_color
        bg_hex = f'#{r:02x}{g:02x}{b:02x}'
        self._root.configure(bg=bg_hex)
        
        # Canvas
        self._canvas = tk.Canvas(
            self._root,
            width=self.config.width,
            height=self.config.height,
            bg=bg_hex,
            highlightthickness=0
        )
        self._canvas.pack(fill=tk.BOTH, expand=True)
        
        # 绑定拖拽事件
        if self.config.draggable:
            self._canvas.bind("<Button-1>", self._on_drag_start)
            self._canvas.bind("<B1-Motion>", self._on_drag)
            self._canvas.bind("<ButtonRelease-1>", self._on_drag_end)
        
        # 右键菜单
        self._setup_context_menu()
        
        # 标题栏
        self._draw_header()
        
        # 启动更新循环
        self._schedule_update()
        
        self._visible = True
        self._root.mainloop()
    
    def _setup_context_menu(self) -> None:
        """设置右键菜单"""
        self._menu = tk.Menu(self._root, tearoff=0, bg='#333333', fg='white')
        self._menu.add_command(label="置顶/取消置顶", command=self._toggle_topmost)
        self._menu.add_command(label="清空消息", command=self.clear_messages)
        self._menu.add_separator()
        self._menu.add_command(label="退出", command=self.stop)
        
        self._canvas.bind("<Button-3>", self._show_menu)
        self._canvas.bind("<Button-2>", self._show_menu)  # macOS 右键
    
    def _show_menu(self, event) -> None:
        """显示右键菜单"""
        self._menu.post(event.x_root, event.y_root)
    
    def _toggle_topmost(self) -> None:
        """切换置顶状态"""
        self.config.always_on_top = not self.config.always_on_top
        self._root.attributes('-topmost', self.config.always_on_top)
    
    def _draw_header(self) -> None:
        """绘制标题栏"""
        header_bg = self._canvas.create_rectangle(
            0, 0, self.config.width, 28,
            fill='#2a2a3a', outline=''
        )
        
        self._canvas.create_text(
            10, 14, text="守望先锋辅助", 
            fill=self.config.header_color,
            font=(self.config.font_family, 11, 'bold'),
            anchor='w'
        )
        
        # 关闭按钮
        close_btn = self._canvas.create_text(
            self.config.width - 15, 14, text="×",
            fill='#ff6666', font=(self.config.font_family, 14, 'bold'),
            anchor='e'
        )
        self._canvas.tag_bind(close_btn, "<Button-1>", lambda e: self.hide())
    
    def _on_drag_start(self, event) -> None:
        """开始拖拽"""
        self._drag_data["x"] = event.x_root - self._root.winfo_x()
        self._drag_data["y"] = event.y_root - self._root.winfo_y()
        self._drag_data["dragging"] = True
    
    def _on_drag(self, event) -> None:
        """拖拽中"""
        if self._drag_data["dragging"]:
            x = event.x_root - self._drag_data["x"]
            y = event.y_root - self._drag_data["y"]
            self._root.geometry(f"+{x}+{y}")
    
    def _on_drag_end(self, event) -> None:
        """结束拖拽"""
        self._drag_data["dragging"] = False
    
    def _schedule_update(self) -> None:
        """定时更新显示"""
        if not self._running or self._root is None:
            return
        
        self._update_display()
        self._root.after(500, self._schedule_update)
    
    def _update_display(self) -> None:
        """更新显示内容"""
        with self._lock:
            # 清理过期消息
            self._messages = deque(
                [m for m in self._messages if not m.is_expired()],
                maxlen=self.config.max_messages
            )
            
            # 清除旧文本
            for item_id in self._text_items:
                self._canvas.delete(item_id)
            self._text_items.clear()
            
            # 重新绘制消息
            y_offset = 35  # 标题栏下方
            line_height = 20
            
            for msg in self._messages:
                # 根据类型选择颜色
                color = msg.color
                if msg.message_type == "translation":
                    color = self.config.text_color
                elif msg.message_type == "recommendation":
                    color = "#ffaa44"
                elif msg.message_type == "system":
                    color = "#66aaff"
                
                # 绘制原文（如果有且不是系统消息）
                if msg.original and msg.message_type == "translation":
                    orig_text = self._canvas.create_text(
                        10, y_offset,
                        text=f"原文: {msg.original[:60]}",
                        fill=self.config.original_color,
                        font=(self.config.font_family, 9),
                        anchor='nw',
                        width=self.config.width - 20
                    )
                    self._text_items.append(orig_text)
                    y_offset += 16
                
                # 绘制翻译/消息
                display_text = msg.text[:100] if len(msg.text) > 100 else msg.text
                text_item = self._canvas.create_text(
                    10, y_offset,
                    text=display_text,
                    fill=color,
                    font=(self.config.font_family, self.config.font_size),
                    anchor='nw',
                    width=self.config.width - 20
                )
                self._text_items.append(text_item)
                
                # 计算文本高度
                bbox = self._canvas.bbox(text_item)
                if bbox:
                    text_height = bbox[3] - bbox[1]
                    y_offset += text_height + 10
                else:
                    y_offset += line_height + 5
    
    def add_message(self, text: str, 
                   original: str = "",
                   message_type: str = "translation",
                   color: Optional[str] = None,
                   ttl: Optional[float] = None) -> None:
        """
        添加消息到叠加层
        
        Args:
            text: 显示文本
            original: 原文（翻译时）
            message_type: 消息类型
            color: 自定义颜色
            ttl: 停留时间
        """
        msg = OverlayMessage(
            text=text,
            original=original,
            message_type=message_type,
            color=color or self.config.text_color,
            ttl=ttl if ttl is not None else self.config.message_ttl
        )
        
        with self._lock:
            self._messages.append(msg)
    
    def add_translation(self, original: str, translated: str) -> None:
        """添加翻译结果"""
        self.add_message(
            text=translated,
            original=original,
            message_type="translation"
        )
    
    def add_recommendation(self, recommendation: str) -> None:
        """添加英雄推荐"""
        self.add_message(
            text=recommendation,
            message_type="recommendation",
            color="#ffaa44",
            ttl=20.0
        )
    
    def add_system_message(self, text: str) -> None:
        """添加系统消息"""
        self.add_message(
            text=text,
            message_type="system",
            color="#66aaff",
            ttl=5.0
        )
    
    def clear_messages(self) -> None:
        """清空所有消息"""
        with self._lock:
            self._messages.clear()
    
    def show(self) -> None:
        """显示窗口"""
        if self._root:
            self._root.deiconify()
            self._visible = True
    
    def hide(self) -> None:
        """隐藏窗口"""
        if self._root:
            self._root.withdraw()
            self._visible = False
    
    def toggle(self) -> None:
        """切换显示/隐藏"""
        if self._visible:
            self.hide()
        else:
            self.show()
    
    def stop(self) -> None:
        """关闭叠加层"""
        self._running = False
        if self._root:
            self._root.quit()
            self._root.destroy()
            self._root = None
    
    @property
    def is_visible(self) -> bool:
        return self._visible
    
    @property
    def is_running(self) -> bool:
        return self._running


class CompactOverlay(OverlayWindow):
    """精简版叠加层 - 只显示最新一条消息"""
    
    def _update_display(self) -> None:
        """精简显示 - 只显示最新消息"""
        with self._lock:
            # 清理过期消息
            self._messages = deque(
                [m for m in self._messages if not m.is_expired()],
                maxlen=1  # 只保留一条
            )
            
            # 清除旧文本
            for item_id in self._text_items:
                self._canvas.delete(item_id)
            self._text_items.clear()
            
            if not self._messages:
                # 显示等待提示
                item = self._canvas.create_text(
                    self.config.width // 2, self.config.height // 2,
                    text="等待消息...",
                    fill="#555555",
                    font=(self.config.font_family, 11),
                    anchor='center'
                )
                self._text_items.append(item)
                return
            
            # 只显示最新一条
            msg = self._messages[-1]
            color = msg.color
            
            # 原文
            if msg.original:
                orig = self._canvas.create_text(
                    10, 35,
                    text=f"原文: {msg.original[:50]}",
                    fill=self.config.original_color,
                    font=(self.config.font_family, 9),
                    anchor='nw',
                    width=self.config.width - 20
                )
                self._text_items.append(orig)
                
                translated = self._canvas.create_text(
                    10, 55,
                    text=msg.text[:80],
                    fill=color,
                    font=(self.config.font_family, 12, 'bold'),
                    anchor='nw',
                    width=self.config.width - 20
                )
                self._text_items.append(translated)
            else:
                text_item = self._canvas.create_text(
                    10, 40,
                    text=msg.text[:80],
                    fill=color,
                    font=(self.config.font_family, 12, 'bold'),
                    anchor='nw',
                    width=self.config.width - 20
                )
                self._text_items.append(text_item)


# 测试代码
if __name__ == "__main__":
    import sys
    import os
    import time
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from config import overlay_config
    
    print("测试叠加层...")
    
    overlay = OverlayWindow(overlay_config)
    overlay.start()
    
    # 等待窗口启动
    time.sleep(2)
    
    # 添加测试消息
    overlay.add_translation("hello everyone", "大家好")
    time.sleep(1)
    overlay.add_translation("heal me please", "请治疗我")
    time.sleep(1)
    overlay.add_recommendation("推荐: 安娜 - 当前阵容缺少远程治疗")
    time.sleep(1)
    overlay.add_system_message("系统已启动")
    
    print("叠加层测试中，按 Ctrl+C 退出...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        overlay.stop()
        print("已退出")

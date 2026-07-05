"""
Overwatch Assistant - Enhanced Overlay Module
增强型透明叠加层显示模块

功能改进（参考 ow-translate-lite）：
- 历史消息滚动
- 鼠标穿透（点击穿透到游戏）
- 拖动缩放
- 回话输入栏
- 更好的消息显示和管理
"""

import time
import threading
import ctypes
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
    message_type: str = "translation"  # translation, recommendation, system, reply
    timestamp: float = field(default_factory=time.time)
    color: str = "#00ff88"
    ttl: float = 15.0  # 0 = 永久显示
    player: Optional[str] = None  # 玩家名（如果有）
    
    def is_expired(self) -> bool:
        if self.ttl <= 0:
            return False
        return time.time() - self.timestamp > self.ttl


class OverlayWindow:
    """增强型透明叠加层窗口"""
    
    def __init__(self, config):
        self.config = config
        self._root: Optional[tk.Tk] = None
        self._canvas: Optional[tk.Canvas] = None
        self._scrollbar: Optional[tk.Scrollbar] = None
        self._text_items: List[int] = []
        self._messages: deque = deque(maxlen=config.max_messages)
        self._lock = threading.Lock()
        self._visible = False
        self._running = False
        self._ui_thread: Optional[threading.Thread] = None
        
        # 拖拽
        self._drag_data = {"x": 0, "y": 0, "dragging": False}
        
        # 鼠标穿透
        self._click_through = False
        
        # 缩放
        self._scale = 1.0
        
        # 回话输入
        self._reply_frame: Optional[tk.Frame] = None
        self._reply_entry: Optional[tk.Entry] = None
        self._reply_lang_var: Optional[tk.StringVar] = None
        self._on_reply: Optional[Callable[[str, str], None]] = None
        
        # 统计
        self._message_count = 0
    
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
        
        # 主容器（带滚动条）
        main_frame = tk.Frame(self._root, bg=bg_hex)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题栏
        header_frame = tk.Frame(main_frame, bg='#2a2a3a', height=28)
        header_frame.pack(fill=tk.X, side=tk.TOP)
        header_frame.pack_propagate(False)
        
        title_label = tk.Label(
            header_frame, text="守望先锋辅助",
            fg=self.config.header_color,
            bg='#2a2a3a',
            font=(self.config.font_family, 11, 'bold'),
            anchor='w', padx=10
        )
        title_label.pack(side=tk.LEFT, fill=tk.Y)
        
        # 控制按钮
        btn_frame = tk.Frame(header_frame, bg='#2a2a3a')
        btn_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5)
        
        # 鼠标穿透切换
        self._clickthrough_btn = tk.Label(
            btn_frame, text="🖱️", font=('Segoe UI Emoji', 10),
            bg='#2a2a3a', fg='#888888', cursor='hand2'
        )
        self._clickthrough_btn.pack(side=tk.LEFT, padx=2)
        self._clickthrough_btn.bind("<Button-1>", lambda e: self._toggle_clickthrough())
        
        # 最小化/隐藏
        hide_btn = tk.Label(
            btn_frame, text="−", font=('Arial', 14, 'bold'),
            bg='#2a2a3a', fg='#aaaaaa', cursor='hand2'
        )
        hide_btn.pack(side=tk.LEFT, padx=2)
        hide_btn.bind("<Button-1>", lambda e: self.hide())
        
        # 关闭
        close_btn = tk.Label(
            btn_frame, text="×", font=('Arial', 14, 'bold'),
            bg='#2a2a3a', fg='#ff6666', cursor='hand2'
        )
        close_btn.pack(side=tk.LEFT, padx=2)
        close_btn.bind("<Button-1>", lambda e: self.stop())
        
        # Canvas + 滚动条
        canvas_frame = tk.Frame(main_frame, bg=bg_hex)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        self._scrollbar = tk.Scrollbar(canvas_frame, orient=tk.VERTICAL)
        self._scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self._canvas = tk.Canvas(
            canvas_frame,
            bg=bg_hex,
            highlightthickness=0,
            yscrollcommand=self._scrollbar.set
        )
        self._canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._scrollbar.config(command=self._canvas.yview)
        
        # 绑定滚动
        self._canvas.bind("<MouseWheel>", self._on_mousewheel)
        self._canvas.bind("<Button-4>", lambda e: self._canvas.yview_scroll(-1, 'units'))
        self._canvas.bind("<Button-5>", lambda e: self._canvas.yview_scroll(1, 'units'))
        
        # 绑定拖拽
        header_frame.bind("<Button-1>", self._on_drag_start)
        header_frame.bind("<B1-Motion>", self._on_drag)
        header_frame.bind("<ButtonRelease-1>", self._on_drag_end)
        title_label.bind("<Button-1>", self._on_drag_start)
        title_label.bind("<B1-Motion>", self._on_drag)
        title_label.bind("<ButtonRelease-1>", self._on_drag_end)
        
        # 右键菜单
        self._setup_context_menu()
        
        # 回话输入栏
        self._setup_reply_bar(main_frame)
        
        # 启动更新循环
        self._schedule_update()
        
        self._visible = True
        self._root.mainloop()
    
    def _setup_context_menu(self) -> None:
        """设置右键菜单"""
        self._menu = tk.Menu(self._root, tearoff=0, bg='#333333', fg='white')
        self._menu.add_command(label="置顶/取消置顶", command=self._toggle_topmost)
        self._menu.add_command(label="切换鼠标穿透", command=self._toggle_clickthrough)
        self._menu.add_separator()
        self._menu.add_command(label="清空消息", command=self.clear_messages)
        self._menu.add_command(label="清空时间线", command=self.clear_timeline)
        self._menu.add_separator()
        self._menu.add_command(label="退出", command=self.stop)
        
        self._canvas.bind("<Button-3>", self._show_menu)
        self._canvas.bind("<Button-2>", self._show_menu)
    
    def _setup_reply_bar(self, parent: tk.Frame) -> None:
        """设置回话输入栏"""
        self._reply_frame = tk.Frame(parent, bg='#2a2a3a', height=32)
        self._reply_frame.pack(fill=tk.X, side=tk.BOTTOM)
        self._reply_frame.pack_propagate(False)
        
        # 语言选择
        self._reply_lang_var = tk.StringVar(value="auto")
        lang_menu = tk.OptionMenu(
            self._reply_frame, self._reply_lang_var,
            "auto", "en", "ko", "ja"
        )
        lang_menu.config(
            bg='#2a2a3a', fg='#00ff88',
            activebackground='#3a3a4a', activeforeground='#00ff88',
            highlightthickness=0, bd=0, width=6
        )
        lang_menu["menu"].config(bg='#2a2a3a', fg='white')
        lang_menu.pack(side=tk.LEFT, padx=2, pady=2)
        
        # 输入框
        self._reply_entry = tk.Entry(
            self._reply_frame,
            bg='#1a1a2a', fg='white',
            insertbackground='white',
            font=(self.config.font_family, 10),
            bd=0, highlightthickness=1,
            highlightcolor='#00ff88', highlightbackground='#333333'
        )
        self._reply_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2, pady=4)
        self._reply_entry.bind("<Return>", self._on_reply_submit)
        self._reply_entry.bind("<KP_Enter>", self._on_reply_submit)
        
        # 发送按钮
        send_btn = tk.Label(
            self._reply_frame, text="📋",
            bg='#2a2a3a', fg='#00ff88',
            font=('Segoe UI Emoji', 12), cursor='hand2'
        )
        send_btn.pack(side=tk.RIGHT, padx=4, pady=2)
        send_btn.bind("<Button-1>", self._on_reply_submit)
        
        # 默认隐藏回话栏
        self._reply_frame.pack_forget()
    
    def show_reply_bar(self, show: bool = True) -> None:
        """显示/隐藏回话栏"""
        if self._reply_frame and self._root:
            if show:
                self._reply_frame.pack(fill=tk.X, side=tk.BOTTOM, before=self._root.winfo_children()[0] if self._root.winfo_children() else None)
            else:
                self._reply_frame.pack_forget()
    
    def set_reply_callback(self, callback: Callable[[str, str], None]) -> None:
        """设置回话回调"""
        self._on_reply = callback
    
    def _on_reply_submit(self, event=None) -> None:
        """提交回话"""
        if self._reply_entry and self._on_reply:
            text = self._reply_entry.get().strip()
            if text:
                lang = self._reply_lang_var.get() if self._reply_lang_var else "auto"
                self._on_reply(text, lang)
                self._reply_entry.delete(0, tk.END)
    
    def _on_mousewheel(self, event) -> None:
        """鼠标滚轮"""
        if self._canvas:
            self._canvas.yview_scroll(int(-1 * (event.delta / 120)), 'units')
    
    def _show_menu(self, event) -> None:
        """显示右键菜单"""
        self._menu.post(event.x_root, event.y_root)
    
    def _toggle_topmost(self) -> None:
        """切换置顶状态"""
        self.config.always_on_top = not self.config.always_on_top
        if self._root:
            self._root.attributes('-topmost', self.config.always_on_top)
    
    def _toggle_clickthrough(self) -> None:
        """切换鼠标穿透"""
        self._click_through = not self._click_through
        self._apply_clickthrough()
        
        if self._clickthrough_btn:
            self._clickthrough_btn.config(
                fg='#00ff88' if self._click_through else '#888888'
            )
        
        print(f"[叠加层] 鼠标穿透: {'开启' if self._click_through else '关闭'}")
    
    def _apply_clickthrough(self) -> None:
        """应用鼠标穿透（Windows API）"""
        if not self._root:
            return
        
        try:
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            # 获取当前扩展样式
            GWL_EXSTYLE = -20
            WS_EX_TRANSPARENT = 0x00000020
            WS_EX_LAYERED = 0x00080000
            
            style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            
            if self._click_through:
                style |= WS_EX_TRANSPARENT
            else:
                style &= ~WS_EX_TRANSPARENT
            
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
        except Exception as e:
            print(f"[叠加层] 鼠标穿透设置失败: {e}")
    
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
            y_offset = 10
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
                elif msg.message_type == "reply":
                    color = "#ff88cc"
                
                # 玩家名
                display_text = msg.text
                if msg.player:
                    display_text = f"[{msg.player}] {msg.text}"
                
                # 绘制原文（如果有且是翻译）
                if msg.original and msg.message_type == "translation":
                    orig_text = f"原文: {msg.original[:60]}"
                    orig_item = self._canvas.create_text(
                        10, y_offset,
                        text=orig_text,
                        fill=self.config.original_color,
                        font=(self.config.font_family, 9),
                        anchor='nw',
                        width=self.config.width - 30
                    )
                    self._text_items.append(orig_item)
                    y_offset += 16
                
                # 绘制消息
                text_item = self._canvas.create_text(
                    10, y_offset,
                    text=display_text[:200],
                    fill=color,
                    font=(self.config.font_family, self.config.font_size),
                    anchor='nw',
                    width=self.config.width - 30
                )
                self._text_items.append(text_item)
                
                # 计算文本高度
                bbox = self._canvas.bbox(text_item)
                if bbox:
                    text_height = bbox[3] - bbox[1]
                    y_offset += text_height + 10
                else:
                    y_offset += line_height + 5
            
            # 更新滚动区域
            self._canvas.config(scrollregion=(0, 0, self.config.width, y_offset + 50))
    
    def add_message(self, text: str, 
                   original: str = "",
                   message_type: str = "translation",
                   color: Optional[str] = None,
                   ttl: Optional[float] = None,
                   player: Optional[str] = None) -> None:
        """添加消息到叠加层"""
        msg = OverlayMessage(
            text=text,
            original=original,
            message_type=message_type,
            color=color or self.config.text_color,
            ttl=ttl if ttl is not None else self.config.message_ttl,
            player=player
        )
        
        with self._lock:
            self._messages.append(msg)
            self._message_count += 1
    
    def add_translation(self, original: str, translated: str, player: Optional[str] = None) -> None:
        """添加翻译结果"""
        self.add_message(
            text=translated,
            original=original,
            message_type="translation",
            player=player
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
    
    def add_reply_result(self, original: str, translated: str, target_lang: str) -> None:
        """添加回话翻译结果"""
        self.add_message(
            text=f"回话[{target_lang}]: {translated}",
            original=original,
            message_type="reply",
            color="#ff88cc",
            ttl=30.0
        )
    
    def clear_messages(self) -> None:
        """清空所有消息"""
        with self._lock:
            self._messages.clear()
    
    def clear_timeline(self) -> None:
        """清空时间线（占位，供外部调用）"""
        pass
    
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
    
    @property
    def message_count(self) -> int:
        return self._message_count

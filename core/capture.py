"""
Overwatch Assistant - Screen Capture Module
屏幕截图模块

提供游戏画面的实时捕获功能，支持选择特定区域进行截图。
"""

import time
import threading
from typing import Tuple, Optional, Callable
from dataclasses import dataclass

try:
    from PIL import Image, ImageGrab, ImageEnhance
except ImportError:
    raise ImportError("请先安装 Pillow: pip install Pillow")

import numpy as np


@dataclass
class CaptureRegion:
    """捕获区域定义"""
    x1: int
    y1: int
    x2: int
    y2: int
    
    @property
    def width(self) -> int:
        return self.x2 - self.x1
    
    @property
    def height(self) -> int:
        return self.y2 - self.y1
    
    @property
    def bbox(self) -> Tuple[int, int, int, int]:
        return (self.x1, self.y1, self.x2, self.y2)
    
    def is_valid(self) -> bool:
        return self.width > 10 and self.height > 10
    
    def to_tuple(self) -> Tuple[int, int, int, int]:
        return self.bbox


class ScreenCapture:
    """屏幕截图器"""
    
    def __init__(self):
        self._running = False
        self._capture_thread: Optional[threading.Thread] = None
        self._callback: Optional[Callable[[Image.Image], None]] = None
        self._interval: float = 0.2
        self._region: Optional[CaptureRegion] = None
        self._last_frame: Optional[Image.Image] = None
        self._lock = threading.Lock()
    
    def set_region(self, region: Tuple[int, int, int, int]) -> None:
        """设置捕获区域"""
        self._region = CaptureRegion(*region)
        print(f"[捕获] 设置区域: {region}")
    
    def get_region(self) -> Optional[CaptureRegion]:
        """获取当前捕获区域"""
        return self._region
    
    def capture(self, region: Optional[Tuple[int, int, int, int]] = None) -> Optional[Image.Image]:
        """
        单次截图
        
        Args:
            region: 截图区域 (x1, y1, x2, y2)，None 则全屏
            
        Returns:
            PIL Image 对象或 None
        """
        try:
            if region is not None:
                bbox = region
            elif self._region is not None:
                bbox = self._region.bbox
            else:
                # 全屏截图
                bbox = None
            
            screenshot = ImageGrab.grab(bbox=bbox)
            
            with self._lock:
                self._last_frame = screenshot
            
            return screenshot
            
        except Exception as e:
            print(f"[捕获错误] 截图失败: {e}")
            return None
    
    def capture_to_numpy(self, region: Optional[Tuple[int, int, int, int]] = None) -> Optional[np.ndarray]:
        """截图并转换为 numpy 数组 (OpenCV 格式 BGR)"""
        img = self.capture(region)
        if img is None:
            return None
        # PIL (RGB) -> OpenCV (BGR)
        return np.array(img)[:, :, ::-1]
    
    def start_continuous(self, 
                         interval: float = 0.2,
                         callback: Optional[Callable[[Image.Image], None]] = None) -> None:
        """
        开始持续截图
        
        Args:
            interval: 截图间隔（秒）
            callback: 每次截图后的回调函数，接收 Image.Image
        """
        if self._running:
            print("[捕获] 已经在运行中")
            return
        
        self._interval = interval
        self._callback = callback
        self._running = True
        
        self._capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._capture_thread.start()
        print(f"[捕获] 开始持续截图 (间隔: {interval}s)")
    
    def stop_continuous(self) -> None:
        """停止持续截图"""
        self._running = False
        if self._capture_thread and self._capture_thread.is_alive():
            self._capture_thread.join(timeout=1.0)
        print("[捕获] 已停止")
    
    def _capture_loop(self) -> None:
        """截图循环线程"""
        while self._running:
            start_time = time.time()
            
            img = self.capture()
            if img is not None and self._callback is not None:
                try:
                    self._callback(img)
                except Exception as e:
                    print(f"[捕获错误] 回调执行失败: {e}")
            
            # 控制帧率
            elapsed = time.time() - start_time
            sleep_time = max(0, self._interval - elapsed)
            if sleep_time > 0:
                time.sleep(sleep_time)
    
    def get_last_frame(self) -> Optional[Image.Image]:
        """获取最后一帧"""
        with self._lock:
            return self._last_frame.copy() if self._last_frame else None
    
    @property
    def is_running(self) -> bool:
        return self._running
    
    @staticmethod
    def get_screen_resolution() -> Tuple[int, int]:
        """获取屏幕分辨率"""
        img = ImageGrab.grab()
        return img.size
    
    @staticmethod
    def preprocess_for_ocr(img: Image.Image, 
                          contrast_alpha: float = 1.5,
                          binary_threshold: int = 150) -> Image.Image:
        """
        预处理图像以提高 OCR 识别率
        
        Args:
            img: 输入图像
            contrast_alpha: 对比度增强系数
            binary_threshold: 二值化阈值
            
        Returns:
            预处理后的图像
        """
        # 转为灰度图
        gray = img.convert('L')
        
        # 对比度增强
        enhancer = ImageEnhance.Contrast(gray)
        enhanced = enhancer.enhance(contrast_alpha)
        
        # 二值化
        binary = enhanced.point(lambda x: 0 if x < binary_threshold else 255, '1')
        
        return binary.convert('L')


class RegionSelector:
    """区域选择器 - 让用户通过拖拽选择屏幕区域"""
    
    def __init__(self):
        self.selected_region: Optional[Tuple[int, int, int, int]] = None
    
    def select_region(self, prompt: str = "请拖拽选择区域") -> Optional[Tuple[int, int, int, int]]:
        """
        打开一个全屏透明窗口让用户选择区域
        
        Returns:
            选择的区域坐标 (x1, y1, x2, y2) 或 None
        """
        try:
            import tkinter as tk
            
            root = tk.Tk()
            root.title(prompt)
            
            # 获取屏幕尺寸
            screen_width = root.winfo_screenwidth()
            screen_height = root.winfo_screenheight()
            
            root.geometry(f"{screen_width}x{screen_height}+0+0")
            root.attributes('-alpha', 0.3)
            root.attributes('-topmost', True)
            root.configure(bg='black')
            
            # 用于存储坐标的变量
            start_x = tk.IntVar()
            start_y = tk.IntVar()
            end_x = tk.IntVar()
            end_y = tk.IntVar()
            drawing = tk.BooleanVar(value=False)
            
            canvas = tk.Canvas(root, cursor="cross", bg='black', highlightthickness=0)
            canvas.pack(fill=tk.BOTH, expand=True)
            
            rect_id = None
            
            def on_mouse_down(event):
                start_x.set(event.x)
                start_y.set(event.y)
                drawing.set(True)
                nonlocal rect_id
                rect_id = canvas.create_rectangle(
                    event.x, event.y, event.x, event.y,
                    outline='red', width=2, fill='white'
                )
            
            def on_mouse_move(event):
                if drawing.get() and rect_id is not None:
                    canvas.coords(rect_id, start_x.get(), start_y.get(), event.x, event.y)
            
            def on_mouse_up(event):
                if drawing.get():
                    end_x.set(event.x)
                    end_y.set(event.y)
                    drawing.set(False)
                    
                    x1, y1 = min(start_x.get(), end_x.get()), min(start_y.get(), end_y.get())
                    x2, y2 = max(start_x.get(), end_x.get()), max(start_y.get(), end_y.get())
                    
                    self.selected_region = (x1, y1, x2, y2)
                    root.destroy()
            
            def on_key(event):
                if event.keysym == 'Escape':
                    self.selected_region = None
                    root.destroy()
            
            canvas.bind("<Button-1>", on_mouse_down)
            canvas.bind("<B1-Motion>", on_mouse_move)
            canvas.bind("<ButtonRelease-1>", on_mouse_up)
            root.bind("<Key>", on_key)
            
            # 显示提示文字
            canvas.create_text(
                screen_width // 2, screen_height // 2,
                text=f"{prompt}\n拖拽选择区域，按 ESC 取消",
                fill='white', font=('Microsoft YaHei', 24),
                justify=tk.CENTER
            )
            
            root.mainloop()
            
            return self.selected_region
            
        except Exception as e:
            print(f"[区域选择] 错误: {e}")
            # 降级方案：手动输入坐标
            print("请手动输入区域坐标 (x1 y1 x2 y2):")
            try:
                coords = input().strip().split()
                if len(coords) == 4:
                    return tuple(int(c) for c in coords)
            except:
                pass
            return None


# 测试代码
if __name__ == "__main__":
    # 测试截图
    cap = ScreenCapture()
    
    print("测试全屏截图...")
    img = cap.capture()
    if img:
        print(f"截图成功: {img.size}")
        img.save("test_capture.png")
    
    print("\n测试区域选择...")
    selector = RegionSelector()
    region = selector.select_region("选择聊天框区域")
    if region:
        print(f"选择区域: {region}")
        cap.set_region(region)
        img = cap.capture()
        if img:
            img.save("test_region.png")
            print("区域截图已保存")

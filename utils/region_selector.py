"""
Overwatch Assistant - Region Selector Utility
区域选择工具

提供可视化界面选择屏幕区域。
"""

import tkinter as tk
from typing import Tuple, Optional, Callable


class RegionSelectorApp:
    """区域选择应用"""
    
    def __init__(self, on_selected: Optional[Callable[[Tuple[int, int, int, int]], None]] = None):
        self.on_selected = on_selected
        self.result: Optional[Tuple[int, int, int, int]] = None
    
    def select(self, prompt: str = "选择区域") -> Optional[Tuple[int, int, int, int]]:
        """
        显示全屏区域选择界面
        
        Returns:
            选择的区域 (x1, y1, x2, y2) 或 None
        """
        root = tk.Tk()
        root.title(prompt)
        
        # 全屏
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        root.geometry(f"{screen_width}x{screen_height}+0+0")
        
        # 透明黑色遮罩
        root.attributes('-alpha', 0.4)
        root.attributes('-topmost', True)
        root.configure(bg='black')
        root.overrideredirect(True)
        
        # 变量
        start_x = tk.IntVar(value=0)
        start_y = tk.IntVar(value=0)
        end_x = tk.IntVar(value=0)
        end_y = tk.IntVar(value=0)
        drawing = tk.BooleanVar(value=False)
        
        canvas = tk.Canvas(root, bg='black', highlightthickness=0, cursor='cross')
        canvas.pack(fill=tk.BOTH, expand=True)
        
        # 提示文字
        canvas.create_text(
            screen_width // 2, 80,
            text=prompt,
            fill='white', font=('Microsoft YaHei', 28, 'bold')
        )
        canvas.create_text(
            screen_width // 2, 130,
            text="拖拽鼠标选择区域 | 按 ESC 取消",
            fill='#aaaaaa', font=('Microsoft YaHei', 16)
        )
        
        rect_id = None
        coords_text = None
        
        def on_press(event):
            nonlocal rect_id, coords_text
            start_x.set(event.x)
            start_y.set(event.y)
            drawing.set(True)
            
            if rect_id:
                canvas.delete(rect_id)
            if coords_text:
                canvas.delete(coords_text)
            
            rect_id = canvas.create_rectangle(
                event.x, event.y, event.x, event.y,
                outline='#00ff88', width=2, fill='#00ff8833'
            )
        
        def on_drag(event):
            if drawing.get() and rect_id:
                canvas.coords(rect_id, start_x.get(), start_y.get(), event.x, event.y)
                
                if coords_text:
                    canvas.delete(coords_text)
                
                w = abs(event.x - start_x.get())
                h = abs(event.y - start_y.get())
                coords_text = canvas.create_text(
                    (start_x.get() + event.x) // 2,
                    (start_y.get() + event.y) // 2,
                    text=f"{w} x {h}",
                    fill='white', font=('Microsoft YaHei', 12)
                )
        
        def on_release(event):
            nonlocal rect_id
            if drawing.get():
                drawing.set(False)
                end_x.set(event.x)
                end_y.set(event.y)
                
                x1 = min(start_x.get(), end_x.get())
                y1 = min(start_y.get(), end_y.get())
                x2 = max(start_x.get(), end_x.get())
                y2 = max(start_y.get(), end_y.get())
                
                self.result = (x1, y1, x2, y2)
                
                if self.on_selected:
                    self.on_selected(self.result)
                
                root.destroy()
        
        def on_key(event):
            if event.keysym == 'Escape':
                self.result = None
                root.destroy()
        
        canvas.bind('<Button-1>', on_press)
        canvas.bind('<B1-Motion>', on_drag)
        canvas.bind('<ButtonRelease-1>', on_release)
        root.bind('<Key>', on_key)
        
        root.mainloop()
        
        return self.result


class MultiRegionSelector:
    """多区域选择器 - 一次性选择多个区域"""
    
    def __init__(self):
        self.regions: dict = {}
    
    def select_multiple(self, region_names: list) -> dict:
        """
        依次选择多个区域
        
        Args:
            region_names: 区域名称列表
            
        Returns:
            区域名称 -> 坐标的字典
        """
        for name in region_names:
            selector = RegionSelectorApp()
            region = selector.select(f"选择: {name}")
            if region:
                self.regions[name] = region
                print(f"已设置 {name}: {region}")
            else:
                print(f"跳过 {name}")
        
        return self.regions


def quick_select(prompt: str = "选择区域") -> Optional[Tuple[int, int, int, int]]:
    """快速选择单个区域"""
    selector = RegionSelectorApp()
    return selector.select(prompt)


# 测试
if __name__ == "__main__":
    print("测试区域选择器...")
    region = quick_select("选择聊天框区域")
    if region:
        print(f"选择结果: {region}")
    else:
        print("未选择区域")

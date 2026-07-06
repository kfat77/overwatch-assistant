"""
Enhanced Capture System with Pixel Diff Patrol + Text Presence Gate
增强型捕获系统：像素差分巡逻 + 文字存在检测门

核心思路（移植自 ow-translate-lite）：
1. 像素差分巡逻：画面稳定时只做低成本截图签名，不跑 OCR
2. 文字存在检测门：检测到变化后，先判断是否疑似有聊天文字
3. 突发 OCR：确认有文字后，进入短突发 OCR 周期
4. 空闲探测：聊天区域无变化时，降低 OCR 频率
"""

import time
import threading
import numpy as np
from typing import Optional, Tuple, Callable
from dataclasses import dataclass
from PIL import Image, ImageGrab

try:
    import cv2
except ImportError:
    cv2 = None


@dataclass
class CaptureState:
    """捕获状态"""
    last_screenshot: Optional[np.ndarray] = None
    last_signature: Optional[bytes] = None
    last_ocr_time: float = 0
    is_active: bool = False  # 是否处于活跃检测期
    stable_count: int = 0    # 连续稳定帧数
    change_count: int = 0    # 连续变化帧数


class FrameDiffGate:
    """帧差分门控
    
    判断两帧画面是否发生显著变化。
    用于：画面稳定时不触发 OCR，节省 CPU。
    """
    
    def __init__(self, threshold: float = 0.02, min_changed_pixels: int = 500):
        self.threshold = threshold  # 变化比例阈值
        self.min_changed_pixels = min_changed_pixels
    
    def compute_signature(self, img: np.ndarray) -> bytes:
        """计算截图签名（低成本的哈希）"""
        # 缩小到 32x32，转灰度，计算平均哈希
        if img.shape[0] > 32 and img.shape[1] > 32:
            small = cv2.resize(img, (32, 32)) if cv2 else img[::img.shape[0]//32, ::img.shape[1]//32]
        else:
            small = img
        
        if len(small.shape) == 3:
            gray = np.mean(small, axis=2)
        else:
            gray = small
        
        # 平均哈希
        mean = np.mean(gray)
        bits = (gray > mean).astype(np.uint8).flatten()
        
        # 转为 bytes
        byte_arr = np.packbits(bits)
        return byte_arr.tobytes()
    
    def has_changed(self, img_a: np.ndarray, img_b: np.ndarray) -> bool:
        """判断两帧是否有显著变化"""
        if img_a is None or img_b is None:
            return True
        
        if img_a.shape != img_b.shape:
            return True
        
        # 快速比较：计算差异像素数
        diff = cv2.absdiff(img_a, img_b) if cv2 else np.abs(img_a.astype(np.int16) - img_b.astype(np.int16))
        
        if len(diff.shape) == 3:
            diff = np.mean(diff, axis=2)
        
        # 阈值：像素值差异 > 30
        changed_pixels = np.sum(diff > 30)
        total_pixels = diff.size
        
        change_ratio = changed_pixels / total_pixels
        return change_ratio > self.threshold or changed_pixels > self.min_changed_pixels


class TextPresenceGate:
    """文字存在检测门
    
    在跑完整 OCR 之前，先快速判断截图中是否有文字。
    方法：检测图像中是否有足够的高对比度边缘（文字特征）。
    """
    
    def __init__(self, edge_threshold: float = 0.05):
        self.edge_threshold = edge_threshold
    
    def has_text(self, img: np.ndarray) -> bool:
        """快速判断图像中是否可能有文字"""
        if cv2 is None:
            # 没有 OpenCV，直接返回 True（跳过优化）
            return True
        
        try:
            # 转灰度
            if len(img.shape) == 3:
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            else:
                gray = img
            
            # 边缘检测（Canny）
            edges = cv2.Canny(gray, 50, 150)
            
            # 计算边缘像素比例
            edge_ratio = np.sum(edges > 0) / edges.size
            
            return edge_ratio > self.edge_threshold
        except Exception:
            return True


class SmartCapture:
    """智能捕获器
    
    自动调节截图和 OCR 频率：
    - 画面稳定：每 2 秒做一次签名检查
    - 画面变化：先过文字存在门，再过突发 OCR
    - 检测到聊天：进入活跃期，高频 OCR
    - 聊天结束：回到空闲期
    """
    
    # 状态枚举
    STATE_IDLE = "idle"         # 空闲：低频签名检查
    STATE_PROBE = "probe"       # 探测：文字存在检测
    STATE_BURST = "burst"       # 突发：高频 OCR
    STATE_ACTIVE = "active"     # 活跃：中频 OCR
    
    def __init__(self):
        self.diff_gate = FrameDiffGate()
        self.text_gate = TextPresenceGate()
        self.state = self.STATE_IDLE
        self.state_data = CaptureState()
        
        # 频率配置
        self.idle_interval = 2.0     # 空闲期签名检查间隔
        self.probe_interval = 0.5    # 探测间隔
        self.burst_interval = 0.2    # 突发 OCR 间隔
        self.active_interval = 0.5   # 活跃期 OCR 间隔
        self.cooldown_frames = 10    # 连续无变化多少帧后回到空闲
        
        self._running = False
        self._callback: Optional[Callable[[np.ndarray], None]] = None
        self._region: Optional[Tuple[int, int, int, int]] = None
        self._thread: Optional[threading.Thread] = None
        # FIX: 跟踪因差分/文字门控跳过的帧数
        self._skipped_count = 0
    
    def set_region(self, region: Tuple[int, int, int, int]) -> None:
        self._region = region
    
    def capture(self) -> Optional[np.ndarray]:
        """截图"""
        try:
            bbox = self._region
            img = ImageGrab.grab(bbox=bbox)
            return np.array(img)
        except Exception:
            return None
    
    def start(self, callback: Callable[[np.ndarray], None]) -> None:
        """启动智能捕获循环"""
        self._callback = callback
        self._running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()
    
    def stop(self) -> None:
        self._running = False
    
    def _capture_loop(self) -> None:
        """主捕获循环"""
        while self._running:
            start_time = time.time()
            
            # 截图
            img = self.capture()
            if img is None:
                time.sleep(0.5)
                continue
            
            # 状态机处理
            should_ocr = self._process_frame(img)
            
            if should_ocr and self._callback:
                try:
                    self._callback(img)
                except Exception as e:
                    print(f"[捕获错误] 回调失败: {e}")
            
            # 计算下次检查间隔
            interval = self._get_interval()
            elapsed = time.time() - start_time
            sleep_time = max(0, interval - elapsed)
            if sleep_time > 0:
                time.sleep(sleep_time)
    
    def _process_frame(self, img: np.ndarray) -> bool:
        """处理一帧，返回是否应该跑 OCR"""
        
        if self.state == self.STATE_IDLE:
            # 空闲期：只做签名比较
            sig = self.diff_gate.compute_signature(img)
            
            if self.state_data.last_signature is not None:
                has_changed = sig != self.state_data.last_signature
                
                if has_changed:
                    # 有变化，进入探测期
                    self.state = self.STATE_PROBE
                    self.state_data.change_count = 1
                    self.state_data.stable_count = 0
                else:
                    self.state_data.stable_count += 1
            
            self.state_data.last_signature = sig
            # FIX: 空闲期跳过 OCR 计数
            self._skipped_count += 1
            return False
        
        elif self.state == self.STATE_PROBE:
            # 探测期：检查文字存在
            has_text = self.text_gate.has_text(img)
            
            if has_text:
                # 有文字，进入突发期
                self.state = self.STATE_BURST
                self.state_data.is_active = True
                return True
            else:
                # 无文字，可能是普通画面变化
                self.state_data.change_count += 1
                if self.state_data.change_count > 5:
                    # 连续多次探测无文字，回空闲
                    self.state = self.STATE_IDLE
                    self.state_data.change_count = 0
                # FIX: 探测期无文字跳过 OCR 计数
                self._skipped_count += 1
                return False
        
        elif self.state == self.STATE_BURST:
            # 突发期：高频 OCR
            # 检查是否还在变化
            if self.state_data.last_screenshot is not None:
                has_changed = self.diff_gate.has_changed(
                    self.state_data.last_screenshot, img
                )
                
                if has_changed:
                    self.state_data.change_count += 1
                    self.state_data.stable_count = 0
                    
                    # 连续变化达到一定次数，转入活跃期
                    if self.state_data.change_count >= 3:
                        self.state = self.STATE_ACTIVE
                else:
                    self.state_data.stable_count += 1
                    
                    # 连续稳定，回到空闲
                    if self.state_data.stable_count >= self.cooldown_frames:
                        self.state = self.STATE_IDLE
                        self.state_data.is_active = False
                        self.state_data.change_count = 0
                        self.state_data.stable_count = 0
            
            self.state_data.last_screenshot = img.copy()
            return True
        
        elif self.state == self.STATE_ACTIVE:
            # 活跃期：中频 OCR
            if self.state_data.last_screenshot is not None:
                has_changed = self.diff_gate.has_changed(
                    self.state_data.last_screenshot, img
                )
                
                if has_changed:
                    self.state_data.change_count += 1
                    self.state_data.stable_count = 0
                else:
                    self.state_data.stable_count += 1
                    
                    if self.state_data.stable_count >= self.cooldown_frames:
                        self.state = self.STATE_IDLE
                        self.state_data.is_active = False
            
            self.state_data.last_screenshot = img.copy()
            return True
        
        return False
    
    def _get_interval(self) -> float:
        """获取当前状态的检查间隔"""
        intervals = {
            self.STATE_IDLE: self.idle_interval,
            self.STATE_PROBE: self.probe_interval,
            self.STATE_BURST: self.burst_interval,
            self.STATE_ACTIVE: self.active_interval,
        }
        return intervals.get(self.state, 1.0)
    
    @property
    def is_active(self) -> bool:
        return self.state_data.is_active
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            "state": self.state,
            "is_active": self.state_data.is_active,
            "stable_count": self.state_data.stable_count,
            "change_count": self.state_data.change_count,
            "skipped_count": self._skipped_count,
        }

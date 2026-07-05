"""
Overwatch Assistant - OCR Engine Module
OCR 文字识别模块

支持英文和韩文识别，使用 EasyOCR 或 Tesseract。
"""

import os
import re
import time
import hashlib
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from collections import OrderedDict

try:
    from PIL import Image, ImageEnhance
except ImportError:
    raise ImportError("请先安装 Pillow: pip install Pillow")


@dataclass
class OCRResult:
    """OCR 识别结果"""
    text: str
    confidence: float
    bbox: Optional[Tuple[int, int, int, int]] = None
    language: Optional[str] = None
    
    def __repr__(self):
        conf_str = f"{self.confidence:.2f}" if self.confidence else "N/A"
        return f"OCRResult(text='{self.text[:30]}...', conf={conf_str})"


class TranslationCache:
    """翻译结果缓存"""
    
    def __init__(self, max_size: int = 500):
        self._cache: OrderedDict[str, str] = OrderedDict()
        self._max_size = max_size
    
    def _make_key(self, text: str, src_lang: str, tgt_lang: str) -> str:
        """生成缓存键"""
        key = f"{src_lang}:{tgt_lang}:{text}"
        return hashlib.md5(key.encode('utf-8')).hexdigest()
    
    def get(self, text: str, src_lang: str = "auto", tgt_lang: str = "zh") -> Optional[str]:
        """获取缓存的翻译结果"""
        key = self._make_key(text, src_lang, tgt_lang)
        if key in self._cache:
            # 移到末尾（最近使用）
            self._cache.move_to_end(key)
            return self._cache[key]
        return None
    
    def set(self, text: str, translation: str, src_lang: str = "auto", tgt_lang: str = "zh") -> None:
        """设置缓存"""
        key = self._make_key(text, src_lang, tgt_lang)
        self._cache[key] = translation
        self._cache.move_to_end(key)
        
        # 超出容量时移除最旧的
        while len(self._cache) > self._max_size:
            self._cache.popitem(last=False)
    
    def clear(self) -> None:
        """清空缓存"""
        self._cache.clear()
    
    def size(self) -> int:
        return len(self._cache)


class OCREngine:
    """OCR 引擎基类"""
    
    def __init__(self, config):
        self.config = config
        self.translation_cache = TranslationCache(config.cache_max_size)
    
    def recognize(self, image) -> List[OCRResult]:
        """识别图像中的文字"""
        raise NotImplementedError
    
    def preprocess_image(self, img: Image.Image) -> Image.Image:
        """图像预处理"""
        if not self.config.enable_preprocessing:
            return img
        
        # 转为灰度
        gray = img.convert('L')
        
        # 对比度增强
        enhancer = ImageEnhance.Contrast(gray)
        enhanced = enhancer.enhance(self.config.contrast_alpha)
        
        # 锐化
        sharpener = ImageEnhance.Sharpness(enhanced)
        sharpened = sharpener.enhance(2.0)
        
        return sharpened
    
    def filter_results(self, results: List[OCRResult]) -> List[OCRResult]:
        """过滤低置信度结果"""
        filtered = []
        for r in results:
            if r.confidence >= self.config.confidence_threshold:
                # 清理文本
                text = self._clean_text(r.text)
                if text and len(text) >= 1:
                    r.text = text
                    filtered.append(r)
        return filtered
    
    @staticmethod
    def _clean_text(text: str) -> str:
        """清理识别出的文字"""
        # 移除多余空白
        text = ' '.join(text.split())
        # 移除特殊字符
        text = text.strip()
        return text


class EasyOCREngine(OCREngine):
    """EasyOCR 引擎 - 推荐，韩文识别效果好"""
    
    def __init__(self, config):
        super().__init__(config)
        self._reader = None
        self._init_engine()
    
    def _init_engine(self):
        """初始化 EasyOCR"""
        try:
            import easyocr
            print("[OCR] 正在加载 EasyOCR 模型 (首次加载需要一些时间)...")
            self._reader = easyocr.Reader(
                self.config.languages,
                gpu=False,  # CPU 运行
                verbose=False
            )
            print("[OCR] EasyOCR 模型加载完成")
        except ImportError:
            print("[OCR错误] 未安装 easyocr，请运行: pip install easyocr")
            raise
        except Exception as e:
            print(f"[OCR错误] EasyOCR 初始化失败: {e}")
            raise
    
    def recognize(self, image) -> List[OCRResult]:
        """
        使用 EasyOCR 识别图像
        
        Args:
            image: PIL Image 或 numpy array
            
        Returns:
            OCRResult 列表
        """
        try:
            import numpy as np
            
            # 确保是 numpy array
            if isinstance(image, Image.Image):
                img = self.preprocess_image(image)
                img_array = np.array(img)
            else:
                img_array = image
            
            # EasyOCR 识别
            results = self._reader.readtext(img_array)
            
            ocr_results = []
            for bbox, text, conf in results:
                ocr_results.append(OCRResult(
                    text=text,
                    confidence=conf,
                    bbox=tuple(int(x) for x in [bbox[0][0], bbox[0][1], bbox[2][0], bbox[2][1]])
                ))
            
            return self.filter_results(ocr_results)
            
        except Exception as e:
            print(f"[OCR错误] EasyOCR 识别失败: {e}")
            return []


class TesseractEngine(OCREngine):
    """Tesseract OCR 引擎"""
    
    def __init__(self, config):
        super().__init__(config)
        self._init_engine()
    
    def _init_engine(self):
        """初始化 Tesseract"""
        try:
            import pytesseract
            # 测试是否可用
            pytesseract.get_tesseract_version()
            print("[OCR] Tesseract 引擎已就绪")
        except ImportError:
            print("[OCR错误] 未安装 pytesseract，请运行: pip install pytesseract")
            print("[OCR错误] 同时需要安装 Tesseract-OCR 本体: https://github.com/UB-Mannheim/tesseract/wiki")
            raise
        except Exception as e:
            print(f"[OCR错误] Tesseract 初始化失败: {e}")
            raise
    
    def recognize(self, image) -> List[OCRResult]:
        """使用 Tesseract 识别图像"""
        try:
            import pytesseract
            
            if isinstance(image, Image.Image):
                img = self.preprocess_image(image)
            else:
                import numpy as np
                img = Image.fromarray(image)
                img = self.preprocess_image(img)
            
            # 使用 pytesseract image_to_data 获取详细结果
            data = pytesseract.image_to_data(
                img, 
                lang=self.config.tesseract_lang,
                output_type=pytesseract.Output.DICT
            )
            
            ocr_results = []
            n_boxes = len(data['text'])
            
            for i in range(n_boxes):
                text = data['text'][i].strip()
                conf = int(data['conf'][i])
                
                if text and conf > 0:
                    x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
                    ocr_results.append(OCRResult(
                        text=text,
                        confidence=conf / 100.0,
                        bbox=(x, y, x + w, y + h)
                    ))
            
            return self.filter_results(ocr_results)
            
        except Exception as e:
            print(f"[OCR错误] Tesseract 识别失败: {e}")
            return []


class TextDeduplicator:
    """文本去重器 - 避免重复识别同一文字"""
    
    def __init__(self, similarity_threshold: float = 0.85, ttl: float = 5.0):
        self._seen_texts: Dict[str, float] = {}
        self._similarity_threshold = similarity_threshold
        self._ttl = ttl
    
    def _similarity(self, a: str, b: str) -> float:
        """计算两个字符串的相似度"""
        # 简单的最长公共子序列近似
        a, b = a.lower(), b.lower()
        if a == b:
            return 1.0
        
        # 使用集合交集/并集
        set_a = set(a)
        set_b = set(b)
        if not set_a or not set_b:
            return 0.0
        
        intersection = len(set_a & set_b)
        union = len(set_a | set_b)
        return intersection / union if union > 0 else 0.0
    
    def is_duplicate(self, text: str) -> bool:
        """检查文本是否已存在（或非常相似）"""
        now = time.time()
        
        # 清理过期条目
        self._seen_texts = {
            k: v for k, v in self._seen_texts.items() 
            if now - v < self._ttl
        }
        
        # 检查相似度
        for seen_text, timestamp in self._seen_texts.items():
            if self._similarity(text, seen_text) >= self._similarity_threshold:
                return True
        
        return False
    
    def add(self, text: str) -> None:
        """添加新文本"""
        self._seen_texts[text] = time.time()
    
    def clear(self) -> None:
        """清空记录"""
        self._seen_texts.clear()


def create_ocr_engine(config) -> OCREngine:
    """
    工厂函数：创建 OCR 引擎
    
    Args:
        config: OCRConfig 配置对象
        
    Returns:
        OCREngine 实例
    """
    if config.engine.lower() == "easyocr":
        return EasyOCREngine(config)
    elif config.engine.lower() == "tesseract":
        return TesseractEngine(config)
    else:
        raise ValueError(f"不支持的 OCR 引擎: {config.engine}")


# 测试代码
if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from config import ocr_config
    
    print("测试 OCR 引擎...")
    
    try:
        engine = create_ocr_engine(ocr_config)
        
        # 测试识别
        test_img = Image.new('RGB', (300, 100), color='white')
        # 这里需要实际测试图片
        # results = engine.recognize(test_img)
        # print(f"识别结果: {results}")
        
        print("OCR 引擎初始化成功")
        
    except Exception as e:
        print(f"测试失败: {e}")

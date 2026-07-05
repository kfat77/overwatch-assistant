import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import app_config, capture_config, ocr_config, translate_config, overlay_config
from core.capture import ScreenCapture
from core.ocr_engine import create_ocr_engine
from core.translator import Translator, ChatMessageTranslator
from core.overlay import OverlayWindow

print("="*50)
print(f"  {app_config.app_name} v{app_config.version}")
print("="*50)

# Test 1: Screen capture
print("\n[Test 1] Screen capture...")
cap = ScreenCapture()
res = cap.get_screen_resolution()
print(f"  Screen resolution: {res[0]}x{res[1]}")
print("  PASS")

# Test 2: OCR engine
print("\n[Test 2] OCR engine...")
try:
    ocr = create_ocr_engine(ocr_config)
    print(f"  Engine: {ocr_config.engine}")
    print("  PASS")
except Exception as e:
    print(f"  FAIL: {e}")
    print("  (This is expected if Tesseract is not installed)")

# Test 3: Translator
print("\n[Test 3] Translator...")
try:
    trans = Translator(translate_config)
    stats = trans.get_stats()
    print(f"  Engine: {stats['engine']}, Available: {stats['available']}")
    print("  PASS")
except Exception as e:
    print(f"  FAIL: {e}")

# Test 4: Overlay window (brief test)
print("\n[Test 4] Overlay window...")
try:
    overlay = OverlayWindow(overlay_config)
    overlay.start()
    import time
    time.sleep(1)
    print("  Window started")
    overlay.add_system_message("Test message")
    print("  Message added")
    time.sleep(1)
    overlay.stop()
    print("  PASS")
except Exception as e:
    print(f"  FAIL: {e}")

print("\n" + "="*50)
print("  All tests completed!")
print("="*50)

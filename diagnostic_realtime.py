"""
Script diagnostik standalone: test kamera + deteksi YOLO tanpa Flask/DB/threading.
Tujuan: mengisolasi apakah masalah ada di kamera atau di model.

Cara pakai:
    python diagnostic_realtime.py

Tekan 'q' untuk keluar dari window.
"""

import cv2
import time
from ultralytics import YOLO

# ==== KONFIGURASI - SESUAIKAN DENGAN SETUP ANDA ====
CAMERA_SOURCE = 0          # ganti sesuai index webcam Anda (0, 1, dst)
MODEL_PATH = "best-23.pt"     # path ke model Anda
CONF_THRESHOLD = 0.5
WIDTH, HEIGHT = 640, 480
USE_DSHOW = True           # True kalau di Windows, False kalau Linux/Mac
# =====================================================


def main():
    print("=" * 50)
    print("STEP 1: Loading model...")
    print("=" * 50)
    try:
        model = YOLO(MODEL_PATH)
        print(f"✅ Model berhasil dimuat: {MODEL_PATH}")
        print(f"   Classes: {model.names}")
    except Exception as e:
        print(f"❌ GAGAL memuat model: {e}")
        return

    print("\n" + "=" * 50)
    print("STEP 2: Membuka kamera...")
    print("=" * 50)
    if USE_DSHOW:
        cap = cv2.VideoCapture(CAMERA_SOURCE, cv2.CAP_DSHOW)
    else:
        cap = cv2.VideoCapture(CAMERA_SOURCE)

    if not cap.isOpened():
        print(f"❌ GAGAL membuka kamera index {CAMERA_SOURCE}")
        print("   -> Coba ganti CAMERA_SOURCE ke 1, 2, dst.")
        print("   -> Coba ganti USE_DSHOW ke False kalau bukan Windows.")
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT)

    actual_w = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    actual_h = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    print(f"✅ Kamera terbuka. Resolusi diminta: {WIDTH}x{HEIGHT}, "
          f"resolusi aktual: {int(actual_w)}x{int(actual_h)}")

    print("\n" + "=" * 50)
    print("STEP 3: Mulai capture + deteksi (tekan 'q' untuk keluar)")
    print("=" * 50)

    frame_count = 0
    while True:
        success, frame = cap.read()
        if not success:
            print("❌ cap.read() gagal — frame tidak terbaca dari kamera")
            time.sleep(0.5)
            continue

        frame_count += 1
        t0 = time.time()
        results = model(frame, verbose=False, conf=CONF_THRESHOLD)
        inference_time = time.time() - t0

        num_boxes = len(results[0].boxes) if results and results[0].boxes is not None else 0

        # Cetak info setiap 15 frame supaya terminal tidak banjir
        if frame_count % 15 == 0:
            print(f"Frame #{frame_count} | shape={frame.shape} | "
                  f"inference={inference_time*1000:.0f}ms | deteksi={num_boxes} objek")
            if num_boxes > 0:
                for box in results[0].boxes:
                    cls_id = int(box.cls[0])
                    conf = float(box.conf[0])
                    print(f"   -> {model.names.get(cls_id, 'unknown')} ({conf:.2f})")

        annotated = results[0].plot()
        cv2.imshow("Diagnostic - Realtime Detection", annotated)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    print(f"\nSelesai. Total frame diproses: {frame_count}")


if __name__ == "__main__":
    main()
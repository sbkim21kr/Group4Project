import cv2
from ultralytics import YOLO
from datetime import datetime
import os
import time
import csv
import pymcprotocol

# ==========================
# --- CONFIGURATION BLOCK ---
# ==========================
PLC_IP   = "192.168.3.39"   # PLC IP address
PLC_PORT = 4003             # PLC Port

YOLO_MODEL_PATH = r"C:\Users\windows11\Desktop\sbkim21\old_files\yolov8test\DeepLearning\runs\detect\my_first_yolov8_run4\weights\best.pt"

SAVE_DIR = "captures"
CSV_FILE = os.path.join(SAVE_DIR, "detections_log.csv")

START_DEVICE = "M402"   # Start trigger device (pulse)
END_DEVICE   = "M401"   # End signal device (pulse)

# Direct mapping of classes to PLC M devices
CLASS_TO_PLC = {
    "brown_critical_defect": "M404",
    "brown_intermediate_defect": "M404",
    "brown_minor_defect": "M404",
    # "brown_pass": "M705",
    "orange_critical_defect": "M404",
    "orange_intermediate_defect": "M404",
    "orange_minor_defect": "M404",
    # "orange_pass": "M709"
}
# ==========================

# --- YOLO model ---
model = YOLO(YOLO_MODEL_PATH)

# --- Camera ---
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Error: Could not open camera.")
    exit()

# --- Save dirs ---
os.makedirs(SAVE_DIR, exist_ok=True)

# --- Initialize CSV ---
if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, mode="w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "filename", "class", "confidence", "x1", "y1", "x2", "y2"])


def capture_and_infer():
    """Capture one frame, run YOLO, save annotated image and log detections."""
    ret, frame = cap.read()
    if not ret:
        print("Failed to grab frame.")
        return []

    results = model(frame, verbose=False)
    annotated_frame = frame.copy()
    detections = []

    h, w = annotated_frame.shape[:2]
    for box in results[0].boxes:
        x1, y1, x2, y2 = box.xyxy[0].int().tolist()
        conf = float(box.conf[0])
        cls_id = int(box.cls[0])
        cls_name = model.names[cls_id]

        # Clamp coords
        x1 = max(0, min(x1, w - 1))
        y1 = max(0, min(y1, h - 1))
        x2 = max(0, min(x2, w - 1))
        y2 = max(0, min(y2, h - 1))

        # Draw bbox
        cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0,255,0), 3)

        # --- Label at lower-left corner with shaded background ---
        label = f"{cls_name} {conf:.2f}"
        (tw, th), baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
        lx, ly = 10, h - 10  # bottom-left corner
        cv2.rectangle(annotated_frame, (lx, ly - th - baseline), (lx + tw, ly + baseline), (0,0,0), -1)
        cv2.putText(annotated_frame, label, (lx, ly), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)

        detections.append((cls_name, conf, x1, y1, x2, y2))

    # Save image
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    filename = datetime.now().strftime("%y%m%d_%Hhr%Mmin%Ssec.jpg")  # Korean style timestamp
    filepath = os.path.join(SAVE_DIR, filename)
    cv2.imwrite(filepath, annotated_frame)

    # Log CSV
    with open(CSV_FILE, mode="a", newline="") as f:
        writer = csv.writer(f)
        for det in detections:
            cls_name, conf, x1, y1, x2, y2 = det
            writer.writerow([timestamp, filename, cls_name, f"{conf:.2f}", x1, y1, x2, y2])

    print(f"[YOLO] Photo captured → {filepath}")
    return detections


def pulse_bit(plc, device, on_time=0.5, off_time=0.5):
    """Pulse a PLC bit device (set 1 then 0)."""
    plc.batchwrite_bitunits(device, [1])
    time.sleep(on_time)
    plc.batchwrite_bitunits(device, [0])
    time.sleep(off_time)


def main():
    print("[System] Worker started")

    plc = pymcprotocol.Type3E()
    try:
        plc.connect(PLC_IP, PLC_PORT)
        print(f"[PLC] Connected to {PLC_IP}:{PLC_PORT}")
    except Exception as e:
        print(f"[PLC] Initial connect error: {e}")
        return

    connected_once = True
    waiting_logged = False

    try:
        while True:
            # --- Connection check ---
            try:
                plc.batchread_bitunits(START_DEVICE, 1)
                if connected_once:
                    print("[PLC] Connection OK")
                    connected_once = False
                    waiting_logged = False
            except Exception as e:
                print(f"[PLC] Connection lost: {e}")
                time.sleep(2)
                connected_once = True
                continue

            # --- Trigger check ---
            try:
                trigger_val = int(plc.batchread_bitunits(START_DEVICE, 1)[0])
            except Exception as e:
                print(f"[PLC] Read error: {e}")
                time.sleep(1)
                continue

            if trigger_val == 1:
                print(f"\n[PLC] Trigger received ({START_DEVICE}=1) → starting vision job")

                # Reset all mapped outputs
                for addr in CLASS_TO_PLC.values():
                    plc.batchwrite_bitunits(addr, [0])

                detections = capture_and_infer()

                if not detections:
                    print("[PLC] No detections → nothing written")
                else:
                    for det in detections:
                        cls_name = det[0]
                        if cls_name in CLASS_TO_PLC:
                            addr = CLASS_TO_PLC[cls_name]
                            pulse_bit(plc, addr, on_time=0.2, off_time=0.2)
                            print(f"[PLC] {cls_name} → pulsed {addr}")

                # Pulse END_DEVICE (job done)
                pulse_bit(plc, END_DEVICE, on_time=0.2, off_time=0.2)

                snapshot = {cls: plc.batchread_bitunits(addr, 1)[0] for cls, addr in CLASS_TO_PLC.items()}
                print("[PLC] Snapshot →", snapshot)

                print("[PLC] Job run complete → waiting for next trigger...")
                waiting_logged = False

            else:
                if not waiting_logged:
                    print(f"[PLC] Waiting for start device {START_DEVICE}=1...")
                    waiting_logged = True
                time.sleep(0.5)

    except KeyboardInterrupt:
        print("\nStopping worker...")
        cap.release()
        cv2.destroyAllWindows()
        plc.close()
        print("[PLC] Disconnected")


if __name__ == "__main__":
    main()

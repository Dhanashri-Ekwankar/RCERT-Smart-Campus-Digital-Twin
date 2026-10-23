import cv2
import time
from ultralytics import YOLO

# YOLO11 Nano ONNX model
model = YOLO("yolo11n.onnx")

# Laptop webcam
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("ERROR: Camera could not be opened.")
    exit()

print("=" * 60)
print("RCERT SMART CAMPUS - AI COMPUTER VISION")
print("=" * 60)
print("Live person detection started.")
print("Only PERSON class will be counted.")
print("Press Q to exit.")
print("=" * 60)

while True:

    success, frame = cap.read()

    if not success:
        print("ERROR: Cannot read webcam frame.")
        break

    # YOLO inference
    results = model(
        frame,
        imgsz=640,
        conf=0.50,
        classes=[0],
        verbose=False
    )

    person_count = 0

    # Process detections
    for result in results:

        for box in result.boxes:

            confidence = float(box.conf[0])

            if confidence < 0.50:
                continue

            x1, y1, x2, y2 = map(
                int,
                box.xyxy[0].tolist()
            )

            person_count += 1

            # Bounding box
            cv2.rectangle(
                frame,
                (x1, y1),
                (x2, y2),
                (0, 255, 0),
                2
            )

            # Label
            cv2.putText(
                frame,
                f"PERSON {confidence:.0%}",
                (x1, max(y1 - 10, 20)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 0),
                2
            )

    # Occupancy status
    if person_count >= 10:
        status = "HIGH OCCUPANCY"
    elif person_count >= 5:
        status = "MODERATE OCCUPANCY"
    else:
        status = "NORMAL OCCUPANCY"

    # Dashboard panel
    cv2.rectangle(
        frame,
        (10, 10),
        (390, 155),
        (15, 15, 15),
        -1
    )

    cv2.putText(
        frame,
        "RCERT SMART CAMPUS",
        (25, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (255, 255, 255),
        2
    )

    cv2.putText(
        frame,
        f"PERSONS DETECTED: {person_count}",
        (25, 75),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (0, 255, 0),
        2
    )

    cv2.putText(
        frame,
        f"OCCUPANCY: {status}",
        (25, 108),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.60,
        (255, 255, 255),
        2
    )

    current_time = time.strftime("%H:%M:%S")

    cv2.putText(
        frame,
        f"LIVE: {current_time}",
        (25, 138),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.50,
        (200, 200, 200),
        1
    )

    cv2.imshow(
        "RCERT Smart Campus - AI Person Detection",
        frame
    )

    # Q to exit
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()

print("AI Computer Vision stopped.")
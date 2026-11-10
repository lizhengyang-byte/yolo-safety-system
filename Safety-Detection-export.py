"""
Safety-Detection (YOLOv8) - Export annotated video to a file.

Based on Safety-Detection.py, but writes the annotated frames to an output
video file instead of only showing them in a window.

Usage:
    uv run python Safety-Detection-export.py [--input ./videos/huuman.mp4] [--output output.mp4]
"""

from ultralytics import YOLO
import cv2
import cvzone
import math
import argparse
import os
from tqdm import tqdm


def main(input_path="videos/地产工人工地干活视频素材.mp4", output_path="videos/当安全员来到工地视察！output.mp4",
         model_path="weights/ppe/ppe.pt", conf_thres=0.5, show=False, device=None):
    # Open the input video
    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {input_path}")

    # Read video metadata for the writer
    frame_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    if not fps or fps <= 0 or fps != fps:  # 0 / NaN fallback
        fps = 30.0

    # Pick a codec based on the output extension
    ext = os.path.splitext(output_path)[1].lower()
    fourcc = cv2.VideoWriter_fourcc(*"mp4v") if ext == ".mp4" else cv2.VideoWriter_fourcc(*"MJPG")
    writer = cv2.VideoWriter(output_path, fourcc, fps, (frame_w, frame_h))
    if not writer.isOpened():
        raise RuntimeError(f"Cannot create output video: {output_path}")

    # Load the YOLO PPE model
    model = YOLO(model_path)

    classNames = ['Hardhat', 'Mask', 'NO-Hardhat', 'NO-Mask', 'NO-Safety Vest', 'Person', 'Safety Cone',
                  'Safety Vest', 'machinery', 'vehicle']

    # Progress bar (total may be unknown for some stream sources)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    pbar = tqdm(total=total_frames if total_frames > 0 else None,
                desc="Processing", unit="frame", dynamic_ncols=True)

    frame_count = 0
    while True:
        # Read a frame from the video
        success, img = cap.read()
        if not success:
            break  # end of video

        # Run detection on the current frame
        results = model(img, stream=True, device=device)

        for r in results:
            boxes = r.boxes
            for box in boxes:
                x1, y1, x2, y2 = box.xyxy[0]
                x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)

                # Confidence and class index
                conf = math.ceil((box.conf[0] * 100)) / 100
                cls = int(box.cls[0])
                if cls >= len(classNames):
                    continue
                currentClass = classNames[cls]

                if conf > conf_thres:
                    # Color by compliance status
                    if currentClass in ('NO-Hardhat', 'NO-Safety Vest', 'NO-Mask'):
                        myColor = (0, 0, 255)   # red: non-compliance
                    elif currentClass in ('Hardhat', 'Safety Vest', 'Mask'):
                        myColor = (0, 255, 0)   # green: compliance
                    else:
                        myColor = (255, 0, 0)   # blue: other objects

                    # Label + box
                    cvzone.putTextRect(img, f'{classNames[cls]} {conf}',
                                       (max(0, x1), max(35, y1)), scale=1, thickness=1,
                                       colorB=myColor, colorT=(255, 255, 255), colorR=myColor, offset=5)
                    cv2.rectangle(img, (x1, y1), (x2, y2), myColor, 3)

        # Write the annotated frame to the output file
        writer.write(img)
        frame_count += 1
        pbar.update(1)

        # Optional live preview (press 'q' to quit early)
        if show:
            cv2.imshow("Image", img)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    pbar.close()
    cap.release()
    writer.release()
    cv2.destroyAllWindows()
    print(f"Done. Wrote {frame_count} frames -> {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="YOLOv8 PPE detection with annotated video export")
    parser.add_argument("--input", default="videos/地产工人工地干活视频素材.mp4", help="input video path")
    parser.add_argument("--output", default="videos/地产工人工地干活视频素材output.mp4", help="output annotated video path")
    parser.add_argument("--model", default="weights/ppe/ppe.pt", help="YOLO weights file")
    parser.add_argument("--conf", type=float, default=0.5, help="confidence threshold")
    parser.add_argument("--show", action="store_true", help="also display frames in a window")
    parser.add_argument("--device", default=None, help="inference device, e.g. 'cpu' or '0'")
    args = parser.parse_args()

    main(input_path=args.input, output_path=args.output, model_path=args.model,
         conf_thres=args.conf, show=args.show, device=args.device)

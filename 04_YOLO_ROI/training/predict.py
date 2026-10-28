
from ultralytics import YOLO
from pathlib import Path

# 현재 파일 기준 프로젝트 루트
ROOT = Path(__file__).resolve().parents[2]

# 학습된 모델
model_path = ROOT / "04_YOLO_ROI" / "models" / "best.pt"

model = YOLO(str(model_path))

# 검증 이미지
image_path = (
    ROOT
    / "02_Data"
    / "04_YOLO_Dataset"
    / "images"
    / "train"
    / "sample_03.jpg"
)

# YOLO ROI 검출
results = model.predict(
    source=str(image_path),
    conf=0.001,
    save=True
)
        print("x2 :", x2)
        print("y2 :", y2)

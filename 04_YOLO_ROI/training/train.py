
from ultralytics import YOLO
from pathlib import Path

# 현재 파일 기준 프로젝트 루트
ROOT = Path(__file__).resolve().parents[2]

# YOLO 기반 모델
model = YOLO("yolo26n.pt")

# 데이터셋 설정 파일
dataset_path = (
    ROOT
    / "02_Data"
    / "04_YOLO_Dataset"
    / "dataset.yaml"
)

# 학습 결과 저장 위치
project_path = (
    ROOT
    / "04_YOLO_ROI"
    / "results"
)

results = model.train(
    data=str(dataset_path),

    epochs=100,
    imgsz=640,
    batch=2,

    # 작은 데이터셋 진단용
    patience=100,
    close_mosaic=0,

    project=str(project_path),
    name="measurement_roi_v2"
)

print()
print("YOLO 재학습 완료")

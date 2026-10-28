
# YOLO Models

본 폴더에는 샤프트 외경 측정부 ROI 자동탐지에 사용한 YOLO 모델 Weight를 저장한다.

## best.pt

`best.pt`는 YOLO 학습 결과 중 Validation 성능이 가장 좋은 모델 Weight이다.

### 모델 정보

- Task: Object Detection
- Class: `measurement_roi`
- Base model: `yolo26n.pt`
- Image size: 640
- Epochs: 100
- Batch size: 2
- Training result folder: `measurement_roi_v2`

### 모델의 역할

본 모델은 샤프트 전체를 검출하는 것이 아니라, 실제 외경 측정을 수행할 **Measurement ROI 위치를 탐지**하는 데 사용한다.

```text
원본 이미지
    ↓
YOLO best.pt
    ↓
measurement_roi Bounding Box 검출
    ↓
ROI Crop
    ↓
OpenCV 정밀 Edge 측정
```

YOLO Bounding Box의 폭이나 높이는 외경 치수값으로 직접 사용하지 않는다.

실제 외경 측정은 검출된 ROI 내부에서 OpenCV 기반 Edge 측정엔진이 수행한다.

따라서 본 프로젝트에서의 역할은 다음과 같이 구분한다.

- YOLO: 측정 위치 탐색
- OpenCV: 실제 외경 Pixel 측정
- Calibration: Pixel 값을 mm로 변환
- Validation: 독립 시편을 이용한 정확도 검증

## 파일

- `best.pt` : 최종 사용 YOLO ROI Detection 모델

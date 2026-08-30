# YOLO ROI Dataset

## 1. 목적

본 데이터셋은 샤프트 외경 자체를 YOLO가 측정하기 위한 것이 아니라,
영상에서 외경 측정에 사용할 ROI(측정영역)를 자동으로 탐지하기 위해 구성하였다.

YOLO가 ROI를 탐지하면 이후 OpenCV 기반 영상처리를 이용하여
실제 샤프트 Edge와 외경을 측정하는 구조이다.

---

## 2. 원본 데이터 구성

YOLO ROI 데이터 구성에 사용한 원본 이미지 계열은 6개이다.

- sample_03
- sample_04
- sample_06
- sample_07
- sample_N01
- sample_N02

각 이미지에는 YOLO 학습을 위한 Label을 구성하였다.

---

## 3. Data Augmentation

제한된 원본 데이터를 보완하기 위해 영상 증강을 수행하였다.

각 원본 계열을 다음 5종으로 구성하였다.

- `orig` : 원본
- `blur` : 흐림 변형
- `bright` : 밝기 증가
- `contrast` : 대비 변화
- `dark` : 밝기 감소

따라서 하나의 원본 계열에서 총 5장의 이미지가 구성된다.

---

## 4. Train / Validation 구성

### Train

다음 5개 원본 계열을 사용하였다.

- sample_03
- sample_04
- sample_06
- sample_N01
- sample_N02

각 원본 계열당 5종의 이미지가 구성되어 있다.

5개 원본 계열 × 5종 = 총 25장

### Validation

`sample_07` 원본 계열을 사용하였다.

- sample_07_orig
- sample_07_blur
- sample_07_bright
- sample_07_contrast
- sample_07_dark

1개 원본 계열 × 5종 = 총 5장

### 전체 구성

| 구분 | 원본 계열 | 증강 포함 이미지 |
|---|---:|---:|
| Train | 5개 | 25장 |
| Validation | 1개 | 5장 |
| 합계 | 6개 | 30장 |

---

## 5. YOLO 학습조건

Day023 `train.py`에서 확인한 학습조건은 다음과 같다.

| 항목 | 설정 |
|---|---|
| Model | yolo26n.pt |
| Epochs | 100 |
| Image Size | 640 |
| Batch Size | 4 |
| Patience | 100 |

---

## 6. 실험 결과

개발기록에 따르면 초기 YOLO ROI 실험에서는
confidence가 약 0.008 수준으로 나타나 ROI 탐지가 어려웠다.

데이터 증강 후 실험에서는 최고 confidence 약 0.784가 기록되어
제한된 데이터 환경에서 ROI 자동탐지 가능성을 확인하였다.

중복 Bounding Box가 발생하는 경우에는
가장 높은 confidence를 가진 Box 1개를 선택하도록 처리하였다.

---

## 7. 데이터 해석 시 주의사항

총 30장은 서로 다른 실물 샤프트 30개를 의미하지 않는다.

실제 6개의 원본 이미지 계열에서
orig / blur / bright / contrast / dark 변형을 통해 구성한 데이터이다.

특히 Validation 5장도 서로 다른 5개 샤프트가 아니라
하나의 `sample_07` 원본 계열에서 파생된 데이터이다.

따라서 본 Validation 결과를 새로운 독립 제품에 대한
일반화 성능 검증 결과로 해석해서는 안 된다.

본 결과는 제한된 데이터 환경에서 YOLO 기반 ROI 자동탐지의
기술적 가능성을 확인한 개발단계 결과이며,
실제 생산환경 적용을 위해서는 새로운 독립 실데이터를 이용한
추가 검증이 필요하다.
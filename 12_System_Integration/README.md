# 12. System Integration

## 1. 개요

본 폴더는 **YOLO + OpenCV 기반 자동차 조향장치 샤프트 외경 자동측정 시스템**을 현장 적용 형태로 확장하기 위한 시스템 통합 구조를 정리한다.

프로젝트의 측정 알고리즘은 다음 흐름으로 구성된다.

**이미지 입력 → ROI 탐색/설정 → V3 Reflection Edge 검출 → 정밀 Edge 처리 → Pixel 외경 계산 → Calibration → mm 변환 → 규격 비교 → OK/NG 판정**

`12_System_Integration`에서는 이러한 측정엔진을 Backend, Frontend, Database와 연결하여 실제 현장에서 사용할 수 있는 시스템 구조로 확장하였다.

---

## 2. 시스템 구성

```text
12_System_Integration/
│
├─ backend/
│
├─ database/
│
├─ frontend/
│
├─ measurement/
│  ├─ images/
│  ├─ models/
│  ├─ output/
│  ├─ measurement_engine.py
│  └─ measurement_engine_EDGE_V3_REFLECTION.py
│
├─ measurement_data/
│  └─ results/
│     └─ calibration_records.csv
│
├─ .gitignore
├─ README.md
└─ start_field_measurement.bat
```

---

## 3. 폴더별 역할

### `backend/`

측정엔진을 외부 시스템에서 호출할 수 있도록 연결하기 위한 Backend 영역이다.

향후 FastAPI 기반 API 형태로 확장하여 다음 기능을 제공할 수 있다.

- 이미지 입력
- 측정 실행
- 측정결과 반환
- OK/NG 판정값 전달
- 측정 이력 저장 연계

---

### `frontend/`

사용자가 측정시스템을 쉽게 사용할 수 있도록 하는 화면 영역이다.

Frontend에서는 다음 정보를 표시할 수 있다.

- 입력 이미지
- 측정 ROI
- Edge 검출 결과
- Pixel 측정값
- mm 변환값
- 규격 상·하한
- OK/NG 판정
- 측정 이력

---

### `database/`

측정결과와 검사 이력을 저장하기 위한 영역이다.

향후 다음 항목을 저장하여 품질 추적성과 분석에 활용할 수 있다.

- 측정 일시
- 시편 ID
- Pixel 측정값
- mm 측정값
- 기준 실측값
- 규격
- OK/NG
- Calibration 정보
- 사용 알고리즘 버전

---

## 4. Measurement Engine

### 최종 기준 측정엔진

```text
measurement/measurement_engine_EDGE_V3_REFLECTION.py
```

본 프로젝트의 최종 기준 측정엔진은 **V3 Reflection Edge 방식**이다.

주요 기능은 다음과 같다.

- 실제 측정부 ROI 기반 측정
- Upper Edge 검출
- Lower Edge 검출
- Gradient 방향 기반 Edge 후보 선택
- Multi-point Edge 측정
- Sub-pixel Edge 위치 산출
- Median 기반 대표값 산출
- MAD 기반 이상점 제거
- Line Fitting
- Reflection Edge 대응
- Pixel 외경 계산
- Calibration 기반 mm 변환
- 도면 규격 기반 OK/NG 판정

---

## 5. 기존 Measurement Engine

```text
measurement/measurement_engine.py
```

`measurement_engine.py`는 프로젝트 초기 및 이전 단계에서 사용한 기본 측정엔진이다.

현재 프로젝트의 최종 성능평가 및 정밀 Edge 측정 기준은 다음 파일을 사용한다.

```text
measurement_engine_EDGE_V3_REFLECTION.py
```

따라서 `measurement_engine.py`는 개발 이력 및 이전 버전 비교를 위한 파일로 유지한다.

---

## 6. V3 Reflection Edge 적용 배경

실제 금속 샤프트 영상에서는 다음 문제가 발생하였다.

- 금속 표면 반사
- 가공무늬
- 내부 Edge 오검출
- 실제 외곽 Edge와 반사 Edge의 혼동
- 촬영조건에 따른 Edge 위치 변화

초기 Edge 방식에서는 강한 내부 Edge를 실제 샤프트 외곽으로 선택하는 사례가 발생하였다.

이를 개선하기 위해 V3에서는 실제 샤프트 외곽 경계를 보다 안정적으로 추적하는 **Reflection Edge 처리 방식**을 적용하였다.

---

## 7. 측정 ROI

최종 측정에서는 샤프트의 실제 외경 측정부를 ROI로 사용한다.

ROI 설정 시 다음 원칙을 적용하였다.

- 실제 제품 측정부와 영상 ROI 위치 일치
- 단차부 제외
- 형상 변화부 제외
- 반사 영향이 큰 영역 최소화
- 동일 시편 간 측정위치 표준화

최종 성능평가에서는 실제 외경 측정부 **10.2 mm 영역**을 기준으로 설정하고, 그중 **중앙 5 mm 영역**을 최종 표준 측정구간으로 사용하였다.

중앙 5 mm를 적용한 목적은 단순히 측정값을 개선하기 위한 것이 아니라 다음 영향을 줄이기 위한 것이다.

- 양끝 단차 영향
- 형상 변화
- 반사 Edge
- 측정위치 불일치
- 표면거칠기 측정위치와 영상 측정위치 차이

---

## 8. Calibration

최종 Pixel → mm 변환에는 다음 선형식을 적용하였다.

```text
mm = 0.002394212845 × pixel + 18.226123549383
```

대표 Pixel은 유효 Edge Point의 **Median**을 기준으로 계산한다.

Calibration 결과 및 관련 기록은 다음 위치에서 관리한다.

```text
measurement_data/results/
└─ calibration_records.csv
```

현재 Calibration은 Pilot/PoC 단계에서 구축된 것이므로 다른 촬영조건이나 광학계에 그대로 적용해서는 안 된다.

---

## 9. 측정 흐름

최종 측정 흐름은 다음과 같다.

```text
Input Image
     ↓
ROI Detection / ROI Setting
     ↓
V3 Reflection Edge Detection
     ↓
Upper / Lower Edge
     ↓
Sub-pixel Processing
     ↓
Line Fitting + MAD
     ↓
Representative Pixel
     ↓
Pixel → mm Calibration
     ↓
Specification Comparison
     ↓
OK / NG
```

YOLO는 측정 위치를 찾는 역할을 담당하며, 외경값 자체는 OpenCV 정밀 Edge 측정을 통해 계산한다.

---

## 10. 현장 실행

현장 실행을 위한 시작 스크립트는 다음 파일이다.

```text
start_field_measurement.bat
```

이 파일을 통해 측정 관련 서비스 또는 프로그램을 순차적으로 실행할 수 있도록 구성하였다.

실제 실행환경에서는 Python 환경, Backend, Frontend, Database 설정을 확인한 후 실행해야 한다.

---

## 11. 측정 데이터 관리

측정 및 Calibration 관련 결과는 다음 위치에서 관리한다.

```text
measurement_data/
└─ results/
   └─ calibration_records.csv
```

측정 결과와 Calibration 기록을 분리하여 관리함으로써 향후 다음 작업에 활용할 수 있다.

- Calibration 이력관리
- 측정값 추적
- 장비 조건 비교
- 알고리즘 버전 비교
- 품질 분석

---

## 12. 프로젝트 내 역할 구분

본 시스템에서 각 구성요소의 역할은 다음과 같다.

| 구성 | 역할 |
|---|---|
| YOLO | 측정 대상 ROI 탐색 |
| OpenCV V3 | 실제 외곽 Edge 정밀 측정 |
| Calibration | Pixel → mm 변환 |
| 판정 로직 | 규격 비교 및 OK/NG |
| Backend | 측정 알고리즘 서비스화 |
| Frontend | 측정 결과 표시 |
| Database | 측정결과 및 이력 저장 |
| Batch Script | 현장 실행 지원 |

---

## 13. 현재 시스템의 의미

본 시스템은 다음 기능을 하나의 흐름으로 연결하였다.

**영상 입력 → 측정영역 결정 → 정밀 Edge 측정 → 실제 치수 변환 → 규격 판정 → 결과 관리**

이를 통해 단순 OpenCV 실험 수준을 넘어 **현장 적용을 고려한 End-to-End 측정시스템 구조**를 구성하였다.

다만 현재 단계는 Pilot / PoC 수준이다.

현재 결과만으로 다음 항목이 검증되었다고 판단하지 않는다.

- ±0.010 mm 양산 측정능력
- Gauge R&R 수준의 반복성·재현성
- 장기간 생산환경 안정성
- 다양한 실제 제품에 대한 일반화 성능

---

## 14. 향후 개선 방향

향후 실제 양산 측정시스템으로 확장하기 위해 다음 항목을 우선적으로 검토한다.

1. Telecentric Lens 적용
2. 산업용 Global Shutter Camera 적용
3. Backlight 기반 Silhouette 촬영
4. 고정 Jig 및 광축 정렬
5. 복수 기준물 Calibration
6. Calibration / Independent Validation 완전 분리
7. Edge Quality Gate 및 Reject Logic
8. 반복성·재현성 평가
9. 생산환경 Pilot Test
10. 측정 이력 Database 및 Dashboard 연계

---

## 15. 최종 정리

`12_System_Integration`은 본 프로젝트에서 개발한 샤프트 외경 측정 알고리즘을 실제 현장 시스템 구조로 확장하기 위한 통합 단계이다.

최종 측정엔진은 다음 파일을 기준으로 한다.

```text
measurement/measurement_engine_EDGE_V3_REFLECTION.py
```

본 프로젝트의 핵심 시스템 구조는 다음과 같다.

**ROI 탐색 → V3 Reflection Edge → 정밀 Pixel 측정 → Calibration → mm 변환 → OK/NG → Backend / Database / Frontend 연계**

현재 시스템은 **기능 구현 및 Pilot 수준의 기술 가능성 검증 단계**이며, 향후 광학계와 고정조건을 안정화하고 Independent Validation 및 측정시스템 신뢰성 평가를 수행한 후 현업 적용 가능성을 최종 판단한다.


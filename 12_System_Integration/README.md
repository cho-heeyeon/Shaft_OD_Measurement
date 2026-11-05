# 12. System Integration

## 1. 개요

본 폴더는 **YOLO + OpenCV 기반 자동차 조향장치 샤프트 외경 자동측정 시스템**을 현장 적용 가능한 형태로 확장하기 위한 시스템 통합 구조를 정리한다.

본 프로젝트에서는 영상 기반 외경 측정 알고리즘을 개발하고, Calibration과 규격 판정 기능을 연결하여 정밀측정의 기술적 가능성을 검토하였다.

기본 측정 흐름은 다음과 같다.

```text
Input Image
    ↓
ROI Detection / Setting
    ↓
V3 Reflection Edge Detection
    ↓
Upper / Lower Edge Extraction
    ↓
Sub-pixel Processing
    ↓
Line Fitting + MAD Filtering
    ↓
Representative Diameter (Pixel)
    ↓
Pixel-to-mm Calibration
    ↓
Specification Comparison
    ↓
OK / NG Decision
```

`12_System_Integration`은 해당 측정엔진을 Backend, Frontend, Database 및 현장 실행환경과 연계하기 위한 통합 구조를 다룬다.

현재 단계는 **Pilot / PoC 기반 시스템 통합 및 현장 적용성 검토 단계**이며, 양산 측정능력의 확보를 의미하지 않는다.

## 2. 시스템 구성

```text
12_System_Integration/
│
├── backend/
│
├── database/
│
├── frontend/
│
├── measurement/
│   ├── images/
│   ├── models/
│   ├── output/
│   ├── measurement_engine.py
│   └── measurement_engine_EDGE_V3_REFLECTION.py
│
├── measurement_data/
│   └── results/
│       └── calibration_records.csv
│
├── .gitignore
├── README.md
└── start_field_measurement.bat
```

위 구조는 측정 알고리즘, 서비스 연계, 사용자 화면 및 데이터 관리를 기능별로 분리하기 위한 것이다.

각 폴더의 존재와 실제 기능 구현 완료 여부는 구분하여 관리한다.

## 3. 폴더별 역할

### 3.1 backend/

측정엔진을 다른 프로그램이나 사용자 화면에서 호출하기 위한 Backend 영역이다.

FastAPI 기반 서비스로 확장할 경우 다음 기능을 제공할 수 있다.

- 측정 이미지 입력 및 유효성 검사
- V3 측정엔진 호출
- 측정 결과 반환
- OK/NG 판정 결과 전달
- 오류 처리 및 실행 이력 관리
- 데이터베이스 저장 연계

API 구현과 실제 실행 여부는 Backend 소스코드 및 통합시험 결과로 확인한다.

### 3.2 frontend/

현장 작업자가 측정 결과를 확인할 수 있도록 하는 사용자 화면 영역이다.

주요 화면 구성 대상은 다음과 같다.

- 입력 이미지
- 측정 ROI
- Upper / Lower Edge 검출 결과
- 대표 Pixel 외경
- Calibration 적용 측정값(mm)
- 규격 상한 및 하한
- OK / NG 판정
- 측정 품질 및 오류 상태
- 측정 이력

현장 적용 시 정상 측정 결과와 측정 실패 또는 품질 불충분 상태를 구분하여 표시하도록 설계한다.

### 3.3 database/

측정 데이터와 검사 이력을 관리하기 위한 영역이다.

주요 관리 대상은 다음과 같다.

- 측정 일시 및 시편 ID
- 대표 Pixel 외경
- 변환된 외경(mm)
- 기준 실측값(존재하는 경우)
- 규격 상한 및 하한
- OK / NG 판정
- 측정 품질 상태
- Calibration ID 및 적용 회귀식 버전
- 측정엔진 및 설정 버전
- 촬영장비와 촬영조건
- 이미지 및 결과 파일 식별정보

해당 데이터는 향후 품질 추적성, 재현성 평가 및 측정시스템 개선에 활용한다.

## 4. 최종 기준 측정엔진

최종 기준 측정엔진은 다음 파일이다.

```text
measurement/
└── measurement_engine_EDGE_V3_REFLECTION.py
```

V3 Reflection Edge 방식은 금속 샤프트 외곽 경계의 검출 안정성을 높이기 위해 개발한 측정 알고리즘이다.

주요 처리 항목은 다음과 같다.

1. 실제 측정부 ROI 설정
2. Upper / Lower Edge 후보 검출
3. Gradient 방향 기반 Edge 후보 평가
4. 다중 지점 Edge 측정
5. Sub-pixel 위치 추정
6. Line Fitting
7. MAD 기반 이상점 제거
8. 유효 직경 Pixel의 대표값 계산
9. Calibration을 이용한 mm 변환
10. 규격 비교 및 OK/NG 판정

각 기능의 구체적인 구현 순서와 옵션은 실제 V3 엔진 소스코드를 기준으로 한다.

측정엔진의 기능 구현과 측정 정확도 및 신뢰성 확보 여부는 별도로 평가한다.

## 5. 기존 Measurement Engine

```text
measurement/
└── measurement_engine.py
```

`measurement_engine.py`는 초기 및 이전 개발 단계에서 사용한 측정엔진이다.

이 파일은 개발 이력과 알고리즘 비교를 위한 목적으로 유지한다.

현재 기준 측정엔진은 다음과 같다.

```text
measurement_engine_EDGE_V3_REFLECTION.py
```

현장 실행 및 성능평가에서는 실제 호출되는 엔진 버전과 설정을 명확하게 기록한다.

## 6. V3 Reflection Edge 적용 배경

금속 샤프트 영상에서는 다음 문제가 확인되었다.

- 금속 표면 반사
- 가공무늬 및 표면 거칠기 영향
- 내부 Edge 오검출
- 실제 외곽 Edge와 반사 경계의 혼동
- 촬영조건에 따른 Edge 위치 변동
- ROI 설정 및 측정 위치 불일치

기존 Edge 검출에서는 영상의 강한 내부 경계를 실제 외곽으로 선택하는 사례가 발생하였다.

이에 따라 외곽 경계 후보와 측정 위치의 일관성을 개선하기 위한 V3 Reflection Edge 방식을 적용하였다.

다만 표면 거칠기와 반사에 따른 측정 편향이 완전히 제거되었다고 판단하지 않는다.

## 7. 측정 ROI 및 중앙 5 mm 표준구간

최종 평가에서는 실제 샤프트 외경 측정부를 기준으로 ROI를 설정하였다.

### 7.1 측정 ROI

```text
Original Image : 16320 × 7532 px

ROI:
x1 = 8008
y1 = 3329
x2 = 8280
y2 = 4276
```

설정한 ROI는 샤프트의 실제 외경 측정부 약 10.2 mm 구간에 대응한다.

### 7.2 중앙 5 mm 표준구간

측정부 전체 영역 중 중앙 약 5 mm 구간을 주요 분석 및 비교 구간으로 설정하였다.

이 구간을 적용한 목적은 다음과 같다.

- 단차 및 형상 변화 영향 최소화
- 측정 위치 표준화
- 반사에 의한 Edge 오검출 감소
- 표면 거칠기 측정 위치와 영상 측정 위치의 대응
- 시편별 측정조건 비교의 일관성 확보

중앙 5 mm 범위는 실제 이미지 좌표에 따라 정의하고, ROI 비율만으로 구간을 지정하는 방식과 혼동하지 않도록 한다.

측정 시 유효 Edge Point를 기준으로 대표 외경을 계산한다.

## 8. Calibration

Pixel 측정값을 실제 외경(mm)으로 변환하기 위해 실측 기준값과 영상 측정값을 이용한 선형 Calibration을 적용하였다.

최종 적용 회귀식은 다음과 같다.

```text
Diameter (mm)
= 0.002394212845 × Pixel
+ 18.226123549383
```

여기서 Pixel은 측정 알고리즘이 산출한 대표 직경 Pixel 값이다.

대표값은 유효 직경 측정점에 대한 강건 통계처리를 바탕으로 계산한다.

본 Calibration은 특정 촬영조건과 시편 데이터를 이용해 구축한 실험적 변환식이다.

따라서 다음 조건이 변경될 경우 재검교정 및 별도 검증이 필요하다.

- 촬영거리
- 카메라와 렌즈
- 해상도 및 영상 스케일
- 지그 및 광축 정렬
- 조명조건
- ROI 및 Edge 검출 설정

Calibration 관련 기록은 다음 위치에서 관리한다.

```text
measurement_data/results/
└── calibration_records.csv
```

Calibration과 Independent Validation은 데이터 누출을 방지하기 위해 구분하여 수행하며, 검증 성능은 별도 결과로 보고한다.

## 9. 측정 및 규격 판정

대상 제품은 자동차 조향장치용 샤프트이다.

### 도면 기준

| 항목 | 기준 |
|---|---|
| 기준 외경 | 20.020 mm |
| 허용 공차 | ±0.010 mm |
| 하한 규격(LSL) | 20.010 mm |
| 상한 규격(USL) | 20.030 mm |

### 판정 로직

```python
if 20.010 <= diameter_mm <= 20.030:
    result = "OK"
else:
    result = "NG"
```

단, 위 판정은 정상적인 유효 측정값이 확보된 경우에 한하여 적용한다.

Edge 검출 실패, 유효점 부족, 측정 품질 불충분 또는 Calibration 적용조건 이탈 시에는 별도 오류 또는 재측정 상태를 반환하도록 개선할 계획이다.

이러한 품질 판정 로직은 실제 현장 적용 전 반드시 검증해야 한다.

## 10. 현장 실행 구조

현장 실행 진입점으로 다음 파일을 관리한다.

```text
start_field_measurement.bat
```

해당 스크립트는 측정 프로그램 또는 관련 서비스를 실행하기 위한 Windows 배치 파일이다.

실제 실행 가능 여부는 BAT 파일 내용과 설치환경에 따라 결정된다.

현장 실행 전 확인할 사항은 다음과 같다.

- Python 및 필수 패키지 설치
- 측정엔진과 모델 파일 경로
- 입력 이미지 경로
- ROI 및 Calibration 설정
- Backend 실행 여부
- Frontend 실행 여부
- 결과 저장 경로 및 접근 권한

시스템 통합시험에서는 영상 입력부터 측정결과 저장까지 실제 동작하는 기능 범위를 확인한다.

## 11. 측정 데이터 및 이력 관리

현재 Calibration 관련 기록은 다음 경로에 관리한다.

```text
measurement_data/
└── results/
    └── calibration_records.csv
```

향후 측정 결과와 Calibration 기록을 구분하여 관리한다.

주요 관리 목표는 다음과 같다.

- Calibration 이력 추적
- 측정 결과의 재현 가능성 확보
- 시편별 측정값 비교
- 촬영조건별 성능 비교
- 알고리즘 버전별 성능 비교
- 품질 데이터 분석
- 측정 오류 및 재측정 이력 관리

데이터베이스가 적용되는 경우 원본 이미지, 측정 결과 및 Calibration 정보를 연결할 수 있도록 식별정보를 일관되게 부여한다.

## 12. 시스템 구성요소별 역할

| 구성요소 | 주요 역할 |
|---|---|
| YOLO | 측정 대상 및 ROI 탐색 |
| OpenCV V3 | 정밀 Edge 검출 및 Pixel 외경 계산 |
| Calibration | Pixel 측정값을 mm로 변환 |
| 판정 로직 | 도면 규격과 측정값 비교 |
| Backend | 측정 알고리즘 호출 및 서비스 연계 |
| Frontend | 측정 화면 및 결과 표시 |
| Database | 측정 결과와 품질 이력 관리 |
| Batch Script | Windows 현장 실행 지원 |

YOLO는 측정 대상 위치를 찾는 역할을 수행하며, 외경값 자체는 OpenCV 기반 정밀 Edge 측정으로 산출한다.

Backend, Frontend, Database의 구현 및 연동 완료 범위는 실제 코드와 실행 결과를 기준으로 관리한다.

## 13. 현재 개발 단계 및 검증 범위

본 프로젝트에서는 다음 요소를 개발 및 검토하였다.

- YOLO 기반 ROI 탐색
- OpenCV 기반 외경 측정
- V3 Reflection Edge 측정엔진
- Pixel-to-mm Calibration
- 도면 규격 기반 OK/NG 판정
- 중앙 5 mm 표준 측정구간
- 현장 적용을 위한 시스템 통합 구조

현 단계는 **Pilot / PoC 기반 기술 가능성 검토 단계**이다.

다음 항목은 추가적인 정량 검증이 필요하다.

| 검증 항목 | 현재 판단 |
|---|---|
| 측정 알고리즘 구성 | 개발 및 실험 진행 |
| V3 Reflection Edge | 적용 및 평가 진행 |
| Calibration | 실험적 회귀식 확보 |
| Independent Validation | 추가 검증 필요 |
| Backend / Frontend / DB 통합 | 실제 연동 확인 필요 |
| ±0.010 mm 양산 측정능력 | 미입증 |
| Gauge R&R | 미검증 |
| 장기간 생산환경 안정성 | 미검증 |
| 실제 제품군 일반화 성능 | 추가 검증 필요 |

특정 시편에서 작은 측정오차가 확인되더라도 이를 전체 제품에 대한 정밀도 또는 양산 측정능력으로 일반화하지 않는다.

## 14. 향후 개선 방향

현장 적용을 위한 주요 개선과제는 다음과 같다.

### 14.1 광학계 및 기구 안정화

- Telecentric Lens 도입 검토
- 산업용 Global Shutter Camera 도입
- Backlight 기반 Silhouette 영상 확보
- 고정 Jig 및 광축 정렬
- 외부광 및 반사 차단
- 측정 위치 표준화

### 14.2 측정 알고리즘 개선

- 실제 외곽 Edge 선택 안정화
- Edge Quality Gate 도입
- 유효 Edge Point 평가
- 이상 측정값 Reject Logic
- 측정 실패 원인 기록
- 표면 거칠기와 측정 편향의 관계 검증

### 14.3 Calibration 및 신뢰성 확보

- 복수 기준물 기반 Calibration
- Calibration / Independent Validation 분리
- 반복성 및 재현성 평가
- Gauge R&R 검토
- 측정 불확도 평가
- 합격/불합격 판정 신뢰성 검증

### 14.4 시스템 통합 및 현장 적용

- Backend API 연계 검증
- Frontend 측정 화면 검증
- Database 측정 이력 저장
- 현장 실행 스크립트 검증
- 측정 오류 처리 및 로그 관리
- 생산환경 Pilot Test

## 15. 시스템 통합 결과 및 향후 과제

### 15.1 시스템 통합 결과

본 프로젝트에서는 YOLO 기반 측정영역 탐색과 OpenCV V3 Reflection Edge 기반 정밀 외경 측정 알고리즘을 개발하고, FastAPI Backend 및 Streamlit Frontend를 활용한 현장 측정시스템 통합 구조를 구현하였다.

주요 구현 및 확인 결과는 다음과 같다.

- V3 Reflection Edge 측정엔진 구현 및 단독 실행 확인
- YOLO 모델을 이용한 측정영역 탐색 기능 구현
- Sub-pixel, Line Fitting, MAD 및 Median 기반 외경 측정 기능 구현
- 최종 Pixel-to-mm Calibration 회귀식 설정
- FastAPI 서버 실행 및 Health Check 정상 응답 확인
- Streamlit V2 현장 측정 화면 실행 확인
- Calibration·Independent Validation·Measurement 기능 구성
- SQLite 및 CSV 기반 측정 이력 저장 기능 구현

다만 SQLite·CSV 저장 기능의 실제 End-to-End 통합시험은 추가 확인이 필요하다.

### 15.2 시스템 처리 흐름

```text
Image Input
    ↓
YOLO ROI Detection / Setting
    ↓
V3 Reflection Edge Detection
    ↓
Sub-pixel + Line Fitting + MAD
    ↓
Representative Pixel Measurement
    ↓
Pixel-to-mm Calibration
    ↓
Diameter (mm)
    ↓
Specification Comparison
    ↓
OK / NG Decision
    ↓
FastAPI / SQLite / Streamlit Integration
```

### 15.3 검증 범위 및 한계

현재 시스템은 Pilot/PoC 단계의 기술적 가능성 검토 결과물이다.

측정엔진 단독 실행과 Backend·Frontend 서버 구동을 확인하였으나, 다음 항목은 추가 검증이 필요하다.

- 실제 End-to-End 측정 및 데이터 저장 검증
- 최종 촬영조건에 대한 Independent Validation
- 중앙 5 mm 표준 측정구간의 코드 정합성 확인
- 측정 반복성 및 재현성 평가
- 측정 불확도 및 판정 신뢰성 평가
- ±0.010 mm 공차에 대한 양산 측정능력 검증
- 장기간 생산환경 안정성 평가

### 15.4 향후 개선 방향

향후 현장 적용 및 양산 확장을 위해 다음 사항을 검토한다.

- Telecentric Lens와 산업용 Global Shutter Camera 도입
- Backlight 기반 Silhouette 촬영 및 고정 Jig 적용
- 촬영거리·광축·측정위치 표준화
- Edge Quality Gate 및 Reject Logic 강화
- Calibration과 Independent Validation의 완전 분리
- SQLite·CSV 저장 및 측정 이력 추적성 검증
- Gauge R&R 및 측정 불확도 평가
- 실제 생산환경 Pilot Test

### 15.5 종합 결론

`12_System_Integration`은 개발된 샤프트 외경 자동측정 알고리즘을 현장 적용을 고려한 시스템 구조로 확장한 결과물이다.

V3 Reflection Edge 측정엔진과 FastAPI·Streamlit 기반 프로그램을 구성하고, 측정엔진 단독 실행 및 서버 구동을 확인하였다.

현재 단계는 Pilot/PoC 수준이며, 실제 생산현장 적용 여부는 독립 Validation과 측정시스템 신뢰성 평가를 거쳐 최종 판단한다.


# 12. System Integration — Shaft OD Measurement System

## 1. 목적

본 단계에서는 기존에 개발한 YOLO + OpenCV 기반
샤프트 외경 자동측정 End-to-End V1을
Backend, Database, Frontend와 연결하여 하나의 시스템으로 통합하였다.

기존 측정 알고리즘의 처리 흐름은 다음과 같다.

이미지 입력  
→ YOLO ROI 탐지  
→ OpenCV 정밀 Edge 측정  
→ Pixel 외경 계산  
→ Calibration  
→ mm 변환  
→ 도면 규격 비교  
→ OK/NG 판정

System Integration 단계에서는 여기에 다음 기능을 추가하였다.

Streamlit Frontend  
→ FastAPI Backend  
→ Measurement Engine  
→ SQLite Database

이를 통해 사용자가 이미지를 업로드하면
측정 엔진이 외경을 계산하고,
측정 결과를 화면에 표시하면서
Database에 측정 이력을 저장하는 기본 시스템 구조를 구현하였다.


---

## 2. 전체 시스템 구조

현재 구현된 시스템의 전체 흐름은 다음과 같다.

```text
사용자
  ↓
Streamlit Frontend
  ↓
이미지 Upload
  ↓
FastAPI Backend
  ↓
POST /measure
  ↓
YOLO ROI Detection
  ↓
OpenCV Precision Measurement
  ↓
Calibration
  ↓
mm 변환
  ↓
도면 규격 비교
  ↓
OK / NG 판정
  ↓
SQLite Database 저장
  ↓
Streamlit 측정 결과 표시

3. 프로젝트 구조

12_System_Integration/
│
├── backend/
│   ├── main.py
│   ├── uploads/
│   └── images/
│       ├── backend_health_200.png
│       └── backend_measure_200.png
│
├── database/
│   ├── database.py
│   ├── measurement.db
│   └── images/
│       ├── database_measure_save_200.png
│       └── database_record_check.png
│
├── frontend/
│   ├── streamlit_app.py
│   └── images/
│       └── frontend_measure_result.png
│
├── measurement/
│   ├── measurement_engine.py
│   ├── models/
│   │   └── best.pt
│   ├── images/
│   └── output/
│
└── README.md

4. Measurement Engine

measurement/measurement_engine.py는
기존 Day027 End-to-End V1 측정 로직을
System Integration 구조에서 사용할 수 있도록 구성한 측정 엔진이다.

주요 처리 과정은 다음과 같다.

입력 이미지
↓
YOLO 모델
↓
샤프트 ROI 탐지
↓
OpenCV 영상 처리
↓
Gradient 기반 Edge 탐색
↓
Multi-point 측정
↓
Sub-pixel Edge 계산
↓
Pixel 외경 계산
↓
Calibration
↓
mm 변환
↓
규격 비교
↓
OK / NG

5. Calibration 및 규격 판정

현재 V1에서 사용한 Calibration 기준값은 다음과 같다.

Calibration pixel : 464.0600 px
Calibration reference : 20.0210 mm

제품 규격은 다음과 같다.

Ø20.020 ± 0.010 mm

따라서 판정 범위는 다음과 같다.

20.010 mm ≤ 측정값 ≤ 20.030 mm

이 범위 안이면 OK,
범위를 벗어나면 NG로 판정한다.

현재 Calibration은 단일 기준값을 이용한 V1 구조이며,
복수 기준물을 이용한 Calibration 및 독립 Validation은
추가 검증이 필요하다.

6. FastAPI Backend

Backend는 FastAPI를 이용하여 구성하였다.

주요 API는 다음과 같다.

GET /health

서버가 정상적으로 실행되고 있는지 확인하기 위한 API이다.

실행 테스트 결과 HTTP 상태코드 200 응답을 확인하였다.

POST /measure

사용자가 업로드한 샤프트 이미지를
측정 엔진으로 전달하기 위한 API이다.

처리 과정은 다음과 같다.

이미지 Upload
↓
FastAPI
↓
Measurement Engine 실행
↓
측정 결과 생성
↓
Database 저장
↓
Response 반환

실제 sample_07.jpg를 업로드하여
HTTP 상태코드 200과 측정 결과 반환을 확인하였다.

7. 측정 실행 결과

System Integration 테스트에서는
sample_07.jpg를 입력 이미지로 사용하였다.

확인된 실행 결과는 다음과 같다.

| 항목                |                 결과 |
| ----------------- | -----------------: |
| YOLO confidence   |           0.784195 |
| Calibration pixel |        464.0600 px |
| Calibration mm    |         20.0210 mm |
| Measured pixel    |        464.0575 px |
| Measured mm       |         20.0209 mm |
| STD pixel         |          1.0460 px |
| Error             |         -0.0001 mm |
| Specification     | 20.010 ~ 20.030 mm |
| Result            |                 OK |


이 결과는 측정 엔진과 Backend가 연결되어
전체 처리 과정이 실행됨을 확인한 결과이다.

단, sample_07은 Calibration 기준에 사용된 이미지이므로
-0.0001 mm 결과를 독립적인 측정 정확도 검증 결과로
해석해서는 안 된다.

8. SQLite Database

측정 결과를 저장하기 위해
SQLite Database를 구성하였다.

Database 파일은 다음과 같다.

database/measurement.db

측정 시 저장하는 주요 정보는 다음과 같다.

측정 일시
이미지 파일명
YOLO confidence
측정 Pixel
측정 mm
규격 하한
규격 상한
OK/NG 결과

실제 /measure API 실행 후
SQLite Database에 측정 결과가 저장되는 것을 확인하였다.
Database 조회를 통해 저장된 측정 기록도 확인하였다.


9. Streamlit Frontend

사용자가 측정 시스템을 쉽게 사용할 수 있도록
Streamlit 기반 Frontend를 구성하였다.

사용자는 화면에서 샤프트 이미지를 선택하고
외경 측정을 실행할 수 있다.

Frontend의 기본 흐름은 다음과 같다.

샤프트 이미지 선택
↓
외경 측정
↓
FastAPI /measure 요청
↓
측정 엔진 실행
↓
측정 결과 수신
↓
화면 표시

실제 sample_07.jpg를 업로드하여
측정 결과가 Streamlit 화면에 표시되는 것을 확인하였다.


10. System Integration에서 확인된 기능

현재 단계에서 실제 실행으로 확인한 기능은 다음과 같다.

| 기능                    | 상태          |
| --------------------- | ----------- |
| YOLO ROI 탐지           | 구현          |
| OpenCV 외경 측정          | 구현          |
| Multi-point 측정        | 구현          |
| Sub-pixel 처리          | 구현          |
| Pixel → mm 변환         | 구현          |
| 규격 비교                 | 구현          |
| OK/NG 판정              | 구현          |
| Measurement Engine 실행 | 확인          |
| FastAPI Backend       | 구현          |
| GET /health           | HTTP 200 확인 |
| POST /measure         | HTTP 200 확인 |
| 이미지 Upload            | 확인          |
| 측정 결과 API 반환          | 확인          |
| SQLite Database       | 구현          |
| 측정 결과 Database 저장     | 확인          |
| Database 기록 조회        | 확인          |
| Streamlit Frontend    | 구현          |
| Streamlit 측정 결과 표시    | 확인          |



11. 현재 구현과 현장 적용의 구분

이번 System Integration을 통해
소프트웨어 수준의 기본 통합 시스템은 구현하였다.

그러나 실제 생산라인 적용이 완료된 것은 아니다.

현재 구현
저장 이미지
↓
Streamlit
↓
FastAPI
↓
YOLO + OpenCV
↓
Calibration
↓
OK / NG
↓
SQLite

향후 현장 적용
Industrial Camera
↓
Image Acquisition
↓
Edge PC / Server
↓
FastAPI Backend
↓
YOLO + OpenCV
↓
Calibration
↓
OK / NG
↓
Production Database
↓
Dashboard / MES / PLC

따라서 현재 결과는
현장 시스템으로 확장하기 위한
소프트웨어 통합 V1으로 정의한다.


12. 현장 적용 전 추가 검증

현재 프로젝트에서는
±0.010 mm 수준의 양산 측정성능이
독립적으로 검증된 상태가 아니다.

따라서 실제 생산현장 적용 전 다음 검증이 필요하다.

서로 다른 실제 외경의 기준물 확보
복수 기준물 Calibration
Calibration과 Validation 데이터 분리
독립 샤프트 측정
기준 측정값과 Vision 측정값 비교
반복 측정 안정성 평가
제품 재장착 시험
제품 위치 변화 시험
조명 및 촬영조건 변화 시험
실제 생산환경 Pilot Test


13. 향후 시스템 확장

향후 다음과 같은 기능 확장을 검토할 수 있다.

Industrial Camera
↓
자동 Image Acquisition
↓
Measurement Server / Edge PC
↓
Vision Measurement
↓
OK / NG
↓
Database
↓
Dashboard
↓
PLC / MES / 품질관리 시스템

특히 정밀 치수 측정을 위해서는
알고리즘뿐만 아니라 다음 요소를 함께 검증해야 한다.

Industrial Camera
Camera Resolution
Lens
Telecentric Lens 적용 필요성
Lighting
제품 설치 위치
촬영 거리
Pixel/mm 해상도
Calibration 방법
반복성
재장착 영향


14. 결론

본 단계에서는 기존 YOLO + OpenCV 기반
샤프트 외경 측정 End-to-End V1을 기반으로

Streamlit
→ FastAPI
→ Measurement Engine
→ SQLite Database
를 연결한 System Integration V1을 구현하였다.

실제 이미지 업로드를 통해

Backend 서버 동작
이미지 전달
측정 엔진 실행
외경 측정
규격 비교
OK/NG 판정
API 결과 반환
Database 저장
Frontend 결과 표시

까지의 전체 소프트웨어 처리 흐름을 확인하였다.

따라서 현재 프로젝트는
단순한 외경 측정 알고리즘 구현에서 한 단계 확장되어
Frontend, Backend, Measurement Engine, Database가 연결된
통합 측정 시스템 V1 단계까지 구현되었다.

다만 이는 실제 양산 측정성능과 생산라인 적용이
검증 완료되었다는 의미는 아니다.

향후 복수 기준물 Calibration,
독립 Validation, 반복성 시험,
광학계 표준화 및 생산환경 Pilot Test를 통해
실제 현장 적용 가능성을 추가 검증해야 한다.


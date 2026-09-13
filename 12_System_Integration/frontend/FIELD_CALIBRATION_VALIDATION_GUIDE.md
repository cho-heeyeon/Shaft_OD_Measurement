# Shaft OD 현장 검증 V2 실행 순서

## 목적
기존 1점 Calibration을 다음 구조로 확장합니다.

1. **3점 반복 Calibration**: A/B/C
2. **독립 Validation**: D/E/F
3. **Measurement**: G/H/I/J

## 실행 전
- FastAPI 서버 실행
- 스마트폰/카메라 거리, 각도, 줌, 해상도 고정
- 샤프트 고정 지그와 백라이트 조건 고정
- Calibration용 A/B/C와 Validation용 D/E/F는 서로 다른 샤프트로 분리
- 각 기준값은 신뢰 가능한 계측기로 사전에 기록

## 1. Calibration
- A/B/C 각각 실제 mm 입력
- 각 샤프트를 기본 10회 반복 촬영
- 기존 YOLO/OpenCV 엔진이 각 사진에서 대표 외경 Pixel을 산출
- 샤프트별 Pixel 중앙값/평균/표준편차 확인
- 3개 대표 Pixel과 실측 mm로 `mm = a × pixel + b` 산출
- 새 Calibration 저장 시 기존 Validation 승인은 자동 해제

## 2. Validation
- Calibration에 사용하지 않은 D/E/F 사용
- 실제 기준 mm 입력
- 각 샤프트 기본 10회 반복 촬영
- 저장된 `a`, `b`로 mm 계산
- Error / Absolute Error / MAE / Max Absolute Error / Bias 확인
- 결과를 사람이 검토한 뒤 Measurement 사용 승인

> 프로그램이 자동으로 계측 정확성을 인증하지 않습니다. Validation 합격기준은 별도로 정의해야 합니다.

## 3. Measurement
- 승인된 Calibration 식 적용
- G/H/I/J 측정
- 대표 Pixel → mm 변환
- 20.010~20.030 mm 규격과 비교하여 OK/NG 표시
- 이미지와 CSV 자동 저장

## 실행 명령
`12_System_Integration` 폴더에서:

```powershell
python -m streamlit run frontend\streamlit_app_mobile_v2.py --server.address 0.0.0.0 --server.port 8501
```

기존 FastAPI는 별도 터미널에서 실행합니다.

## 실패 시 재촬영 / 초기화
- **Calibration A/B/C 중 한 시편만 실패**: `Calibration 재촬영 / 초기화`에서 해당 시편을 선택 → 삭제 확인 체크 → `선택 시편만 초기화 → 재촬영` 실행
  - 해당 시편의 CSV 기록과 촬영 이미지가 삭제됨
  - 기존 Calibration 식은 무효화됨
  - 이전 Validation 기록/승인도 자동 초기화됨
  - 다른 Calibration 시편 기록은 유지됨
- **Calibration 전체를 다시 시작**: `Calibration 전체 초기화` 사용
  - A/B/C 기록·이미지·Calibration 식 삭제
  - Validation 기록/승인도 함께 초기화
- **Validation D/E/F 중 한 시편만 실패**: `Validation 재촬영 / 초기화`에서 해당 시편만 초기화 후 재촬영
  - 해당 Validation 시편의 CSV 기록과 촬영 이미지가 삭제됨
  - Measurement 사용 승인은 자동 해제됨
  - Calibration 식은 유지됨
- **Validation 전체를 다시 시작**: `Validation 전체 초기화` 사용

> 잘못된 촬영값을 단순히 평균에 포함시키지 말고, 실패 원인을 확인한 뒤 해당 시편 기록을 초기화하고 동일 촬영조건에서 재촬영하세요.

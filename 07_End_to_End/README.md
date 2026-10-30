07_End_to_End

Shaft OD Measurement — End-to-End Prototype

본 폴더는 YOLO/OpenCV 기반 샤프트 외경 자동 정밀측정 프로젝트의 End-to-End 프로토타입 실행 결과를 정리한 폴더입니다.

현재 시스템은 다음 흐름으로 구성됩니다.
Input Image
   ↓
Measurement ROI
   ↓
V3 Reflection Edge Detection
   ↓
31-point Edge Measurement
   ↓
Sub-pixel + Robust Line Fitting
   ↓
Measured Pixel
   ↓
Pixel → mm Conversion
   ↓
Result / Diagnostic Output
현재 단계의 핵심 성과는 영상에서 샤프트 외경 Pixel을 자동 측정하는 End-to-End 프로토타입을 구현하고, 3차 반복 촬영을 통해 Calibration 한계와 개선 조건을 정량적으로 확인한 것입니다.

1. 프로젝트 목적
   
자동차 조향장치용 샤프트의 외경을 영상 기반으로 자동 측정하기 위한 프로토타입을 구현했습니다.

측정 대상 규격은 다음과 같습니다.
항목	값
기준 외경	20.020 mm
하한	20.010 mm
상한	20.030 mm
공차	±0.010 mm


프로젝트의 목표는 단순 이미지 분류가 아니라,
1. 측정 위치 탐색
2. 실제 물리 외곽 Edge 검출
3. Pixel 단위 외경 측정
4. Pixel → mm 변환
5. 측정 결과 출력
까지 이어지는 End-to-End 측정 흐름을 구현하는 것입니다.

2. End-to-End 측정 엔진
   
현재 End-to-End 측정은 기존의
measurement_engine_EDGE_V3_REFLECTION.py
를 사용합니다.

V3 Reflection 엔진의 주요 기능은 다음과 같습니다.
- 물리적 실루엣 Edge 방향을 이용한 상·하단 Edge 탐색
- 반사 영역 억제
- 31개 측정 위치 사용
- Dynamic Programming 기반 연속 Edge 선택
- Sub-pixel 보정
- Robust line fitting
- Median / MAD 기반 이상점 억제
- Pixel 외경 계산
End-to-End 코드는 Edge 측정 알고리즘을 새로 구현하지 않고 기존 V3 Reflection 엔진을 그대로 호출하는 구조로 구성했습니다.


3. 3차 촬영 기준 ROI
   
3차 촬영 데이터의 최종 Shaft 측정 ROI는 다음 좌표를 사용했습니다.
SHAFT ROI = [8008, 3329, 8280, 4276]
기준 이미지 크기:
16320 × 7532 pixel
NO1은 촬영 해상도가 달라 최신 정밀 ROI 기반 분석에서는 제외했습니다.

4. Calibration 재계산 데이터
   
3차 촬영 데이터 중 다음 세 시편을 이용해 Pixel과 실제 외경의 관계를 다시 확인했습니다.
시편	실제 외경	대표 Pixel	유효 이미지
NO6	20.011 mm	748.622508 px	9
NO2	20.020 mm	749.889325 px	10
NO3	20.028 mm	748.836126 px	10


NO6의 다음 이미지는 Edge 오선택 이상치로 판단하여 제외했습니다.
20261021_154352.jpg
NO3에는 Median + MAD 기반 이상치 판정을 추가했지만 통계적으로 제외되는 이미지는 없었습니다.


5. Pixel → mm 환산식
   
위 세 대표점을 이용한 1차 선형 회귀 결과는 다음과 같습니다.
mm = 0.002394212845 × pixel + 18.226123549383
따라서 기울기 기준으로 보면:
1 pixel ≈ 0.002394 mm
        ≈ 2.394 µm
입니다.

17 µm의 실제 치수 차이는 수치상 약 다음 Pixel 차이에 해당합니다.
17 µm ÷ 2.394 µm/pixel
≈ 7.1 pixel
즉 수치적인 Pixel 분해능 관점에서는 ±10 µm 공차를 다루기 위한 가능성이 확인되었습니다.


6. 1차~3차 촬영의 Pixel 분해능 비교
   
단계	약 mm/pixel	약 µm/pixel	17 µm 환산 Pixel
1차	0.007682	7.68 µm	약 2.2 px
2차	0.024814	24.81 µm	약 0.69 px
3차	0.002394	2.39 µm	약 7.1 px


3차 촬영은 수치적으로는 이전 단계보다 Pixel 분해능이 개선되었습니다.

그러나 작은 mm/pixel 값만으로 측정 정확도가 확보되었다고 판단할 수는 없습니다.


7. 3점 환산 결과
   
현재 선형식을 세 기준 시편에 적용하면 다음과 같습니다.
시편	실제값	환산값	Bias	절대오차
NO2	20.020 mm	약 20.02152 mm	+0.00152 mm	약 1.52 µm
NO3	20.028 mm	약 20.01900 mm	-0.00900 mm	약 9.00 µm
NO6	20.011 mm	약 20.01849 mm	+0.00749 mm	약 7.49 µm


세 시편 중 가장 큰 환산 오차는 NO3의 약 9.0 µm입니다.


8. Calibration 선형성 확인
   
현재 3점 회귀 결과:
R² = 0.03645
이며,
monotonic = false
입니다.

실제 외경 순서는:
NO6 20.011
<
NO2 20.020
<
NO3 20.028
이지만 대표 Pixel은:
NO6 748.623
NO3 748.836
NO2 749.889
순서입니다.

따라서 외경 증가에 따라 Pixel이 한 방향으로 증가하거나 감소하는 **단조성(Monotonicity)**이 확보되지 않았습니다.


9. 반복 측정 관점의 해석
    
현재 문제는 특정 한 장의 이상 촬영만으로 설명되지는 않습니다.

NO6의 명확한 이상 이미지 1장을 제외하고 NO3에 MAD 이상치 검사를 적용한 후에도 Pixel 순서는 정상적으로 정렬되지 않았습니다.

이는 현재 17 µm 범위에서:
- 시편 간 실제 Pixel 차이
- 촬영 위치 변화
- 광학 배율 변화
- 표면 반사
- Edge 선택 변동
- 시편 자세 및 깊이 변화
가 서로 비슷한 수준으로 영향을 주고 있음을 의미합니다.

특히 NO3와 NO6의 대표 Pixel 차이는 약:
0.214 pixel
에 불과해 반복 측정 흔들림보다 작습니다.

따라서 현재 조건에서는 Pixel → mm 관계를 안정적인 하나의 직선으로 표현하기 어렵습니다.


10. 현재 End-to-End 결과의 의미
    
현재 End-to-End 시스템에서 확인된 내용은 다음과 같습니다.
구현 완료
- 이미지 입력
- ROI 설정
- V3 Reflection Edge 측정
- 31-point 측정
- Sub-pixel 처리
- Robust fitting
- Pixel 외경 산출
- 반복 이미지 분석
- 이상 이미지 선별
- Pixel → mm 환산 실험
- 결과 파일 저장
확인된 성과
- 3차 촬영 기준 약 2.394 µm/pixel의 수치적 분해능 확인
- 반복 촬영 기반 Pixel 안정성 분석
- 명확한 Edge 오선택 이미지 선별 가능
- Calibration 실패 원인을 단순 코드 오류가 아니라 시편 간 분리도 대비 촬영·Edge 변동 문제로 좁힘
아직 검증되지 않은 항목
- ±10 µm 공차의 양산 측정 정확도
- 추적 가능한 최종 Pixel → mm Calibration
- Independent Validation
- 장기 측정 안정성
- 산업용 광학계 기준 반복재현성

  
11. 현재 Calibration 식 사용 시 주의사항
    
현재 식:
mm = 0.002394212845 × pixel + 18.226123549383
은 3차 촬영 데이터를 이용한 진단용 선형 환산식입니다.

현재 결정계수와 단조성 문제 때문에 다음 용도로 사용하면 안 됩니다.
X 양산 OK/NG 최종 판정
X 공인 측정 결과
X 최종 검교정 계수
현재 식은 다음 용도로 사용합니다.
O End-to-End 동작 확인
O Pixel → mm 변환 흐름 확인
O 3차 촬영 결과 분석
O Calibration 한계 분석
O 후속 광학계 개선 기준 수립


12. 실행 결과 이미지
    
본 폴더에는 End-to-End 코드 실행 결과와 Edge 측정 결과 이미지를 함께 보관합니다.

권장 구조:
07_End_to_End/
│
├─ README.md
├─ end_to_end_v3.py
│
├─ calibration/
│   └─ calibration_3point_recalculated.json
│
├─ results/
│   ├─ measurement_result.json
│   ├─ measurement_result.txt
│   └─ calibration_recalc_summary.csv
│
└─ images/
    ├─ end_to_end_execution.png
    ├─ edge_result_NO2.png
    ├─ edge_result_NO3.png
    └─ edge_result_NO6.png
실행 결과 이미지는 코드가 실제로 동작하고 Pixel 결과를 출력한 화면을 기록하는 용도로 사용합니다.


13. 프로젝트 최종 판단
    
본 프로젝트는 현재 단계에서 양산용 정밀 측정시스템 완성으로 판단하지 않습니다.

대신 다음 수준의 성과로 정리합니다.
YOLO와 OpenCV를 이용한 샤프트 외경 자동 정밀측정 시스템의 End-to-End 프로토타입을 구현하고, 반복 촬영·Calibration·Edge 안정성 시험을 통해 ±10 µm 공차 측정의 핵심 제한요인과 후속 산업용 광학계 전환 조건을 도출하였다.

특히 3차 촬영에서는 Pixel 분해능 자체는 개선되었으나, 시편 간 Pixel 순서성이 안정적으로 확보되지 않아 최종 Calibration을 확정하지 않았습니다.

이는 실패 결과를 숨기는 것이 아니라, 현재 스마트폰 기반 파일럿 시스템에서 정확도 한계가 어디에서 발생하는지 정량적으로 확인한 결과입니다.


14. 향후 개선 방향
    
추가 촬영 및 산업용 시스템으로 확장할 경우 다음 항목을 우선 검토합니다.
1. 텔레센트릭 렌즈
2. 산업용 Global Shutter 카메라
3. 텔레센트릭 또는 균일 백라이트
4. 카메라·지그·샤프트 고정 구조
5. 샤프트 깊이 및 자세 고정
6. 더 넓은 치수 범위의 Master 기준물
7. Edge Quality Gate 강화
8. Calibration 계수 동결 후 별도 Independent Validation
목표는 단순히 더 작은 µm/pixel을 만드는 것이 아니라,
동일 외경 → 동일 Pixel
외경 증가 → Pixel의 일관된 단조 변화
를 확보하는 것입니다.


15. 현재 프로젝트 상태
    
Prototype implementation        : 완료
V3 Reflection measurement       : 완료
3rd capture repeat test         : 완료
Outlier review                  : 완료
Pixel resolution evaluation     : 완료
3-point calibration experiment  : 완료
Calibration linearity           : 미충족
Independent validation          : 미완료
Production metrology validation : 미완료
따라서 현재 프로젝트는 End-to-End Prototype + Pilot Validation 단계로 마무리합니다.

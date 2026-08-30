# Line Fitting 기반 Edge 안정화

## 1. 목적

Multi-point 방식으로 검출된 여러 Edge 점은
반사광, 가공무늬 및 영상 노이즈 등에 의해
위치가 조금씩 흔들릴 수 있다.

따라서 상단과 하단에서 검출된 여러 Edge 점을
각각 하나의 직선으로 근사하여
샤프트 외곽 Edge의 전체적인 형태를 안정적으로 추정하였다.

## 2. 처리 방법

상단 Edge 점과 하단 Edge 점을 각각 수집한 후
NumPy의 `np.polyfit()`을 이용하여
1차 직선으로 근사하였다.

직선 모델은 다음과 같다.

`y = ax + b`

상단 Edge:

`top_y = top_a * x + top_b`

하단 Edge:

`bottom_y = bottom_a * x + bottom_b`

## 3. Line Fitting 조건

상단과 하단에서 각각 최소 5개 이상의
Edge 점이 확보된 경우 Line Fitting을 수행하였다.

## 4. 의미

개별 Edge 점 하나에 의존하지 않고
여러 Edge 점의 전체적인 분포를 이용하여
대표적인 상단 및 하단 Edge Line을 추정하였다.

이를 통해 일부 위치의 Edge 흔들림이
전체 외경 측정에 미치는 영향을 줄이고자 하였다.

## 5. 결과 이미지

Line Fitting 결과 이미지에서는 다음과 같이 표시하였다.

- 빨간 점: 검출된 상단 Edge 점
- 파란 점: 검출된 하단 Edge 점
- 초록선: `np.polyfit()`으로 계산한 상단 및 하단 대표 Edge Line
- 노란선: 중앙 위치에서 상단과 하단 fitted line 사이의 측정 구간

![Line Fitting 결과](./line_fitting_measurement.jpg)


## 6. 주의사항

Line Fitting 자체가 측정 정확도를 보장하는 것은 아니다.

검출된 Edge 점 자체가 실제 샤프트 외곽이 아닌 경우에는
잘못된 점들을 이용하여 직선을 계산할 수 있으므로,
실제 외곽 Edge 선택 과정과 함께 사용해야 한다.
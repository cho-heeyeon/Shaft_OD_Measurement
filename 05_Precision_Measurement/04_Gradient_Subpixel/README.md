# Gradient + Sub-pixel 정밀측정

## 1. 목적

기존의 기본 Edge 기반 측정에서 정밀도를 더욱 높이기 위해
Sobel Gradient를 이용하여 상·하 Edge의 위치를 보다 세밀하게 찾고,
Sub-pixel 보간을 적용하여 정밀 외경을 계산하였다.

## 2. 처리 과정

1. Gray 변환
2. Gaussian Blur
3. y방향 Sobel Gradient 계산
4. Gradient 절대값 계산
5. 중앙 영역 7개 x 위치 선정
6. 각 위치에서 상단/하단 Gradient peak 탐색
7. Sub-pixel 보간
8. 외경 계산
9. 7개 외경값의 Median / Mean / Std 계산

## 3. 대표값

최종 대표 외경은 중앙값(Median)을 사용하였다.

## 4. 의미

Gradient는 Edge 위치를 찾기 위한 기준으로 사용하였고,
Sub-pixel 보간을 통해 정수 Pixel보다 세밀한 Edge 위치를 계산하였다.

# Reflection Handling

표면 반사 및 내부 Edge 오선택 문제를 줄이기 위한 V3 Reflection 대응 단계이다.

주요 파일:
- `measurement_engine_EDGE_V3_REFLECTION.py`

주요 개선:
- 반사로 인한 잘못된 Edge 선택 억제
- 상·하 Edge 안정화
- 31-point 기반 측정
- Median / MAD
- Sub-pixel
- Line fitting

from fastapi import FastAPI, UploadFile, File, HTTPException
from pathlib import Path
from datetime import datetime
import subprocess
import sys
import shutil

DATABASE_DIR = Path(__file__).resolve().parent.parent / "database"
sys.path.insert(0, str(DATABASE_DIR))

from database import init_db, save_measurement

app = FastAPI(
    title="Shaft OD Measurement API",
    version="1.0"
)

init_db()

# ---------------------------------------------------------
# 경로
# ---------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent

MEASUREMENT_ENGINE = (
    BASE_DIR
    / "measurement"
    / "measurement_engine.py"
)

OUTPUT_FILE = (
    BASE_DIR
    / "measurement"
    / "output"
    / "measurement_result.txt"
)

UPLOAD_DIR = (
    BASE_DIR
    / "backend"
    / "uploads"
)

UPLOAD_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ---------------------------------------------------------
# Health Check
# ---------------------------------------------------------

@app.get("/health")
def health():

    return {
        "status": "ok",
        "service": "shaft_od_measurement"
    }


# ---------------------------------------------------------
# Shaft Measurement
# ---------------------------------------------------------

@app.post("/measure")
async def measure(
    file: UploadFile = File(...)
):

    try:

        # 업로드 이미지 저장
        image_path = (
            UPLOAD_DIR
            / file.filename
        )

        with open(
            image_path,
            "wb"
        ) as buffer:

            shutil.copyfileobj(
                file.file,
                buffer
            )


        # 기존 측정 엔진 실행
        process = subprocess.run(
            [
                sys.executable,
                str(MEASUREMENT_ENGINE),
                str(image_path)
            ],
            capture_output=True,
            text=True
        )


        # 측정 엔진 실행 오류
        if process.returncode != 0:

            raise HTTPException(
                status_code=500,
                detail=process.stderr
            )        



        # 결과 파일 확인
        if not OUTPUT_FILE.exists():

            raise HTTPException(
                status_code=500,
                detail="Measurement result file not found"
            )


                # 결과 TXT 읽기
        result_text = OUTPUT_FILE.read_text(
            encoding="utf-8"
        )

        # 결과 TXT를 항목별로 분리
        result_data = {}

        for line in result_text.splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                result_data[key.strip()] = value.strip()

        confidence = float(
            result_data["YOLO confidence"]
        )

        measured_pixel = float(
            result_data["Measured pixel"]
        )

        measured_mm = float(
            result_data["Measured mm"]
        )

        # 규격값 분리
        spec_text = (
            result_data["Specification"]
            .replace("mm", "")
            .strip()
        )

        spec_lower_text, spec_upper_text = spec_text.split("~")

        spec_lower = float(spec_lower_text.strip())
        spec_upper = float(spec_upper_text.strip())

        result = result_data["Result"]

        # SQLite 저장
        save_measurement(
            measured_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            filename=file.filename,
            confidence=confidence,
            measured_pixel=measured_pixel,
            measured_mm=measured_mm,
            spec_lower=spec_lower,
            spec_upper=spec_upper,
            result=result
        )

        return {
            "status": "success",
            "filename": file.filename,
            "measurement_result": result_text
        }

    except HTTPException:
        raise

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
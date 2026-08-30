import sqlite3
from pathlib import Path


# ============================================================
# 1. 데이터베이스 파일 경로
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

DB_PATH = BASE_DIR / "measurement.db"


# ============================================================
# 2. 데이터베이스 초기화
# ============================================================

def init_db():

    conn = sqlite3.connect(DB_PATH)

    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS measurements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            measured_at TEXT NOT NULL,
            filename TEXT NOT NULL,
            confidence REAL,
            measured_pixel REAL,
            measured_mm REAL,
            spec_lower REAL,
            spec_upper REAL,
            result TEXT
        )
        """
    )

    conn.commit()
    conn.close()

def save_measurement(
    measured_at,
    filename,
    confidence,
    measured_pixel,
    measured_mm,
    spec_lower,
    spec_upper,
    result
):

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO measurements (
            measured_at,
            filename,
            confidence,
            measured_pixel,
            measured_mm,
            spec_lower,
            spec_upper,
            result
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            measured_at,
            filename,
            confidence,
            measured_pixel,
            measured_mm,
            spec_lower,
            spec_upper,
            result
        )
    )

    conn.commit()
    conn.close()
# ============================================================
# 3. 실행
# ============================================================

if __name__ == "__main__":

    init_db()

    print("SQLite 데이터베이스 생성 완료")
    print("DB 경로 :", DB_PATH)
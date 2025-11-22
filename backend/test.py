# scripts/test_db.py
from timetable.models import SessionLocal, Rooms  # adjust if class name is different

def main():
    db = SessionLocal()
    try:
        count = db.query(Rooms).count()
        print("Rooms count:", count)
    finally:
        db.close()

if __name__ == "__main__":
    main()

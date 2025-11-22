# db_init.py
"""
Initializes the MySQL database 'college' and all required tables
for the timetable solver.

- Creates DB if not exists
- Creates tables if not exist (departments, rooms, faculty, batches,
  subjects, subject_offerings, faculty_assignments, timeslots,
  faculty_unavailability, fixed_slots, config)
- Creates indexes
- Inserts sample rooms if 'rooms' is empty

Call init_database() once at backend startup.
"""

import os
import pymysql # pyright: ignore[reportMissingModuleSource]


MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "binatlos")
MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_DB = os.getenv("MYSQL_DB", "college")


def get_connection(include_db: bool = False):
    if include_db:
        return pymysql.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            port=MYSQL_PORT,
            database=MYSQL_DB,
            autocommit=True,
        )
    else:
        return pymysql.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            port=MYSQL_PORT,
            autocommit=True,
        )


def ensure_database_exists():
    conn = get_connection(include_db=False)
    try:
        with conn.cursor() as cur:
            cur.execute(f"CREATE DATABASE IF NOT EXISTS `{MYSQL_DB}`")
            print(f"[DB INIT] Ensured database '{MYSQL_DB}' exists.")
    finally:
        conn.close()


def ensure_tables_exist():
    conn = get_connection(include_db=True)
    try:
        with conn.cursor() as cur:
            # Departments
            cur.execute("""
            CREATE TABLE IF NOT EXISTS departments (
              id INT AUTO_INCREMENT PRIMARY KEY,
              code VARCHAR(16) NOT NULL UNIQUE,
              name VARCHAR(128) NOT NULL
            );
            """)

            # Rooms
            cur.execute("""
            CREATE TABLE IF NOT EXISTS rooms (
              id INT AUTO_INCREMENT PRIMARY KEY,
              code VARCHAR(32) NOT NULL UNIQUE,
              capacity INT NOT NULL,
              type ENUM('theory','lab') NOT NULL,
              location VARCHAR(128)
            );
            """)

            # Faculty
            cur.execute("""
            CREATE TABLE IF NOT EXISTS faculty (
              id INT AUTO_INCREMENT PRIMARY KEY,
              name VARCHAR(150) NOT NULL,
              email VARCHAR(150) UNIQUE,
              department_id INT,
              max_classes_per_day INT DEFAULT 4,
              subjects_can_teach JSON,
              active TINYINT(1) DEFAULT 1,
              FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE SET NULL
            );
            """)

            # Batches
            cur.execute("""
            CREATE TABLE IF NOT EXISTS batches (
              id INT AUTO_INCREMENT PRIMARY KEY,
              name VARCHAR(80) NOT NULL,
              department_id INT,
              semester INT NOT NULL,
              shift ENUM('day','evening') DEFAULT 'day',
              size INT NOT NULL,
              FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE SET NULL
            );
            """)

            # Subjects
            cur.execute("""
            CREATE TABLE IF NOT EXISTS subjects (
              code VARCHAR(32) PRIMARY KEY,
              title VARCHAR(200) NOT NULL,
              department_id INT,
              type ENUM('theory','lab') NOT NULL,
              classes_per_week INT NOT NULL DEFAULT 3,
              duration_slots INT NOT NULL DEFAULT 1,
              FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE SET NULL
            );
            """)

            # Subject offerings
            cur.execute("""
            CREATE TABLE IF NOT EXISTS subject_offerings (
              id INT AUTO_INCREMENT PRIMARY KEY,
              subject_code VARCHAR(32) NOT NULL,
              batch_id INT NOT NULL,
              semester INT NOT NULL,
              elective TINYINT(1) DEFAULT 0,
              FOREIGN KEY (subject_code) REFERENCES subjects(code) ON DELETE CASCADE,
              FOREIGN KEY (batch_id) REFERENCES batches(id) ON DELETE CASCADE
            );
            """)

            # Faculty assignments
            cur.execute("""
            CREATE TABLE IF NOT EXISTS faculty_assignments (
              id INT AUTO_INCREMENT PRIMARY KEY,
              subject_offering_id INT NOT NULL,
              faculty_id INT NOT NULL,
              preference_score DECIMAL(4,2) DEFAULT NULL,
              FOREIGN KEY (subject_offering_id) REFERENCES subject_offerings(id) ON DELETE CASCADE,
              FOREIGN KEY (faculty_id) REFERENCES faculty(id) ON DELETE CASCADE
            );
            """)

            # Timeslots
            cur.execute("""
            CREATE TABLE IF NOT EXISTS timeslots (
              id INT AUTO_INCREMENT PRIMARY KEY,
              day TINYINT NOT NULL,
              slot TINYINT NOT NULL,
              start_time TIME NOT NULL,
              end_time TIME NOT NULL,
              UNIQUE KEY (day, slot)
            );
            """)

            # Faculty unavailability
            cur.execute("""
            CREATE TABLE IF NOT EXISTS faculty_unavailability (
              id INT AUTO_INCREMENT PRIMARY KEY,
              faculty_id INT NOT NULL,
              date DATE DEFAULT NULL,
              day TINYINT DEFAULT NULL,
              slot TINYINT DEFAULT NULL,
              reason VARCHAR(200),
              FOREIGN KEY (faculty_id) REFERENCES faculty(id) ON DELETE CASCADE
              -- MySQL historically ignores CHECK constraints, so we skip it
            );
            """)

            # Fixed slots
            cur.execute("""
            CREATE TABLE IF NOT EXISTS fixed_slots (
              id INT AUTO_INCREMENT PRIMARY KEY,
              subject_offering_id INT NOT NULL,
              day TINYINT NOT NULL,
              slot TINYINT NOT NULL,
              room_id INT DEFAULT NULL,
              reason VARCHAR(200),
              FOREIGN KEY (subject_offering_id) REFERENCES subject_offerings(id) ON DELETE CASCADE,
              FOREIGN KEY (room_id) REFERENCES rooms(id) ON DELETE SET NULL,
              UNIQUE KEY (subject_offering_id, day, slot)
            );
            """)

            # Config
            cur.execute("""
            CREATE TABLE IF NOT EXISTS config (
              `key` VARCHAR(100) PRIMARY KEY,
              `value` TEXT
            );
            """)

            # Indexes
#            cur.execute("""
#           CREATE INDEX IF NOT EXISTS idx_faculty_dept ON faculty(department_id);
#            """)
#            cur.execute("""
#            CREATE INDEX IF NOT EXISTS idx_batches_dept ON batches(department_id);
#            """)
#            cur.execute("""
#            CREATE INDEX IF NOT EXISTS idx_offerings_batch ON subject_offerings(batch_id);
#            """)
#            cur.execute("""
#           CREATE INDEX IF NOT EXISTS idx_timeslot_day_slot ON timeslots(day, slot);
#            """)
#
#            print("[DB INIT] Tables and indexes ensured.")
    finally:
        conn.close()

def init_database():
    """
    Call this once at backend startup.
    """
    ensure_database_exists()
    ensure_tables_exist()
    print("[DB INIT] Database initialization complete.")

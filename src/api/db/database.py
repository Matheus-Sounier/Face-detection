import os
import oracledb
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    return oracledb.connect(
        user=os.getenv("USER"),
        password=os.getenv("ORACLE_PWD"),
        host=os.getenv("ORACLE_HOSTNAME"),
        port=os.getenv("PORT_DB"),
        service_name=os.getenv("SERVICE_NAME"),
    )

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            CREATE TABLE DETECTED_PEOPLE (
                id            NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                name          VARCHAR2(255) NOT NULL,
                employee_id   VARCHAR2(50) NOT NULL UNIQUE,
                access_level  VARCHAR2(50) NOT NULL,
                embedding     VECTOR(512, FLOAT32) NOT NULL,
                enrolled_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        print("Table DETECTED_PEOPLE created.")
    except oracledb.DatabaseError as e:
        error, = e.args
        if error.code == 955:  # ORA-00955
            print("Table DETECTED_PEOPLE already exists, continuing...")
        else:
            raise
    finally:
        cursor.close()
        conn.close()

def logs():
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            CREATE TABLE ACCESS_LOGS (
                id           NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                person_id    NUMBER REFERENCES DETECTED_PEOPLE(id),
                employee_id  VARCHAR2(50),
                recognized   NUMBER(1) NOT NULL,
                access_granted NUMBER(1) NOT NULL,
                attempted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        print("Table ACCESS_LOGS's created.")
    except oracledb.DatabaseError as e:
        error, = e.args
        if error.code == 955:  # ORA-00955
            print("Table simulated_calendar already exists, continuing...")
        else:
            raise
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    init_db()
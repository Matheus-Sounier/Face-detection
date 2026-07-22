import os
import oracledb
import array
from dotenv import load_dotenv

load_dotenv()

MATCH_THRESHOLD = 0.45

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
                id              NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                name            VARCHAR2(255) NOT NULL,
                employee_id     VARCHAR2(50) NOT NULL UNIQUE,
                access_level    VARCHAR2(50) NOT NULL,
                enrolled_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            CREATE TABLE PERSON_FACES (
                id           NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                person_id    NUMBER NOT NULL REFERENCES DETECTED_PEOPLE(id) ON DELETE CASCADE,
                embedding    VECTOR(512, FLOAT32) NOT NULL,
                face_image   BLOB,
                enrolled_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        print("Table PERSON_FACES created.")
    except oracledb.DatabaseError as e:
        error, = e.args
        if error.code == 955:
            print("Table PERSON_FACES already exists, continuing...")
        else:
            raise
    finally:
        cursor.close()
        conn.close()

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            CREATE TABLE ACCESS_LOGS (
                id             NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                person_id      NUMBER REFERENCES DETECTED_PEOPLE(id),
                employee_id    VARCHAR2(50),
                recognized     NUMBER(1) NOT NULL,
                access_granted NUMBER(1) NOT NULL,
                face_detected  BLOB,
                attempted_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        print("Table ACCESS_LOGS's created.")
    except oracledb.DatabaseError as e:
        error, = e.args
        if error.code == 955:  # ORA-00955
            print("Table ACCESS_LOGS already exists, continuing...")
        else:
            raise
    finally:
        cursor.close()
        conn.close()
        
def insert_person(name: str, employee_id: str, access_level: str) -> int:
    """
    Inserts a new person with their facial embedding.
    Returns the generated id. Raises oracledb.IntegrityError if employee_id already exists.
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        result_id = cursor.var(int)
        cursor.execute(
            '''
            INSERT INTO DETECTED_PEOPLE (name, employee_id, access_level)
            VALUES (:name, :employee_id, :access_level)
            RETURNING id INTO :id
            ''',
            {
                "name": name,
                "employee_id": employee_id,
                "access_level": access_level,
                "id": result_id,
            },
        )
        conn.commit()
        return result_id.getvalue()[0]
    finally:
        cursor.close()
        conn.close()

def find_closest_match(embedding):
    """
    Search for the person whose embedding is closest to the one provided.
    Returns a dict with the person's data + distance, or None if 
    no one in the database falls within the MATCH_THRESHOLD
    """
    conn = get_connection()
    cursor = conn.cursor()

    vector_value = array.array("f", embedding.tolist())

    try:
        cursor.execute(
            '''
            SELECT p.id, p.name, p.employee_id, p.access_level,
                   MIN(VECTOR_DISTANCE(f.embedding, :embedding, COSINE)) AS distance
            FROM PERSON_FACES f
            JOIN DETECTED_PEOPLE p ON p.id = f.person_id
            GROUP BY p.id, p.name, p.employee_id, p.access_level
            ORDER BY distance ASC
            FETCH FIRST 1 ROW ONLY
            ''',
            {"embedding": vector_value},
        )
        row = cursor.fetchone()

        if row is None:
            return None

        person_id, name, employee_id, access_level, distance = row

        if distance > MATCH_THRESHOLD:
            return None

        return {
            "id": person_id,
            "name": name,
            "employee_id": employee_id,
            "access_level": access_level,
            "distance": distance,
        }
    finally:
        cursor.close()
        conn.close()

def log_access(person_id, employee_id, recognized: bool, access_granted: bool, face_image_bytes: bytes = None):
    """no recognizable face in the submitted cutout"""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            '''
            INSERT INTO ACCESS_LOGS (person_id, employee_id, recognized, access_granted, face_detected)
            VALUES (:person_id, :employee_id, :recognized, :access_granted, :face_detected)
            ''',
            {
                "person_id": person_id,
                "employee_id": employee_id,
                "recognized": 1 if recognized else 0,
                "access_granted": 1 if access_granted else 0,
                "face_detected": face_image_bytes,
            },
        )
        conn.commit()
    finally:
        cursor.close()
        conn.close()

def insert_face(person_id: int, embedding, face_image_bytes: bytes) -> int:
    """
    Adds one face embedding + image.
    called multiple times for the same person_id.
    """
    conn = get_connection()
    cursor = conn.cursor()

    vector_value = array.array("f", embedding.tolist())

    try:
        result_id = cursor.var(int)
        cursor.execute(
            '''
            INSERT INTO PERSON_FACES (person_id, embedding, face_image)
            VALUES (:person_id, :embedding, :face_image)
            RETURNING id INTO :id
            ''',
            {
                "person_id": person_id,
                "embedding": vector_value,
                "face_image": face_image_bytes,
                "id": result_id,
            },
        )
        conn.commit()
        return result_id.getvalue()[0]
    finally:
        cursor.close()
        conn.close()
        
if __name__ == "__main__":
    init_db()
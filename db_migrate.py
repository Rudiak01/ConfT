from sqlalchemy import text
from api.models import engine

with engine.connect() as conn:
    queries = [
        "ALTER TABLE nodes ADD COLUMN stp_mode VARCHAR(50)",
        "ALTER TABLE nodes ADD COLUMN stp_root_vlan VARCHAR(50)",
        "ALTER TABLE nodes ADD COLUMN routes_json TEXT"
    ]
    for q in queries:
        try:
            conn.execute(text(q))
            print(f"Executed: {q}")
        except Exception as e:
            print(f"Skipped {q}: {e}")
    conn.commit()

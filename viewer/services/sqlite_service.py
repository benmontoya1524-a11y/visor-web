import sqlite3
from typing import Any, Dict, List, Tuple

def get_schema(db_path: str) -> Dict[str, List[str]]:
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [r[0] for r in cur.fetchall()]
        schema: Dict[str, List[str]] = {}
        for tbl in tables:
            cur.execute(f"PRAGMA table_info('{tbl}')")
            cols = [c[1] for c in cur.fetchall()]
            schema[tbl] = cols
        return schema
    finally:
        conn.close()

def run_select(
    db_path: str,
    table: str,
    cols: List[str],
    filter_text: str | None = None,
    limit: int = 500,
) -> Tuple[List[str], List[Tuple[Any, ...]]]:
    if not cols:
        return [], []

    # Identificadores entre comillas dobles
    escaped_cols = [f'"{c}"' for c in cols]
    query = f'SELECT {", ".join(escaped_cols)} FROM "{table}"'
    params: List[Any] = []

    if filter_text:
        # LIKE contra columnas seleccionadas (como texto)
        likes = [f'CAST("{c}" AS TEXT) LIKE ?' for c in cols]
        query += " WHERE " + " OR ".join(likes)
        params = [f"%{filter_text}%" for _ in cols]

    query += f" LIMIT {int(limit)}"

    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute(query, params)
        rows = cur.fetchall()
        return cols, rows
    finally:
        conn.close()

from __future__ import annotations

import argparse
import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv


TABLES: list[tuple[str, str]] = [
    # (dataset_folder, raw_table_name)
    ("sales_order_headers", "sales_order_headers"),
    ("sales_order_items", "sales_order_items"),
    ("sales_order_schedule_lines", "sales_order_schedule_lines"),
    ("outbound_delivery_headers", "outbound_delivery_headers"),
    ("outbound_delivery_items", "outbound_delivery_items"),
    ("billing_document_headers", "billing_document_headers"),
    ("billing_document_items", "billing_document_items"),
    ("billing_document_cancellations", "billing_document_cancellations"),
    ("journal_entry_items_accounts_receivable", "journal_entry_items_accounts_receivable"),
    ("payments_accounts_receivable", "payments_accounts_receivable"),
    ("business_partners", "business_partners"),
    ("business_partner_addresses", "business_partner_addresses"),
    ("customer_company_assignments", "customer_company_assignments"),
    ("customer_sales_area_assignments", "customer_sales_area_assignments"),
    ("products", "products"),
    ("product_descriptions", "product_descriptions"),
    ("plants", "plants"),
    ("product_plants", "product_plants"),
    ("product_storage_locations", "product_storage_locations"),
]


def default_dataset_dir() -> Path:
    # repo_root/dataset/sap-order-to-cash-dataset/sap-o2c-data
    repo_root = Path(__file__).resolve().parents[2]
    return repo_root / "dataset" / "sap-order-to-cash-dataset" / "sap-o2c-data"


def to_psycopg_dsn(database_url: str) -> str:
    # SQLAlchemy uses dialect+driver; psycopg wants plain postgresql://
    if database_url.startswith("postgresql+psycopg://"):
        return "postgresql://" + database_url.removeprefix("postgresql+psycopg://")
    if database_url.startswith("postgresql://") or database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql://")
    return database_url


def iter_jsonl_files(folder: Path) -> list[Path]:
    return sorted(folder.glob("*.jsonl"))


def copy_jsonl_to_table(cur: psycopg.Cursor, *, table: str, files: list[Path]) -> int:
    inserted = 0
    copy_sql = f"COPY raw.{table} (payload) FROM STDIN"

    with cur.copy(copy_sql) as copy:
        for fp in files:
            with fp.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    copy.write(line + "\n")
                    inserted += 1
    return inserted


def _run_sql_script(cur: psycopg.Cursor, sql_text: str) -> None:
    # Simple splitter suitable for our init script (no functions/procedures).
    # Strips full-line `--` comments and executes each statement separately.
    lines: list[str] = []
    for line in sql_text.splitlines():
        if line.lstrip().startswith("--"):
            continue
        lines.append(line)
    cleaned = "\n".join(lines)
    for stmt in cleaned.split(";"):
        stmt = stmt.strip()
        if stmt:
            cur.execute(stmt)


def ensure_db_initialized(conn: psycopg.Connection, *, init_db: bool) -> None:
    """
    Ensure `raw.*` and `graph.*` schemas/tables exist.

    RCA for common failure:
    - If `raw.sales_order_headers` doesn't exist, you likely didn't run `init_db.sql`
      against THIS database/branch/endpoint.
    """
    with conn.cursor() as cur:
        missing: list[str] = []
        for _folder, table in TABLES:
            cur.execute("SELECT to_regclass(%s) AS t;", (f"raw.{table}",))
            exists = cur.fetchone()[0]  # type: ignore[index]
            if exists is None:
                missing.append(f"raw.{table}")

        if not missing:
            return

        if not init_db:
            raise SystemExit(
                "raw.* tables are missing. "
                "Run Backend/scripts/init_db.sql on the same DATABASE_URL first.\n"
                f"Missing: {', '.join(missing[:5])}{' ...' if len(missing) > 5 else ''}"
            )

        init_path = Path(__file__).resolve().parent / "init_db.sql"
        if not init_path.exists():
            raise SystemExit(f"init_db.sql not found at {init_path}")

        print(f"[init] Missing {len(missing)} raw tables. Running init_db.sql ...")
        _run_sql_script(cur, init_path.read_text(encoding="utf-8"))
        conn.commit()

        cur.execute("SELECT to_regclass('raw.sales_order_headers') AS t;")
        exists_after = cur.fetchone()[0]  # type: ignore[index]
        if exists_after is None:
            raise SystemExit(
                "Failed to create raw.* tables. "
                "Double-check DATABASE_URL points to the Neon database/branch where you want the tables."
            )


def main() -> None:
    backend_dir = Path(__file__).resolve().parents[1]
    env_path = backend_dir / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    else:
        # Fall back to current working directory .env (if present).
        load_dotenv()

    parser = argparse.ArgumentParser(description="Ingest SAP O2C JSONL dataset into Postgres raw.* tables.")
    parser.add_argument(
        "--dataset-dir",
        type=Path,
        default=default_dataset_dir(),
        help="Path to sap-o2c-data folder (default: repo/dataset/.../sap-o2c-data).",
    )
    parser.add_argument(
        "--only",
        nargs="*",
        default=None,
        help="Optional list of dataset folders to ingest (e.g., sales_order_headers billing_document_headers).",
    )
    parser.add_argument(
        "--truncate",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Truncate raw tables before load (default: true).",
    )
    parser.add_argument(
        "--init-db",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Create schemas/tables by running scripts/init_db.sql if missing (default: true).",
    )

    args = parser.parse_args()

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise SystemExit(
            "DATABASE_URL is not set. Create Backend/.env (recommended) or set env var DATABASE_URL."
        )

    dsn = to_psycopg_dsn(database_url)
    dataset_dir: Path = args.dataset_dir
    if not dataset_dir.exists():
        raise SystemExit(f"Dataset directory not found: {dataset_dir}")

    only = set(args.only) if args.only else None

    print(f"Connecting to DB via DATABASE_URL (psycopg dsn).")
    print(f"Dataset dir: {dataset_dir}")
    print(f"Truncate before load: {args.truncate}")
    if only:
        print(f"Only ingesting folders: {sorted(only)}")

    with psycopg.connect(dsn) as conn:
        conn.execute("SET statement_timeout TO '0'")  # no timeout during bulk load
        ensure_db_initialized(conn, init_db=args.init_db)

        with conn.cursor() as cur:
            for folder_name, table_name in TABLES:
                if only and folder_name not in only:
                    continue

                folder = dataset_dir / folder_name
                if not folder.exists():
                    print(f"[skip] {folder_name} (folder not found)")
                    continue

                files = iter_jsonl_files(folder)
                if not files:
                    print(f"[skip] {folder_name} (no .jsonl files)")
                    continue

                if args.truncate:
                    cur.execute(f"TRUNCATE TABLE raw.{table_name} RESTART IDENTITY;")

                inserted = copy_jsonl_to_table(cur, table=table_name, files=files)
                conn.commit()

                cur.execute(f"SELECT COUNT(*) FROM raw.{table_name};")
                count = cur.fetchone()[0]  # type: ignore[index]

                print(f"[ok] {table_name}: inserted={inserted} rows_in_table={count}")


if __name__ == "__main__":
    main()


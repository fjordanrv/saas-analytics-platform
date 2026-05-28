"""
Ingesta de datos Billing (subscriptions y payments) a la capa Bronze de DuckDB.

Lee desde data/raw/, valida esquema, ejecuta quality checks,
agrega metadata Bronze y escribe en DuckDB.

Uso:
    python -m src.ingestion.billing_ingestion
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List

import pandas as pd
from rich.console import Console
from rich.table import Table

from src.quality.data_quality_checks import DataQualityChecker, QualityReport, Severity
from src.utils.database import DatabaseConnection
from src.utils.logger import get_logger

PROJECT_ROOT = Path(__file__).resolve().parents[2]
console = Console()


# ── Dataclass de resultado ────────────────────────────────────────────────────

@dataclass
class IngestionResult:
    """Resultado de una ejecución de ingesta para una tabla."""
    table:             str
    source_file:       str
    rows_read:         int
    rows_ingested:     int
    quality_score:     float
    critical_failures: int
    batch_id:          str
    ingested_at:       str
    duration_seconds:  float


# ── Clase principal ───────────────────────────────────────────────────────────

class BillingIngestion:
    """Ingesta de las tablas Billing (subscriptions y payments) a Bronze.

    Flujo por tabla:
        read_source → validate_schema → run_quality_checks
        → add_bronze_metadata → write_bronze

    Si hay critical_failures en los quality checks, la ingesta se cancela
    y se lanza ValueError para que Airflow marque la tarea como fallida.
    """

    VALID_SUB_STATUSES     = ["active", "cancelled", "upgraded", "downgraded"]
    VALID_PAYMENT_STATUSES = ["paid", "failed", "refunded"]
    VALID_PAYMENT_METHODS  = ["credit_card", "bank_transfer", "paypal"]

    SUBSCRIPTIONS_REQUIRED = [
        "sub_id", "customer_id", "plan", "mrr", "start_date", "status",
    ]
    PAYMENTS_REQUIRED = [
        "payment_id", "sub_id", "customer_id",
        "amount", "payment_date", "status", "payment_method",
    ]

    def __init__(self, db: DatabaseConnection) -> None:
        self.db         = db
        self.source_dir = PROJECT_ROOT / "data" / "raw"
        self.log        = get_logger(__name__)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def read_source(self, filename: str) -> pd.DataFrame:
        """Lee un CSV de data/raw/ y loggea las filas leídas.

        Args:
            filename: Nombre del archivo CSV (solo el nombre, no la ruta).

        Returns:
            DataFrame con el contenido del CSV.

        Raises:
            FileNotFoundError: Si el archivo no existe en source_dir.
        """
        path = self.source_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {path}")

        df = pd.read_csv(path)
        self.log.info(f"Leído {filename}: {len(df):,} filas")
        return df

    def validate_schema(self, df: pd.DataFrame, required_columns: List[str]) -> None:
        """Verifica que el DataFrame tenga todas las columnas requeridas.

        Args:
            df:               DataFrame a validar.
            required_columns: Columnas que deben estar presentes.

        Raises:
            ValueError: Con la lista de columnas faltantes.
        """
        missing = [c for c in required_columns if c not in df.columns]
        if missing:
            raise ValueError(f"Columnas faltantes en el schema: {missing}")
        self.log.info(f"Schema válido — {len(required_columns)} columnas requeridas presentes")

    def run_quality_checks(
        self, df: pd.DataFrame, table_name: str, is_subscriptions: bool = True
    ) -> QualityReport:
        """Ejecuta el conjunto de quality checks para subscriptions o payments.

        Args:
            df:                DataFrame a evaluar.
            table_name:        Nombre de la tabla (usado en el reporte).
            is_subscriptions:  True para subscriptions, False para payments.

        Returns:
            QualityReport con todos los checks ejecutados.
        """
        checker = DataQualityChecker(df, table_name)

        if is_subscriptions:
            checker = (
                checker
                .check_nulls(["sub_id", "customer_id", "plan", "mrr"], Severity.CRITICAL)
                .check_duplicates(["sub_id"], Severity.CRITICAL)
                .check_referential_integrity("status", self.VALID_SUB_STATUSES, Severity.WARNING)
                .check_value_ranges("mrr", 0, 10000, Severity.WARNING)
                .check_date_consistency("start_date", "end_date", Severity.WARNING)
            )
        else:
            checker = (
                checker
                .check_nulls(["payment_id", "sub_id", "amount"], Severity.CRITICAL)
                .check_duplicates(["payment_id"], Severity.CRITICAL)
                .check_referential_integrity("status", self.VALID_PAYMENT_STATUSES, Severity.WARNING)
                .check_referential_integrity("payment_method", self.VALID_PAYMENT_METHODS, Severity.WARNING)
                .check_value_ranges("amount", 0, 10000, Severity.WARNING)
            )

        report = checker.generate_report()
        self.log.info(
            f"Quality checks [{table_name}]: score={report.quality_score:.1f}%, "
            f"{report.critical_failures} critical failure(s)"
        )
        return report

    def add_bronze_metadata(
        self, df: pd.DataFrame, source_file: str, batch_id: str
    ) -> pd.DataFrame:
        """Agrega 4 columnas de metadata Bronze al DataFrame.

        Args:
            df:          DataFrame original.
            source_file: Nombre del archivo CSV de origen.
            batch_id:    Identificador único del batch de ingesta.

        Returns:
            Copia del DataFrame con columnas _ingested_at, _source_file,
            _batch_id y _layer añadidas.
        """
        df = df.copy()
        now = datetime.now().isoformat(timespec="seconds")
        df["_ingested_at"] = now
        df["_source_file"] = source_file
        df["_batch_id"]    = batch_id
        df["_layer"]       = "bronze"
        return df

    def write_bronze(self, df: pd.DataFrame, table_name: str) -> None:
        """Crea (o reemplaza) la tabla Bronze en DuckDB con el contenido del DataFrame.

        Args:
            df:         DataFrame con metadata Bronze incluida.
            table_name: Nombre completo de la tabla (ej. 'bronze.subscriptions').
        """
        self.db.create_schema("bronze")
        self.db.write_dataframe(df, table_name)
        self.log.info(f"Escrito en Bronze: {table_name} ({len(df):,} filas)")

    # ── Métodos de ingesta ────────────────────────────────────────────────────

    def ingest_subscriptions(self) -> IngestionResult:
        """Ingesta completa de billing_subscriptions.csv → bronze.subscriptions.

        Returns:
            IngestionResult con métricas de la ejecución.

        Raises:
            FileNotFoundError: Si el CSV no existe.
            ValueError: Si hay critical quality failures o columnas faltantes.
        """
        start    = time.time()
        batch_id = str(uuid.uuid4())[:8]

        df = self.read_source("billing_subscriptions.csv")
        rows_read = len(df)

        self.validate_schema(df, self.SUBSCRIPTIONS_REQUIRED)
        report = self.run_quality_checks(df, "bronze.subscriptions", is_subscriptions=True)

        if report.critical_failures > 0:
            self.log.error(
                f"Ingesta cancelada — {report.critical_failures} critical failure(s) "
                f"en bronze.subscriptions"
            )
            raise ValueError(
                f"Critical quality failures en subscriptions: {report.critical_failures}"
            )

        df = self.add_bronze_metadata(df, "billing_subscriptions.csv", batch_id)
        self.write_bronze(df, "bronze.subscriptions")

        return IngestionResult(
            table             = "bronze.subscriptions",
            source_file       = "billing_subscriptions.csv",
            rows_read         = rows_read,
            rows_ingested     = len(df),
            quality_score     = report.quality_score,
            critical_failures = report.critical_failures,
            batch_id          = batch_id,
            ingested_at       = datetime.now().isoformat(timespec="seconds"),
            duration_seconds  = round(time.time() - start, 3),
        )

    def ingest_payments(self) -> IngestionResult:
        """Ingesta completa de billing_payments.csv → bronze.payments.

        Returns:
            IngestionResult con métricas de la ejecución.

        Raises:
            FileNotFoundError: Si el CSV no existe.
            ValueError: Si hay critical quality failures o columnas faltantes.
        """
        start    = time.time()
        batch_id = str(uuid.uuid4())[:8]

        df = self.read_source("billing_payments.csv")
        rows_read = len(df)

        self.validate_schema(df, self.PAYMENTS_REQUIRED)
        report = self.run_quality_checks(df, "bronze.payments", is_subscriptions=False)

        if report.critical_failures > 0:
            self.log.error(
                f"Ingesta cancelada — {report.critical_failures} critical failure(s) "
                f"en bronze.payments"
            )
            raise ValueError(
                f"Critical quality failures en payments: {report.critical_failures}"
            )

        df = self.add_bronze_metadata(df, "billing_payments.csv", batch_id)
        self.write_bronze(df, "bronze.payments")

        return IngestionResult(
            table             = "bronze.payments",
            source_file       = "billing_payments.csv",
            rows_read         = rows_read,
            rows_ingested     = len(df),
            quality_score     = report.quality_score,
            critical_failures = report.critical_failures,
            batch_id          = batch_id,
            ingested_at       = datetime.now().isoformat(timespec="seconds"),
            duration_seconds  = round(time.time() - start, 3),
        )

    def run(self) -> List[IngestionResult]:
        """Ejecuta la ingesta completa de Billing: subscriptions → payments.

        Returns:
            Lista de IngestionResult para cada tabla procesada.

        Raises:
            ValueError: Si alguna tabla tiene critical quality failures.
        """
        self.log.info("=== Iniciando ingesta Billing ===")
        results: List[IngestionResult] = []

        results.append(self.ingest_subscriptions())
        results.append(self.ingest_payments())

        tbl = Table(title="Billing Ingestion — Resumen", show_lines=True)
        tbl.add_column("Tabla",         style="cyan",  no_wrap=True)
        tbl.add_column("Filas",         style="green", justify="right")
        tbl.add_column("Quality Score", justify="right")
        tbl.add_column("Duration",      style="dim",   justify="right")

        for r in results:
            score_color = "green" if r.quality_score >= 80 else "yellow"
            tbl.add_row(
                r.table,
                f"{r.rows_ingested:,}",
                f"[{score_color}]{r.quality_score:.1f}%[/{score_color}]",
                f"{r.duration_seconds:.3f}s",
            )

        console.print(tbl)
        self.log.info("=== Ingesta Billing completada ===")
        return results


# ── Entrypoint ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    db = DatabaseConnection.get_instance()
    db.connect()
    ingestion = BillingIngestion(db)
    results = ingestion.run()
    db.close()

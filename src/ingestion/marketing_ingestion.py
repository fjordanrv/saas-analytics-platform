"""
Ingesta de Marketing Leads a la capa Bronze de DuckDB.

Uso:
    python -m src.ingestion.marketing_ingestion
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


class MarketingIngestion:
    """Ingesta de marketing_leads.csv a bronze.marketing_leads."""

    VALID_SOURCES  = ["organic", "paid_search", "referral", "email", "social"]
    VALID_CHANNELS = ["Blog", "Google", "Referral", "Newsletter",
                      "LinkedIn", "Facebook", "Twitter"]

    LEADS_REQUIRED = [
        "lead_id", "email", "source",
        "campaign", "channel", "lead_date", "converted",
    ]

    def __init__(self, db: DatabaseConnection) -> None:
        self.db         = db
        self.source_dir = PROJECT_ROOT / "data" / "raw"
        self.log        = get_logger(__name__)

    def read_source(self, filename: str) -> pd.DataFrame:
        """Lee un CSV de data/raw/.

        Raises:
            FileNotFoundError: Si el archivo no existe.
        """
        path = self.source_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {path}")
        df = pd.read_csv(path)
        self.log.info(f"Leído {filename}: {len(df):,} filas")
        return df

    def validate_schema(self, df: pd.DataFrame, required_columns: List[str]) -> None:
        """Verifica columnas requeridas.

        Raises:
            ValueError: Con la lista de columnas faltantes.
        """
        missing = [c for c in required_columns if c not in df.columns]
        if missing:
            raise ValueError(f"Columnas faltantes en el schema: {missing}")
        self.log.info(f"Schema válido — {len(required_columns)} columnas requeridas presentes")

    def run_quality_checks(self, df: pd.DataFrame, table_name: str) -> QualityReport:
        """Ejecuta quality checks para marketing_leads."""
        checker = (
            DataQualityChecker(df, table_name)
            .check_nulls(["lead_id", "email", "source", "converted"], Severity.CRITICAL)
            .check_duplicates(["lead_id"], Severity.CRITICAL)
            .check_referential_integrity("source", self.VALID_SOURCES, Severity.WARNING)
            .check_date_consistency("lead_date", "conversion_date", Severity.WARNING)
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
        """Agrega columnas de metadata Bronze."""
        df = df.copy()
        now = datetime.now().isoformat(timespec="seconds")
        df["_ingested_at"] = now
        df["_source_file"] = source_file
        df["_batch_id"]    = batch_id
        df["_layer"]       = "bronze"
        return df

    def write_bronze(self, df: pd.DataFrame, table_name: str) -> None:
        """Escribe el DataFrame en DuckDB como tabla Bronze."""
        self.db.create_schema("bronze")
        self.db.write_dataframe(df, table_name)
        self.log.info(f"Escrito en Bronze: {table_name} ({len(df):,} filas)")

    def ingest_leads(self) -> IngestionResult:
        """Ingesta completa de marketing_leads.csv → bronze.marketing_leads.

        Returns:
            IngestionResult con métricas de la ejecución.

        Raises:
            FileNotFoundError: Si el CSV no existe.
            ValueError: Si hay critical quality failures.
        """
        start    = time.time()
        batch_id = str(uuid.uuid4())[:8]

        df = self.read_source("marketing_leads.csv")
        rows_read = len(df)

        self.validate_schema(df, self.LEADS_REQUIRED)
        report = self.run_quality_checks(df, "bronze.marketing_leads")

        if report.critical_failures > 0:
            self.log.error(
                f"Ingesta cancelada — {report.critical_failures} critical failure(s) "
                f"en bronze.marketing_leads"
            )
            raise ValueError(f"Critical quality failures en marketing_leads: {report.critical_failures}")

        df = self.add_bronze_metadata(df, "marketing_leads.csv", batch_id)
        self.write_bronze(df, "bronze.marketing_leads")

        return IngestionResult(
            table             = "bronze.marketing_leads",
            source_file       = "marketing_leads.csv",
            rows_read         = rows_read,
            rows_ingested     = len(df),
            quality_score     = report.quality_score,
            critical_failures = report.critical_failures,
            batch_id          = batch_id,
            ingested_at       = datetime.now().isoformat(timespec="seconds"),
            duration_seconds  = round(time.time() - start, 3),
        )

    def run(self) -> List[IngestionResult]:
        """Ejecuta la ingesta completa de Marketing Leads."""
        self.log.info("=== Iniciando ingesta Marketing ===")
        results = [self.ingest_leads()]

        tbl = Table(title="Marketing Ingestion — Resumen", show_lines=True)
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
        self.log.info("=== Ingesta Marketing completada ===")
        return results


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    db = DatabaseConnection.get_instance()
    db.connect()
    ingestion = MarketingIngestion(db)
    results = ingestion.run()
    db.close()

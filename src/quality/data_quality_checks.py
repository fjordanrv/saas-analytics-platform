"""
Checks de calidad de datos para el pipeline Bronze de CloudMetrics.

Uso típico:
    report = (
        DataQualityChecker(df, "bronze.customers")
        .check_nulls(["email", "customer_id"], Severity.CRITICAL)
        .check_duplicates(["customer_id"], Severity.CRITICAL)
        .check_value_ranges("mrr", 0, 10000, Severity.WARNING)
        .generate_report()
    )
    report.print_summary()
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, List

import pandas as pd
from rich.console import Console
from rich.markup import escape
from rich.table import Table

from src.utils.logger import get_logger

log = get_logger(__name__)


# ── Enums y dataclasses ───────────────────────────────────────────────────────

class Severity(Enum):
    """Severidad de un check de calidad."""
    CRITICAL = "CRITICAL"
    WARNING  = "WARNING"
    INFO     = "INFO"


@dataclass
class QualityCheck:
    """Resultado de un único check de calidad sobre una tabla."""
    check_name:      str
    table:           str
    column:          str
    severity:        Severity
    passed:          bool
    records_checked: int
    records_failed:  int
    failure_rate:    float
    details:         str


@dataclass
class QualityReport:
    """Reporte agregado de todos los checks ejecutados sobre una tabla."""
    table:             str
    total_checks:      int
    passed:            int
    failed:            int
    critical_failures: int
    quality_score:     float
    checks:            List[QualityCheck]
    generated_at:      str

    def print_summary(self) -> None:
        """Imprime el reporte con rich: tabla de checks + score + resumen."""
        console = Console()

        _sev_color = {
            Severity.CRITICAL: "red",
            Severity.WARNING:  "yellow",
            Severity.INFO:     "blue",
        }

        tbl = Table(
            title=f"Quality Report — {self.table}",
            show_lines=True,
            title_style="bold white",
        )
        tbl.add_column("",         width=3,  no_wrap=True)
        tbl.add_column("Severity", width=10, style="bold")
        tbl.add_column("Check",    style="cyan")
        tbl.add_column("Details",  style="dim")

        for c in self.checks:
            icon  = "✅" if c.passed else "❌"
            color = _sev_color[c.severity]
            tbl.add_row(
                icon,
                f"[{color}]{c.severity.value}[/{color}]",
                escape(c.check_name),
                escape(c.details),
            )

        console.print(tbl)

        score_color = "green" if self.quality_score >= 80 else ("yellow" if self.quality_score >= 60 else "red")
        console.print(
            f"\n  Quality Score: [{score_color}][bold]{self.quality_score:.1f}%[/bold][/{score_color}]"
            f"  |  {self.passed}/{self.total_checks} checks passed"
            f"  |  [red]{self.critical_failures} critical failure(s)[/red]\n"
        )


# ── Checker principal ─────────────────────────────────────────────────────────

class DataQualityChecker:
    """Ejecuta checks de calidad sobre un DataFrame y genera un QualityReport.

    Soporta method chaining: cada check_* retorna self.

    Args:
        df:         DataFrame a evaluar (capa Bronze o raw).
        table_name: Nombre de la tabla, usado en logs y reportes.
    """

    def __init__(self, df: pd.DataFrame, table_name: str) -> None:
        self.df         = df
        self.table_name = table_name
        self.checks:    List[QualityCheck] = []

    def check_nulls(self, columns: List[str], severity: Severity) -> DataQualityChecker:
        """Crea un QualityCheck por columna contando valores nulos.

        Args:
            columns:  Columnas a verificar. Si una no existe se loggea un warning.
            severity: Severidad asignada a cada check que falle.

        Returns:
            self para method chaining.
        """
        for col in columns:
            if col not in self.df.columns:
                log.warning(f"check_nulls: columna '{col}' no existe en {self.table_name}")
                continue

            n_total = len(self.df)
            n_nulls = int(self.df[col].isna().sum())
            rate    = (n_nulls / n_total * 100) if n_total > 0 else 0.0

            self.checks.append(QualityCheck(
                check_name      = f"nulls:{col}",
                table           = self.table_name,
                column          = col,
                severity        = severity,
                passed          = n_nulls == 0,
                records_checked = n_total,
                records_failed  = n_nulls,
                failure_rate    = round(rate, 2),
                details         = f"{n_nulls} nulls encontrados ({rate:.1f}%)",
            ))
        return self

    def check_duplicates(self, key_columns: List[str], severity: Severity) -> DataQualityChecker:
        """Cuenta filas duplicadas por la combinación de key_columns.

        Args:
            key_columns: Columnas que forman la clave única esperada.
            severity:    Severidad asignada si hay duplicados.

        Returns:
            self para method chaining.
        """
        existing = [c for c in key_columns if c in self.df.columns]
        if not existing:
            log.warning(f"check_duplicates: ninguna key_column existe en {self.table_name}")
            return self

        n_total  = len(self.df)
        n_dups   = int(self.df.duplicated(subset=existing).sum())
        rate     = (n_dups / n_total * 100) if n_total > 0 else 0.0
        cols_str = ", ".join(existing)

        self.checks.append(QualityCheck(
            check_name      = f"duplicates:[{cols_str}]",
            table           = self.table_name,
            column          = cols_str,
            severity        = severity,
            passed          = n_dups == 0,
            records_checked = n_total,
            records_failed  = n_dups,
            failure_rate    = round(rate, 2),
            details         = f"{n_dups} duplicados en [{cols_str}]",
        ))
        return self

    def check_value_ranges(
        self, column: str, min_val: Any, max_val: Any, severity: Severity
    ) -> DataQualityChecker:
        """Verifica que los valores de una columna estén dentro de [min_val, max_val].

        Args:
            column:   Columna numérica a evaluar.
            min_val:  Límite inferior permitido (inclusive).
            max_val:  Límite superior permitido (inclusive).
            severity: Severidad asignada si hay valores fuera de rango.

        Returns:
            self para method chaining.
        """
        if column not in self.df.columns:
            log.warning(f"check_value_ranges: columna '{column}' no existe en {self.table_name}")
            return self

        n_total      = len(self.df)
        out_of_range = int(((self.df[column] < min_val) | (self.df[column] > max_val)).sum())
        rate         = (out_of_range / n_total * 100) if n_total > 0 else 0.0

        self.checks.append(QualityCheck(
            check_name      = f"range:{column}[{min_val},{max_val}]",
            table           = self.table_name,
            column          = column,
            severity        = severity,
            passed          = out_of_range == 0,
            records_checked = n_total,
            records_failed  = out_of_range,
            failure_rate    = round(rate, 2),
            details         = f"{out_of_range} valores fuera de [{min_val}, {max_val}]",
        ))
        return self

    def check_referential_integrity(
        self, column: str, valid_values: List[Any], severity: Severity
    ) -> DataQualityChecker:
        """Verifica que todos los valores no nulos de una columna estén en valid_values.

        Los nulls se ignoran aquí; validarlos por separado con check_nulls si es necesario.

        Args:
            column:       Columna a evaluar.
            valid_values: Conjunto de valores permitidos.
            severity:     Severidad asignada si hay valores inválidos.

        Returns:
            self para method chaining.
        """
        if column not in self.df.columns:
            log.warning(f"check_referential_integrity: columna '{column}' no existe en {self.table_name}")
            return self

        non_null  = self.df[column].dropna()
        n_total   = len(non_null)
        n_invalid = int((~non_null.isin(valid_values)).sum())
        rate      = (n_invalid / n_total * 100) if n_total > 0 else 0.0

        self.checks.append(QualityCheck(
            check_name      = f"referential:{column}",
            table           = self.table_name,
            column          = column,
            severity        = severity,
            passed          = n_invalid == 0,
            records_checked = n_total,
            records_failed  = n_invalid,
            failure_rate    = round(rate, 2),
            details         = f"{n_invalid} valores inválidos en {column}",
        ))
        return self

    def check_date_consistency(
        self, start_col: str, end_col: str, severity: Severity
    ) -> DataQualityChecker:
        """Verifica que start_col <= end_col en todas las filas con end_col no nulo.

        Args:
            start_col: Columna de fecha de inicio.
            end_col:   Columna de fecha de fin (nulls permitidos y se ignoran).
            severity:  Severidad asignada si hay inconsistencias.

        Returns:
            self para method chaining.
        """
        for col in (start_col, end_col):
            if col not in self.df.columns:
                log.warning(f"check_date_consistency: columna '{col}' no existe en {self.table_name}")
                return self

        # Solo evaluar filas donde end_col no es nulo
        mask      = self.df[end_col].notna()
        subset    = self.df[mask].copy()
        n_checked = len(subset)

        if n_checked == 0:
            n_bad = 0
        else:
            start = pd.to_datetime(subset[start_col])
            end   = pd.to_datetime(subset[end_col])
            n_bad = int((start > end).sum())

        rate = (n_bad / n_checked * 100) if n_checked > 0 else 0.0

        self.checks.append(QualityCheck(
            check_name      = f"date_consistency:{start_col}≤{end_col}",
            table           = self.table_name,
            column          = f"{start_col},{end_col}",
            severity        = severity,
            passed          = n_bad == 0,
            records_checked = n_checked,
            records_failed  = n_bad,
            failure_rate    = round(rate, 2),
            details         = f"{n_bad} filas donde {start_col} > {end_col}",
        ))
        return self

    def generate_report(self) -> QualityReport:
        """Agrega los resultados de todos los checks en un QualityReport.

        quality_score = (checks pasados / total checks) × 100.

        Returns:
            QualityReport listo para imprimir o serializar.
        """
        total    = len(self.checks)
        passed   = sum(1 for c in self.checks if c.passed)
        failed   = total - passed
        critical = sum(1 for c in self.checks if not c.passed and c.severity == Severity.CRITICAL)
        score    = round((passed / total * 100) if total > 0 else 100.0, 2)

        log.info(
            f"Quality report [{self.table_name}]: "
            f"{passed}/{total} passed, score={score:.1f}%, "
            f"{critical} critical failure(s)"
        )

        return QualityReport(
            table             = self.table_name,
            total_checks      = total,
            passed            = passed,
            failed            = failed,
            critical_failures = critical,
            quality_score     = score,
            checks            = self.checks,
            generated_at      = datetime.now().isoformat(timespec="seconds"),
        )

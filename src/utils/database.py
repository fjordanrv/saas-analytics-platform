"""
Conexión centralizada a la base de datos para CloudMetrics pipeline.

Soporta DuckDB (dev local) y Databricks (prod cloud).
El swap entre motores se controla exclusivamente con DB_TYPE en .env,
sin cambiar ninguna línea de código en los módulos que usan esta clase.
"""

import os
from pathlib import Path
from typing import Any, Optional

import duckdb
import pandas as pd
from dotenv import load_dotenv

from src.utils.logger import get_logger

load_dotenv()

log = get_logger(__name__)


class DatabaseConnection:
    """Singleton que gestiona la conexión activa a DuckDB o Databricks.

    El patrón Singleton garantiza que todo el pipeline comparte una sola
    conexión durante la ejecución, evitando conexiones duplicadas y
    simplificando la gestión de recursos.

    Usage:
        db = DatabaseConnection.get_instance()
        rows = db.execute("SELECT * FROM bronze.customers")
        df   = db.execute_df("SELECT * FROM bronze.customers")
    """

    _instance: Optional["DatabaseConnection"] = None

    def __init__(self) -> None:
        self.conn: Any = None
        self._db_type: str = os.getenv("DB_TYPE", "duckdb").lower()

    @classmethod
    def get_instance(cls) -> "DatabaseConnection":
        """Retorna la instancia única de DatabaseConnection (Singleton).

        Returns:
            La misma instancia en todas las llamadas dentro del proceso.
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def connect(self) -> None:
        """Abre la conexión al motor configurado en DB_TYPE.

        Lee las variables de entorno necesarias según el motor:
        - duckdb:     DUCKDB_PATH
        - databricks: DATABRICKS_HOST, DATABRICKS_HTTP_PATH, DATABRICKS_TOKEN

        Raises:
            ValueError: Si DB_TYPE tiene un valor no soportado.
            RuntimeError: Si la conexión falla por credenciales o ruta inválida.
        """
        if self._db_type == "duckdb":
            self._connect_duckdb()
        elif self._db_type == "databricks":
            self._connect_databricks()
        else:
            raise ValueError(
                f"DB_TYPE='{self._db_type}' no soportado. "
                "Valores válidos: 'duckdb', 'databricks'."
            )

    def _connect_duckdb(self) -> None:
        """Establece la conexión a DuckDB creando la carpeta del archivo si no existe."""
        db_path = os.getenv("DUCKDB_PATH")
        if not db_path:
            raise RuntimeError("DUCKDB_PATH no está definido en .env")

        path = Path(db_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        try:
            self.conn = duckdb.connect(str(path))
            log.info(f"Conectado a DuckDB: {path}")
        except Exception as e:
            raise RuntimeError(f"Error al conectar a DuckDB en '{path}': {e}") from e

    def _connect_databricks(self) -> None:
        """Establece la conexión a Databricks usando el SQL Connector."""
        # Import lazy: solo se carga cuando DB_TYPE=databricks
        try:
            import databricks.sql as dbsql
        except ImportError as e:
            raise RuntimeError(
                "El paquete 'databricks-sql-connector' no está instalado. "
                "Instálalo con: pip install databricks-sql-connector"
            ) from e

        host = os.getenv("DATABRICKS_HOST")
        http_path = os.getenv("DATABRICKS_HTTP_PATH")
        token = os.getenv("DATABRICKS_TOKEN")

        missing = [k for k, v in {
            "DATABRICKS_HOST": host,
            "DATABRICKS_HTTP_PATH": http_path,
            "DATABRICKS_TOKEN": token,
        }.items() if not v]

        if missing:
            raise RuntimeError(
                f"Variables de Databricks faltantes en .env: {', '.join(missing)}"
            )

        try:
            self.conn = dbsql.connect(
                server_hostname=host,
                http_path=http_path,
                access_token=token,
            )
            log.info(f"Conectado a Databricks: {host}")
        except Exception as e:
            raise RuntimeError(f"Error al conectar a Databricks: {e}") from e

    def execute(self, query: str, params: Optional[list] = None) -> list[tuple]:
        """Ejecuta una query SQL y retorna los resultados como lista de tuplas.

        Conecta automáticamente si no hay conexión activa.

        Args:
            query:  Sentencia SQL a ejecutar.
            params: Parámetros posicionales para queries parametrizadas (opcional).

        Returns:
            Lista de tuplas con las filas resultantes. Lista vacía para
            sentencias DDL/DML que no retornan filas.

        Raises:
            RuntimeError: Si la ejecución falla.
        """
        if self.conn is None:
            self.connect()

        try:
            if self._db_type == "duckdb":
                result = self.conn.execute(query, params or [])
                return result.fetchall()
            else:
                cursor = self.conn.cursor()
                cursor.execute(query, params or [])
                return cursor.fetchall()
        except Exception as e:
            log.error(f"Error ejecutando query: {e}\nSQL: {query[:200]}")
            raise RuntimeError(f"Error en execute(): {e}") from e

    def execute_df(self, query: str, params: Optional[list] = None) -> pd.DataFrame:
        """Ejecuta una query SQL y retorna el resultado como pandas DataFrame.

        Conecta automáticamente si no hay conexión activa.

        Args:
            query:  Sentencia SQL SELECT a ejecutar.
            params: Parámetros posicionales para queries parametrizadas (opcional).

        Returns:
            DataFrame de pandas con los resultados. DataFrame vacío si no
            hay filas.

        Raises:
            RuntimeError: Si la ejecución falla.
        """
        if self.conn is None:
            self.connect()

        try:
            if self._db_type == "duckdb":
                result = self.conn.execute(query, params or [])
                return result.df()
            else:
                cursor = self.conn.cursor()
                cursor.execute(query, params or [])
                columns = [desc[0] for desc in cursor.description]
                return pd.DataFrame(cursor.fetchall(), columns=columns)
        except Exception as e:
            log.error(f"Error ejecutando query a DataFrame: {e}\nSQL: {query[:200]}")
            raise RuntimeError(f"Error en execute_df(): {e}") from e

    def write_dataframe(self, df: pd.DataFrame, table_name: str) -> None:
        """Escribe un DataFrame como tabla en el motor configurado.

        Para DuckDB usa register() + CREATE OR REPLACE TABLE.
        Para Databricks usa Parquet + Unity Catalog Volume + COPY INTO.

        Args:
            df:         DataFrame a escribir.
            table_name: Nombre completo de la tabla (ej. 'bronze.customers').
        """
        if self.conn is None:
            self.connect()

        if self._db_type == "duckdb":
            self._write_duckdb(df, table_name)
        else:
            self._write_databricks(df, table_name)

    def _write_duckdb(self, df: pd.DataFrame, table_name: str) -> None:
        """Escribe DataFrame en DuckDB via register() + CREATE OR REPLACE TABLE."""
        try:
            self.conn.register("_tmp_write", df)
            self.conn.execute(f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM _tmp_write")
            log.info(f"Escrito en DuckDB: {table_name} ({len(df):,} filas)")
        except Exception as e:
            raise RuntimeError(f"Error escribiendo en DuckDB '{table_name}': {e}") from e

    def _write_databricks(self, df: pd.DataFrame, table_name: str) -> None:
        """Escribe DataFrame en Databricks via Parquet + Unity Catalog Volume + COPY INTO."""
        import tempfile
        import requests

        host = os.getenv("DATABRICKS_HOST")
        token = os.getenv("DATABRICKS_TOKEN")
        catalog = os.getenv("DATABRICKS_CATALOG", "saas_platform")

        # Extraer solo el nombre de tabla sin schema (ej. 'bronze.customers' → 'customers')
        short_name = table_name.split(".")[-1]
        volume_path = f"/Volumes/{catalog}/bronze/raw_files/{short_name}.parquet"

        # 1. Guardar Parquet en archivo temporal
        with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp:
            local_path = tmp.name
        df.to_parquet(local_path, index=False)
        log.info(f"Parquet guardado temporalmente: {local_path}")

        try:
            # 2. Subir al Volume via REST API
            with open(local_path, "rb") as f:
                response = requests.put(
                    f"https://{host}/api/2.0/fs/files{volume_path}",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/octet-stream",
                    },
                    data=f,
                )
            response.raise_for_status()
            log.info(f"Subido a Volume: {volume_path}")

            # 3. Crear tabla Delta si no existe
            cols = []
            for col, dtype in zip(df.columns, df.dtypes):
                dtype_str = str(dtype)
                if "int" in dtype_str:
                    sql_type = "BIGINT"
                elif "float" in dtype_str:
                    sql_type = "DOUBLE"
                elif "bool" in dtype_str:
                    sql_type = "BOOLEAN"
                elif "datetime" in dtype_str:
                    sql_type = "TIMESTAMP"
                elif "date" in dtype_str:
                    sql_type = "DATE"
                else:
                    sql_type = "STRING"
                cols.append(f"`{col}` {sql_type}")

            cursor = self.conn.cursor()
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {catalog}.{table_name}
                ({", ".join(cols)})
                USING DELTA
            """)
            cursor.execute(f"TRUNCATE TABLE {catalog}.{table_name}")

            # 4. COPY INTO desde Volume
            cursor.execute(f"""
                COPY INTO {catalog}.{table_name}
                FROM '{volume_path}'
                FILEFORMAT = PARQUET
                FORMAT_OPTIONS ('mergeSchema' = 'true')
                COPY_OPTIONS ('mergeSchema' = 'true', 'force' = 'true')
            """)
            cursor.close()
            log.info(f"Escrito en Databricks: {catalog}.{table_name} ({len(df):,} filas)")

        finally:
            # 5. Limpiar archivo temporal local
            import os as _os
            _os.remove(local_path)

    def create_schema(self, schema_name: str) -> None:
        """Crea un schema en la base de datos si no existe.

        Args:
            schema_name: Nombre del schema a crear (ej. 'bronze', 'silver', 'gold').
        """
        try:
            self.execute(f"CREATE SCHEMA IF NOT EXISTS {schema_name}")
            log.info(f"Schema '{schema_name}' listo")
        except Exception as e:
            log.error(f"Error creando schema '{schema_name}': {e}")
            raise

    def close(self) -> None:
        """Cierra la conexión activa y resetea la instancia Singleton.

        Llama a este método al final del pipeline o en bloques finally
        para liberar recursos correctamente.
        """
        if self.conn is not None:
            try:
                self.conn.close()
                log.info(f"Conexión a {self._db_type} cerrada")
            except Exception as e:
                log.warning(f"Error al cerrar la conexión: {e}")
            finally:
                self.conn = None
                DatabaseConnection._instance = None

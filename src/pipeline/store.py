import sqlite3
import pandas as pd
from pathlib import Path


DB_PATH = Path("data/energy.db")


# ── Init ──────────────────────────────────────────────────────────────────────

def init_db(db_path: Path = DB_PATH) -> None:
    """
    Initialize the SQLite database and create tables if they don't exist.

    Tables
    ------
    power_actual_load : electricity load in MW (15-min intervals) from entsoe
    power_prices_DA      : day-ahead electricity prices in €/MWh (15-min intervals) from entsoe
    ttf_prices        : TTF natural gas prices (daily) form yfinance
    brent_prices      : Brent crude oil prices (daily) from yfinance
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS power_actual_load (
                timestamp TEXT NOT NULL,
                country   TEXT NOT NULL,
                value     REAL NOT NULL,
                PRIMARY KEY (timestamp, country)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS power_prices_DA (
                timestamp TEXT NOT NULL,
                country   TEXT NOT NULL,
                value     REAL NOT NULL,
                PRIMARY KEY (timestamp, country)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ttf_prices (
                timestamp TEXT NOT NULL PRIMARY KEY,
                value     REAL NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS brent_prices (
                timestamp TEXT NOT NULL PRIMARY KEY,
                value     REAL NOT NULL
            )
        """)
        conn.commit()
    print(f"[DB] Initialized at {db_path}")


# ── Save ──────────────────────────────────────────────────────────────────────

def get_table_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    """
    Return column names for a SQLite table.
    """
    cursor = conn.execute(f"PRAGMA table_info({table})")
    columns = [row[1] for row in cursor.fetchall()]

    if not columns:
        raise ValueError(f"Table '{table}' does not exist or has no columns.")

    return columns


def save_series(series: pd.Series, table: str, country: str | None = None, db_path: Path = DB_PATH) -> None:
    """
    Save a pd.Series to a SQLite table.

    The function adapts automatically to the target table schema:

    - Tables with a `country` column: timestamp, country, value
    - Tables without a `country` column: timestamp, value

    Duplicate rows are handled with `INSERT OR REPLACE`, based on the table's primary key.

    Parameters
    ----------
    series : pd.Series
        Time series indexed by timestamp.

    table : str
        Target SQLite table name.
        Examples: "power_actual_load", "power_prices", "ttf_prices", "brent_prices".

    country : str | None, optional
        Country code used for country-specific tables.
        Required if the target table contains a `country` column.
        Examples: "FR", "DE", "NL".

    db_path : Path, optional
        Path to the SQLite database.

    Examples
    --------
    >>> save_series(load, "power_actual_load", country="FR")
    >>> save_series(brent, "brent_prices")
    """

    if series.empty:
        print(f"[DB] Nothing to save to '{table}'")
        return

    df = series.dropna().reset_index()
    df.columns = ["timestamp", "value"]

    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True).dt.strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )

    with sqlite3.connect(db_path) as conn:
        table_columns = get_table_columns(conn, table)

        required_columns = ["timestamp", "value"]

        if "country" in table_columns:
            if country is None:
                raise ValueError(f"Table '{table}' requires a country.")

            df["country"] = country
            insert_columns = ["timestamp", "country", "value"]

        else:
            insert_columns = ["timestamp", "value"]

        missing_columns = [col for col in required_columns if col not in table_columns]
        if missing_columns:
            raise ValueError(
                f"Table '{table}' is missing required columns: {missing_columns}"
            )

        records = list(
            df[insert_columns].itertuples(index=False, name=None)
        )

        columns_sql = ", ".join(insert_columns)
        placeholders = ", ".join(["?"] * len(insert_columns))

        query = f"""
            INSERT OR REPLACE INTO {table}
            ({columns_sql})
            VALUES ({placeholders})
        """

        conn.executemany(query, records)
        conn.commit()

    print(f"[DB] Saved {len(df)} rows to '{table}'")

# ── Load ──────────────────────────────────────────────────────────────────────

def load_series(table: str, country: str, db_path: Path = DB_PATH) -> pd.Series:
    """
    Load a full time series from SQLite as a pd.Series.

    Parameters
    ----------
    table : str
        Source table name. Ex: "load", "prices"
    country : str
        Country code. Ex: "FR", "DE"
    db_path : Path, optional
        Path to the SQLite database.

    Returns
    -------
    pd.Series
        Time series indexed by timestamp, sorted ascending.

    Examples
    --------
    >>> load = load_series("load", "FR")
    >>> prices = load_series("prices", "FR")
    """
    with sqlite3.connect(db_path) as conn:
        df = pd.read_sql(
            f"SELECT timestamp, value FROM {table} WHERE country = '{country}' ORDER BY timestamp",
            conn,
            parse_dates=["timestamp"],
            index_col="timestamp"
        )

    series = df["value"]
    series.name = f"{table}_{country}"
    return series


# ── Last update ───────────────────────────────────────────────────────────────

def get_last_timestamp(table: str, country: str, db_path: Path = DB_PATH) -> pd.Timestamp | None:
    """
    Get the most recent timestamp stored in a table for a given country.

    Parameters
    ----------
    table : str
        Table name. Ex: "load", "prices"
    country : str
        Country code. Ex: "FR", "DE"

    Returns
    -------
    pd.Timestamp or None
        Last available timestamp, or None if table is empty.

    Examples
    --------
    >>> last = get_last_timestamp("load", "FR")
    """
    with sqlite3.connect(db_path) as conn:
        result = conn.execute(
            f"SELECT MAX(timestamp) FROM {table} WHERE country = '{country}'"
        ).fetchone()[0]

    if result is None:
        return None

    return pd.Timestamp(result)

if __name__ == "__main__" : 
    print("DB code start")
    init_db()


    #TEST CODE
    import sys
   # Add project root to path
    sys.path.append(str(Path(__file__).resolve().parents[2]))

    from src.pipeline.fetch import get_power_load,get_power_prices,get_yf_prices
    from datetime import datetime
    import yfinance as yf

    country = "FR"

    # load = get_power_load(
    #     start="2026-01-01",
    #     end=datetime.today().strftime("%Y-%m-%d"),
    #     country=country  
    # )

    # prices = get_power_prices(
    #     start="2026-01-01",
    #     end=datetime.today().strftime("%Y-%m-%d"),
    #     country=country 
    # )


    ttf = yf.download("TTF=F", start="2020-01-01")["Close"]
    brent = yf.download("BZ=F", start="2020-01-01")["Close"]


    save_series(ttf,   "ttf_prices")
    save_series(brent, "brent_prices")
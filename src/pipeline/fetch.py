import os 
from pathlib import Path
import requests
import pandas as pd
from entsoe import EntsoePandasClient
from dotenv import load_dotenv
import yfinance as yf


# ─── ICE OPTION PRICES ────────────────────────────────────────────────────────────
def fetch_ice_historical_prices(market_id: int, historical_span: int = 3) -> pd.DataFrame:
    """
    Fetch historical ICE chart data for a given marketId.

    Parameters
    ----------
    market_id : int
        ICE marketId for the contract.
    historical_span : int
        ICE chart span.
        From observation:
        - 0 = Intraday
        - 1 = 3 month
        - 2 = 1 year
        - 3 = 2 years

    Returns
    -------
    pd.DataFrame
        DataFrame indexed by date with price values.
    
    Examples
    --------
    >>> Coal_2y_Jul26 = fetch_ice_historical_prices(market_id=6265632,historical_span=3)
    """

    if historical_span == 0 :
        url = (
        "https://www.ice.com/marketdata/api/productguide/charting/data/current-day"
        f"?marketId={market_id}"
    )
    else : 
        url = (
            "https://www.ice.com/marketdata/api/productguide/charting/data/historical"
            f"?marketId={market_id}&historicalSpan={historical_span}"
        )

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
    }

    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()

    data = response.json()

    bars = data.get("bars", [])

    if not bars:
        raise ValueError(f"No price bars returned for marketId={market_id}")

    df = pd.DataFrame(bars, columns=["date", "coal_price_usd_tonne"])

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["coal_price_usd_tonne"] = pd.to_numeric(
        df["coal_price_usd_tonne"],
        errors="coerce",
    )

    df = df.dropna().set_index("date").sort_index()

    return df

# ─── BRENT + TTF PRICES ────────────────────────────────────────────────────────────

def get_yf_prices(tickers,name:str ,start: str, end: str, interval: str = "1d") -> pd.Series:
    """
    Download closing prices from Yahoo Finance.

    Parameters
    ----------
    tickers : str | list[str]
        Yahoo Finance ticker(s). Ex: "TTF=F", "BZ=F", "MTF=F"
    name : str
        Name of the returned series. Ex: "ttf", "brent", "coal"
    start : str
        Start date in "YYYY-MM-DD" format. Ex: "2020-01-01"
    end : str
        End date in "YYYY-MM-DD" format. Ex: "2024-12-31"
    interval : str, optional
        Data frequency. "1d" (default), "1wk", "1mo"

    Returns
    -------
    pd.Series
        Time series of closing prices indexed by date.

    Examples
    --------
    >>> ttf = get_yf_prices("TTF=F", "ttf", "2022-01-01", "2024-01-01")
    >>> brent = get_yf_prices("BZ=F", "brent", "2022-01-01", "2024-01-01")
    """

    df = yf.download(tickers=tickers, start=start, end=end, interval=interval, auto_adjust=True, progress=False)
    return df["Close"].squeeze().rename(name)




# ─── POWER PRICES ────────────────────────────────────────────────────────────

def get_entsoe_client():
    load_dotenv(Path(".env"))
    api_key = os.getenv("ENTSOE_API_KEY")
    return EntsoePandasClient(api_key=api_key)

def get_power_prices(start: str, end: str, country: str = "FR",tz: str = "Europe/Paris") -> pd.Series:
    """
    Fetch day-ahead electricity prices from ENTSO-E Transparency Platform.

    Parameters
    ----------
    start : str
        Start date in "YYYY-MM-DD" format. Ex: "2020-01-01"
    end : str
        End date in "YYYY-MM-DD" format. Ex: "2024-12-31"
    country : str, optional
        ENTSO-E country code (default: "FR").
        Supported: "FR", "DE", "NL", "BE", "ES", "IT" ...
    tz : str, optional
        Timezone for timestamps (default: "Europe/Paris").
        Must match the country. Ex: "Europe/Berlin" for "DE"

    Returns
    -------
    pd.Series
        Hourly day-ahead prices in €/MWh, indexed by UTC timestamp.
        Series name: "power_{country}". Ex: "power_FR"

    Examples
    --------
    >>> prices = get_power_prices("2022-01-01", "2024-01-01", country="FR")
    >>> prices_de = get_power_prices("2022-01-01", "2024-01-01", country="DE", tz="Europe/Berlin")
    """
    
    client = get_entsoe_client()
    start_ts = pd.Timestamp(start, tz=tz)
    end_ts   = pd.Timestamp(end,   tz=tz)

    prices = client.query_day_ahead_prices(country, start=start_ts, end=end_ts)
    prices.name = f"power_{country}"
    return prices



def get_all_prices(start: str = "2020-01-01", end: str = "2024-12-31") -> pd.DataFrame:

    power  = get_power_prices(start, end)
    ttf = get_yf_prices("TTF=F", "ttf", start=start, end=end)
    brent = get_yf_prices("BZ=F", "brent",start=start, end=end)
    # coal   = get_coal_prices(start, end)

    df = pd.DataFrame({
        "power": power,
        "ttf":   ttf,
        "brent": brent,
        # "coal":  coal,
    })

    df = df.ffill().dropna()
    return df


def get_power_load(start: str, end: str, country: str = "FR",tz: str = "Europe/Paris") -> pd.Series:
    """
    Fetch actual electricity load (consumption) from ENTSO-E Transparency Platform.

    Parameters
    ----------
    start : str
        Start date in "YYYY-MM-DD" format. Ex: "2020-01-01"
    end : str
        End date in "YYYY-MM-DD" format. Ex: "2024-12-31"
    country : str, optional
        ENTSO-E country code (default: "FR").
        Supported: "FR", "DE", "NL", "BE", "ES", "IT" ...
    tz : str, optional
        Timezone for timestamps (default: "Europe/Paris").
        Must match the country. Ex: "Europe/Berlin" for "DE"

    Returns
    -------
    pd.Series
        Hourly actual electricity load in MW, indexed by UTC timestamp.
        Series name: "load_{country}". Ex: "load_FR"

    Examples
    --------
    >>> load = get_power_load("2022-01-01", "2024-01-01", country="FR")
    """
    client = get_entsoe_client()
    start_ts = pd.Timestamp(start, tz=tz)
    end_ts   = pd.Timestamp(end,   tz=tz)

    load = client.query_load(country, start=start_ts, end=end_ts)
    load = load.squeeze()
    load.name = f"load_{country}"

    return load





# ─── TEMPERATURE ────────────────────────────────────────────────────────────
def get_avg_temp(country:str, cities:dict , start_date: str, end_date:str, tz: str = "Europe/Paris") -> pd.Series: 
    """
    Fetch and average daily mean temperatures across multiple cities via Open-Meteo API.

    Parameters
    ----------
    country : str
        Country identifier used to name the output series. Ex: "FR", "DE"
    cities : dict
        Dictionary mapping city names to (latitude, longitude) tuples.
        Ex: {"Paris": (48.8566, 2.3522), "Lyon": (45.7640, 4.8357)}
    start_date : str
        Start date in "YYYY-MM-DD" format. Ex: "2026-01-01"
    end_date : str
        End date in "YYYY-MM-DD" format. Ex: "2026-12-31"
    tz : str, optional
        Timezone for timestamps (default: "Europe/Paris").

    Returns
    -------
    pd.Series
        Daily mean temperature in °C averaged across all cities, indexed by date. 
        Series name: "mean_temperature_{country}".
        Ex: "mean_temperature_FR"

    Examples
    --------
    >>> cities = {"Paris": (48.8566, 2.3522), "Lyon": (45.7640, 4.8357)}
    >>> temp = get_avg_temp("FR", cities, "2022-01-01", "2024-01-01")
    """

    df_temp = pd.DataFrame()

    for city, (lat, lon) in cities.items():
        url = "https://archive-api.open-meteo.com/v1/archive"
        params = {
            "latitude": lat,
            "longitude": lon,
            "start_date": start_date,
            "end_date": end_date,
            "daily": "temperature_2m_mean",
            "timezone": tz
        }

        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        dates = pd.to_datetime(data["daily"]["time"])
        temperatures = data["daily"]["temperature_2m_mean"]

        df_temp[city] = pd.Series(temperatures, index=dates)

    # Mean
    serie_temp = df_temp.mean(axis=1)
    serie_temp.name = f"mean_temperature_{country}"

    return serie_temp

def get_missing_load(db_path: str, country: str = "FR", tz: str = "Europe/Paris") -> pd.Series | None:
   return



if __name__ == "__main__":
    load = get_power_load(start="2026-01-01",
        end="2026-01-07",
        country="FR")
    
    print(load)
    print(type(load))
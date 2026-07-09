import os
import pandas as pd
import yaml
from dotenv import load_dotenv
import yfinance as yf

load_dotenv() 

def load_config():
    with open("config/settings.yaml", "r") as f:
        config = yaml.safe_load(f)

    config["api"]["entsoe_key"] = os.getenv("ENTSOE_API_KEY")
    
    return config

def compute_spark_spread(power: pd.Series, gaz: pd.Series, heat_rate_mwh: float = 2.0) -> pd.Series:
    """
    Calculate the spark spread.

    Spark spread = power price (€/MWh_e) - gas price (€/MWh_th) * heat rate

    TTF gas prices are expressed in €/MWh_th.
    The heat rate is expressed in MWh_th/MWh_e and represents the amount
    of thermal gas energy required to produce one MWh of electricity.

    Parameters
    ----------
    power_price : pd.Series
        Power price in €/MWh_e.
    gas_price : pd.Series
        Gas price in €/MWh_th.
    heat_rate : float
        Gas plant heat rate in MWh_th/MWh_e.

    Returns
    -------
    pd.Series
        Spark spread in €/MWh_e.
    """
        
    return power - (gaz * heat_rate_mwh)

def compute_dark_spread(power: pd.Series, coal: pd.Series, heat_rate: float = 8.5) -> pd.Series:
    """
    Calculate the dark spread.

    Dark spread = power price (€/MWh_e) - coal price (€/MWh_th) * heat rate

    Coal prices must be expressed in €/MWh_th.
    The heat rate is expressed in MWh_th/MWh_e and represents the amount
    of thermal coal energy required to produce one MWh of electricity.

    Parameters
    ----------
    power_price : pd.Series
        Power price in €/MWh_e.
    coal_price : pd.Series
        Coal price in €/MWh_th.
    heat_rate : float
        Coal plant heat rate in MWh_th/MWh_e.

    Returns
    -------
    pd.Series
        Dark spread in €/MWh_e.
    """
    return power - (coal * heat_rate)

def coal_usd_tonne_to_eur_mwh_th(coal_price_usd_tonne: pd.Series, eurusd: float, calorific_value_kcal_kg: float = 6000) -> pd.Series:
    """
    Convert a thermal coal price from USD/tonne to EUR/MWh_th.

    The default calorific value is 6,000 kcal/kg, consistent with the
    common API2 / CIF ARA thermal coal benchmark used in Europe.

    Formula
    -------
    MWh_th per tonne = calorific_value_kcal_kg * 1000 / 860_420

    coal_price_eur_mwh_th =
        coal_price_usd_tonne / EURUSD / MWh_th_per_tonne

    Parameters
    ----------
    coal_price_usd_tonne : pd.Series
        Coal price in USD per metric tonne.
    eurusd : float
        EUR/USD exchange rate, expressed as USD per EUR.
        Example: 1.08 means 1 EUR = 1.08 USD.
    calorific_value_kcal_kg : float, default 6000
        Coal calorific value in kcal/kg.

    Returns
    -------
    pd.Series
        Coal price in EUR/MWh_th.
    """
    mwh_th_per_tonne = calorific_value_kcal_kg * 1000 / 860_420
    return coal_price_usd_tonne / eurusd / mwh_th_per_tonne


def get_peak_offpeak_spread(prices: pd.Series) -> pd.DataFrame:
    """
    Compute daily peak vs off-peak price spread.

    Peak hours    : 08h00–20h00 on weekdays
    Off-peak hours: 20h00–08h00 + weekends

    Parameters
    ----------
    prices : pd.Series
        15-min or hourly day-ahead electricity prices in €/MWh.

    Returns
    -------
    pd.DataFrame
        Daily DataFrame with columns:
        - peak               : mean price during peak hours (€/MWh)
        - offpeak            : mean price during off-peak hours (€/MWh)
        - peak_offpeak_spread: peak minus offpeak (€/MWh)

    Examples
    --------
    >>> df = get_peak_offpeak_spread(prices)
    >>> df["peak_offpeak_spread"].plot()
    """
    prices = prices.sort_index()

    peak_mask = (
        (prices.index.hour >= 8) &
        (prices.index.hour < 20) &
        (prices.index.dayofweek < 5)
    )

    peak = prices[peak_mask].resample("1D").mean().rename("peak")
    offpeak = prices[~peak_mask].resample("1D").mean().rename("offpeak")
    spread = (peak - offpeak).rename("peak_offpeak_spread")

    return pd.DataFrame({
        "peak": peak,
        "offpeak": offpeak,
        "peak_offpeak_spread": spread
    })



if __name__ == "__main__":
    ttf = yf.download("TTF=F", start="2020-01-01")["Close"]
    brent = yf.download("BZ=F", start="2020-01-01")["Close"]
    print(ttf)

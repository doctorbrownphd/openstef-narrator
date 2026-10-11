"""NWS weather API integration — free hourly temperature forecasts.

Uses the National Weather Service API (api.weather.gov) to fetch
hourly temperature forecasts for feeder service territories. No API
key is required.

This module is opt-in: it requires ``httpx`` (install with
``pip install openstef-narrator[weather]``). The core narrator works
without it.
"""

from __future__ import annotations

try:
    import httpx
except ImportError:
    httpx = None  # type: ignore[assignment]

# ------------------------------------------------------------------
# NWS location mapping — feeder districts to (lat, lon)
# ------------------------------------------------------------------
NWS_LOCATIONS: dict[str, tuple[float, float]] = {
    "Eastgate": (44.4759, -73.2121),       # Burlington, VT
    "Mill District": (42.6334, -71.3162),  # Lowell, MA
    "Northborough": (42.3195, -71.6417),   # Northborough, MA
    "Lakeside": (43.5278, -71.4704),       # Laconia, NH
    "Riverside": (41.7658, -72.6734),      # Hartford, CT
}


def fetch_nws_forecast(lat: float, lon: float) -> list[dict]:
    """Fetch hourly temperature forecast from the NWS API.

    Parameters
    ----------
    lat, lon : float
        Coordinates for the forecast point.

    Returns
    -------
    list[dict]
        Up to 48 entries of ``{"hour": int, "temperature": float}``
        where hour is an offset from 0 and temperature is in Fahrenheit.
        Returns an empty list on any failure.
    """
    if httpx is None:
        return []

    headers = {"User-Agent": "openstef-narrator/0.1 (github.com/doctorbrownphd/openstef-narrator)"}

    try:
        # Step 1: resolve the forecast grid endpoint
        points_url = f"https://api.weather.gov/points/{lat},{lon}"
        with httpx.Client(headers=headers, timeout=10.0) as client:
            resp = client.get(points_url)
            resp.raise_for_status()
            forecast_url = resp.json()["properties"]["forecastHourly"]

            # Step 2: fetch the hourly forecast
            resp2 = client.get(forecast_url)
            resp2.raise_for_status()
            periods = resp2.json()["properties"]["periods"]

        # Extract up to 48 hours
        result = []
        for i, period in enumerate(periods[:48]):
            result.append({
                "hour": i,
                "temperature": float(period["temperature"]),
            })
        return result

    except Exception:
        return []


def get_temperature_forecast(feeder_id: str) -> list[float] | None:
    """Get 48-hour temperature forecast for a feeder's district.

    Parameters
    ----------
    feeder_id : str
        A feeder ID (e.g. ``"feeder7"``). The feeder's district is
        looked up to find NWS coordinates.

    Returns
    -------
    list[float] or None
        48 hourly temperatures in Fahrenheit, or None on failure.
    """
    from openstef_narrator.feeders import get_feeder

    try:
        feeder = get_feeder(feeder_id)
    except ValueError:
        return None

    coords = NWS_LOCATIONS.get(feeder.district)
    if coords is None:
        return None

    lat, lon = coords
    forecast = fetch_nws_forecast(lat, lon)
    if not forecast:
        return None

    return [entry["temperature"] for entry in forecast]

"""Tests for the NWS weather module — all HTTP calls are mocked."""

from unittest.mock import MagicMock, patch

from openstef_narrator.weather import (
    NWS_LOCATIONS,
    fetch_nws_forecast,
    get_temperature_forecast,
)


def _mock_nws_responses():
    """Create mock httpx responses for the two-step NWS flow."""
    # Mock the points response
    points_response = MagicMock()
    points_response.status_code = 200
    points_response.json.return_value = {
        "properties": {
            "forecastHourly": "https://api.weather.gov/gridpoints/GYX/50,50/forecast/hourly",
        }
    }
    points_response.raise_for_status = MagicMock()

    # Mock the hourly forecast response with 48 periods
    periods = [
        {"temperature": 65.0 + i * 0.5, "temperatureUnit": "F"}
        for i in range(48)
    ]
    forecast_response = MagicMock()
    forecast_response.status_code = 200
    forecast_response.json.return_value = {
        "properties": {"periods": periods}
    }
    forecast_response.raise_for_status = MagicMock()

    return points_response, forecast_response


class TestFetchNwsForecast:
    def test_returns_48_hours(self):
        points_resp, forecast_resp = _mock_nws_responses()

        mock_client = MagicMock()
        mock_client.get.side_effect = [points_resp, forecast_resp]
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        mock_httpx = MagicMock()
        mock_httpx.Client.return_value = mock_client

        with patch("openstef_narrator.weather.httpx", mock_httpx):
            result = fetch_nws_forecast(44.4759, -73.2121)

        assert len(result) == 48
        assert result[0]["hour"] == 0
        assert result[0]["temperature"] == 65.0
        assert result[47]["hour"] == 47

    def test_returns_empty_on_http_error(self):
        mock_client = MagicMock()
        mock_client.get.side_effect = Exception("Connection timeout")
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        mock_httpx = MagicMock()
        mock_httpx.Client.return_value = mock_client

        with patch("openstef_narrator.weather.httpx", mock_httpx):
            result = fetch_nws_forecast(44.4759, -73.2121)

        assert result == []

    def test_returns_empty_when_httpx_is_none(self):
        with patch("openstef_narrator.weather.httpx", None):
            result = fetch_nws_forecast(44.4759, -73.2121)
        assert result == []

    def test_hour_and_temperature_shape(self):
        points_resp, forecast_resp = _mock_nws_responses()

        mock_client = MagicMock()
        mock_client.get.side_effect = [points_resp, forecast_resp]
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        mock_httpx = MagicMock()
        mock_httpx.Client.return_value = mock_client

        with patch("openstef_narrator.weather.httpx", mock_httpx):
            result = fetch_nws_forecast(42.0, -71.0)

        for entry in result:
            assert "hour" in entry
            assert "temperature" in entry
            assert isinstance(entry["hour"], int)
            assert isinstance(entry["temperature"], float)


class TestNwsLocations:
    def test_all_five_districts_mapped(self):
        expected = {"Eastgate", "Mill District", "Northborough", "Lakeside", "Riverside"}
        assert set(NWS_LOCATIONS.keys()) == expected

    def test_coordinates_are_tuples(self):
        for district, coords in NWS_LOCATIONS.items():
            assert isinstance(coords, tuple)
            assert len(coords) == 2


class TestGetTemperatureForecast:
    def test_returns_list_of_floats(self):
        points_resp, forecast_resp = _mock_nws_responses()

        mock_client = MagicMock()
        mock_client.get.side_effect = [points_resp, forecast_resp]
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        mock_httpx = MagicMock()
        mock_httpx.Client.return_value = mock_client

        with patch("openstef_narrator.weather.httpx", mock_httpx):
            result = get_temperature_forecast("feeder7")

        assert result is not None
        assert len(result) == 48
        assert all(isinstance(t, float) for t in result)

    def test_unknown_feeder_returns_none(self):
        result = get_temperature_forecast("nonexistent_feeder")
        assert result is None

    def test_api_failure_returns_none(self):
        mock_client = MagicMock()
        mock_client.get.side_effect = Exception("Network error")
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        mock_httpx = MagicMock()
        mock_httpx.Client.return_value = mock_client

        with patch("openstef_narrator.weather.httpx", mock_httpx):
            result = get_temperature_forecast("feeder7")

        assert result is None

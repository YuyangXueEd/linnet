from extensions.base import FeedSection
from extensions.weather import WeatherExtension
from extensions.weather.collector import describe_weather_code, fetch_today_weather


def test_describe_weather_code_maps_known_values():
    assert describe_weather_code(2) == "Partly cloudy"
    assert describe_weather_code(99) == "Thunderstorm with heavy hail"


def test_fetch_today_weather_resolves_city_and_parses_forecast(httpx_mock):
    httpx_mock.add_response(
        json={
            "results": [
                {
                    "name": "Boston",
                    "admin1": "Massachusetts",
                    "country": "United States",
                    "latitude": 42.3601,
                    "longitude": -71.0589,
                }
            ]
        }
    )
    httpx_mock.add_response(
        json={
            "timezone": "America/New_York",
            "current": {
                "temperature_2m": 14.5,
                "apparent_temperature": 13.9,
                "relative_humidity_2m": 62,
                "weather_code": 2,
                "wind_speed_10m": 12.3,
                "is_day": 1,
            },
            "daily": {
                "time": ["2026-04-13"],
                "temperature_2m_max": [16.2],
                "temperature_2m_min": [8.1],
                "precipitation_probability_max": [30],
                "sunrise": ["2026-04-13T06:05"],
                "sunset": ["2026-04-13T19:27"],
            },
        }
    )

    items = fetch_today_weather("Boston")

    assert len(items) == 1
    assert items[0]["label"] == "Boston, Massachusetts, United States"
    assert items[0]["condition"] == "Partly cloudy"
    assert items[0]["temp_max_c"] == 16.2
    assert items[0]["precipitation_probability_pct"] == 30

    requests = httpx_mock.get_requests()
    assert requests[0].url.host == "geocoding-api.open-meteo.com"
    assert requests[0].url.params["name"] == "Boston"
    assert requests[1].url.host == "api.open-meteo.com"


def test_fetch_today_weather_returns_empty_when_city_not_found(httpx_mock):
    httpx_mock.add_response(json={"results": []})

    assert fetch_today_weather("Atlantis") == []


def test_weather_extension_render_includes_icon_and_city():
    ext = WeatherExtension({"city": "Boston"})

    section = ext.render([{"label": "Boston"}])

    assert isinstance(section, FeedSection)
    assert section.icon == "🌦️"
    assert section.meta["city"] == "Boston"

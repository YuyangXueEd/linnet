# weather extension

Fetches today's weather forecast for one configured city and renders it as
a brief summary card at the top of the daily digest.

Data comes from [Open-Meteo](https://open-meteo.com/) — a free, no-API-key
weather service. City names are resolved via the Open-Meteo Geocoding API.

---

## Pipeline

```
fetch()    — resolves city name → lat/lon via Open-Meteo Geocoding API
           → fetches current conditions + today's daily forecast
process()  — pass-through (no LLM calls)
render()   — wraps the single weather item in a FeedSection
```

---

## Config

**`config/sources.yaml`**:

| Key | Default | Notes |
|---|---|---|
| `enabled` | `true` | Set to `false` to skip weather entirely |
| `city` | `""` | City name to look up, e.g. `"Edinburgh"`. Required. |
| `timezone` | `"auto"` | `"auto"` uses the city's local timezone. Or set explicitly, e.g. `"Europe/London"` |

**`config/extensions/weather.yaml`**:

| Key | Default | Notes |
|---|---|---|
| `city` | — | Overrides the `city` key in sources.yaml if set here |
| `timezone` | `"auto"` | Overrides the `timezone` key in sources.yaml if set here |

The full list of valid timezone strings follows the IANA tz database
(e.g. `"America/New_York"`, `"Asia/Tokyo"`).

---

## Output item schema

One item is returned per successful fetch:

```python
{
    "query":                      str,          # city name as typed in config
    "label":                      str,          # "Edinburgh, Scotland, United Kingdom"
    "resolved_name":              str,          # canonical name from geocoder
    "region":                     str,          # admin1 region (state / county)
    "country":                    str,
    "latitude":                   float,
    "longitude":                  float,
    "timezone":                   str,          # IANA tz string actually used
    "forecast_date":              str,          # ISO date, e.g. "2026-04-15"
    "condition":                  str,          # human-readable, e.g. "Partly cloudy"
    "weather_code":               int,          # WMO weather interpretation code
    "temperature_c":              float,        # current temperature °C
    "apparent_temperature_c":     float,        # "feels like" °C
    "temp_max_c":                 float,        # today's high °C
    "temp_min_c":                 float,        # today's low °C
    "humidity_pct":               int,          # relative humidity %
    "wind_speed_kmh":             float,        # wind speed km/h
    "precipitation_probability_pct": int | None, # chance of rain today %
    "is_day":                     bool,         # True if fetched during daytime
    "sunrise":                    str,          # ISO datetime
    "sunset":                     str,          # ISO datetime
    "source":                     str,          # "Open-Meteo"
    "source_url":                 str,          # "https://open-meteo.com/"
}
```

---

## Credentials

None — Open-Meteo is a free public API that requires no authentication.

---

## Tests

```bash
# Run weather-specific tests
PYTHONPATH=. pytest tests/test_weather_collector.py -v

# Smoke test: fetch real data without LLM calls
python main.py --dry-run
```

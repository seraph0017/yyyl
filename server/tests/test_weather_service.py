import unittest
from unittest.mock import AsyncMock, patch

from services import weather_service


class WeatherServiceTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        weather_service.clear_weather_memory_cache()

    def tearDown(self):
        weather_service.clear_weather_memory_cache()

    async def test_current_weather_parses_caiyun_realtime_and_hourly(self):
        payload = {
            "status": "ok",
            "server_time": 1710000000,
            "result": {
                "realtime": {
                    "temperature": 23.6,
                    "skycon": "PARTLY_CLOUDY_DAY",
                    "humidity": 0.68,
                    "wind": {"direction": 135, "speed": 8.4},
                    "precipitation": {"local": {"intensity": 0.02}},
                },
                "minutely": {"description": "未来两小时无明显降水"},
                "hourly": {
                    "skycon": [
                        {"datetime": "2026-06-18T10:00+08:00", "value": "PARTLY_CLOUDY_DAY"},
                        {"datetime": "2026-06-18T11:00+08:00", "value": "LIGHT_RAIN"},
                    ],
                    "temperature": [
                        {"datetime": "2026-06-18T10:00+08:00", "value": 24.1},
                        {"datetime": "2026-06-18T11:00+08:00", "value": 24.8},
                    ],
                    "precipitation": [
                        {"datetime": "2026-06-18T10:00+08:00", "value": 0.0, "probability": 0.1},
                        {"datetime": "2026-06-18T11:00+08:00", "value": 0.8, "probability": 0.7},
                    ],
                },
            },
        }

        with (
            patch.object(weather_service.settings, "CAIYUN_API_TOKEN", "token"),
            patch.object(weather_service, "_request_caiyun_weather", AsyncMock(return_value=payload)),
        ):
            data = await weather_service.get_current_weather(site_id=1)

        self.assertEqual(data["weather"], "多云")
        self.assertEqual(data["icon"], "⛅")
        self.assertEqual(data["temperature"], 23.6)
        self.assertEqual(data["humidity"], 68)
        self.assertEqual(data["wind"], "东南风2级")
        self.assertEqual(data["description"], "未来两小时无明显降水")
        self.assertEqual(len(data["hourly_forecasts"]), 2)
        self.assertEqual(data["hourly_forecasts"][1]["weather"], "小雨")
        self.assertEqual(data["hourly_forecasts"][1]["precipitation_probability"], 70)

    async def test_forecast_parses_caiyun_daily_weather(self):
        payload = {
            "status": "ok",
            "result": {
                "daily": {
                    "skycon": [
                        {"date": "2026-06-18", "value": "CLEAR_DAY"},
                        {"date": "2026-06-19", "value": "MODERATE_RAIN"},
                    ],
                    "temperature": [
                        {"date": "2026-06-18", "min": 20.2, "max": 29.4},
                        {"date": "2026-06-19", "min": 19.7, "max": 25.1},
                    ],
                    "precipitation": [
                        {"date": "2026-06-18", "probability": 0.1},
                        {"date": "2026-06-19", "probability": 0.8},
                    ],
                },
            },
        }

        with (
            patch.object(weather_service.settings, "CAIYUN_API_TOKEN", "token"),
            patch.object(weather_service, "_request_caiyun_weather", AsyncMock(return_value=payload)),
        ):
            data = await weather_service.get_weather_forecast(site_id=1, days=2)

        self.assertEqual(len(data["forecasts"]), 2)
        self.assertEqual(data["forecasts"][0]["weather"], "晴")
        self.assertEqual(data["forecasts"][0]["temperature_min"], 20.2)
        self.assertEqual(data["forecasts"][1]["weather"], "中雨")
        self.assertEqual(data["forecasts"][1]["precipitation_probability"], 80)

    async def test_memory_cache_avoids_repeated_caiyun_requests(self):
        payload = {
            "status": "ok",
            "result": {
                "realtime": {
                    "temperature": 21,
                    "skycon": "CLEAR_DAY",
                    "humidity": 0.55,
                    "wind": {"direction": 90, "speed": 4},
                },
                "hourly": {},
            },
        }
        request_mock = AsyncMock(return_value=payload)

        with (
            patch.object(weather_service.settings, "CAIYUN_API_TOKEN", "token"),
            patch.object(weather_service, "_request_caiyun_weather", request_mock),
        ):
            first = await weather_service.get_current_weather(site_id=1)
            second = await weather_service.get_current_weather(site_id=1)

        self.assertEqual(first, second)
        self.assertEqual(request_mock.await_count, 1)

    async def test_missing_token_uses_fallback_weather(self):
        with patch.object(weather_service.settings, "CAIYUN_API_TOKEN", ""):
            data = await weather_service.get_current_weather(site_id=1)

        self.assertEqual(data["weather"], "多云")
        self.assertIn("hourly_forecasts", data)


if __name__ == "__main__":
    unittest.main()

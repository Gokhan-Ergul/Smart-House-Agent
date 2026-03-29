"""Weather tool (Open-Meteo) — same behavior as notebook."""

from __future__ import annotations

from typing import Any

import requests
from langchain_core.tools import tool


def create_weather_tool() -> Any:
    @tool
    def get_weather() -> str:
        """
        Hava durumu bilgisini getirir.
        WMO kodlarını insan diline çevirerek döndürür.
        """
        city_name = "Aydın"

        wmo_codes = {
            0: "Açık/Güneşli",
            1: "Çoğunlukla Açık",
            2: "Parçalı Bulutlu",
            3: "Kapalı",
            45: "Sisli",
            48: "Kırağı/Sis",
            51: "Hafif Çiseleme",
            53: "Çiseleme",
            55: "Yoğun Çiseleme",
            61: "Hafif Yağmurlu",
            63: "Yağmurlu",
            65: "Şiddetli Yağmur",
            71: "Hafif Kar Yağışlı",
            73: "Kar Yağışlı",
            75: "Yoğun Kar Yağışlı",
            77: "Kar Taneleri",
            80: "Hafif Sağanak",
            81: "Sağanak",
            82: "Şiddetli Sağanak",
            95: "Fırtına/Gök Gürültülü",
            96: "Dolu ve Fırtına",
            99: "Şiddetli Dolu ve Fırtına",
        }

        geo_url = "https://geocoding-api.open-meteo.com/v1/search"
        geo_params = {"name": city_name, "count": 1, "language": "tr", "format": "json"}

        try:
            geo_response = requests.get(geo_url, params=geo_params, timeout=30)
            geo_response.raise_for_status()
            geo_data = geo_response.json()

            if not geo_data.get("results"):
                return f"Hata: '{city_name}' bulunamadı."

            location = geo_data["results"][0]
            lat = location["latitude"]
            lon = location["longitude"]
            place_name = f"{location['name']}, {location.get('country', '')}"

        except Exception as e:
            return f"Hata (Konum): {str(e)}"

        weather_url = "https://api.open-meteo.com/v1/forecast"
        weather_params = {
            "latitude": lat,
            "longitude": lon,
            "current_weather": "true",
            "timezone": "auto",
        }

        try:
            w_response = requests.get(weather_url, params=weather_params, timeout=30)
            w_response.raise_for_status()
            w_data = w_response.json()

            current = w_data.get("current_weather", {})
            code = current.get("weathercode")

            condition_text = wmo_codes.get(code, "Bilinmiyor")

            result = {
                "konum": place_name,
                "sicaklik": f"{current.get('temperature')}°C",
                "ruzgar": f"{current.get('windspeed')} km/h",
                "durum": condition_text,
            }

            return str(result)

        except Exception as e:
            return f"Hata (Hava Durumu): {str(e)}"

    return get_weather

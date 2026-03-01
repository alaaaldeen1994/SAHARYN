import os
import logging
import datetime
from typing import List, Dict, Any
from tenacity import retry, stop_after_attempt, wait_fixed
import cdsapi
from pydantic_settings import BaseSettings

logger = logging.getLogger("WeatherIngestor")

class WeatherConfig(BaseSettings):
    ECMWF_API_URL: str = "https://cds.climate.copernicus.eu/api/v2"
    ECMWF_API_KEY: str = os.getenv("ECMWF_API_KEY", "dummy-key")
    
    class Config:
        env_file = ".env"

config = WeatherConfig()

class ECMWFWeatherIngestor:
    """
    Enterprise Weather Data Ingestor.
    Pulls high-resolution forecast ensembles for wind, temp, and humidity.
    """
    
    def __init__(self):
        self.client = cdsapi.Client(url=config.ECMWF_API_URL, key=config.ECMWF_API_KEY)

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(10))
    def ingest_forecast(self, area: List[float]):
        """
        72-hour forecast ingestion (ERA5-Land or Reanalysis-5).
        """
        now = datetime.datetime.now()
        target_file = f"data/raw/weather/forecast_{now.strftime('%Y%m%d_%H')}.grib"
        os.makedirs(os.path.dirname(target_file), exist_ok=True)

        try:
            self.client.retrieve(
                'reanalysis-era5-single-levels',
                {
                    'product_type': 'reanalysis',
                    'format': 'grib',
                    'variable': [
                        '10m_u_component_of_wind', 
                        '10m_v_component_of_wind',
                        '2m_temperature',
                        '2m_dewpoint_temperature', # For humidity calculation
                        'surface_pressure'
                    ],
                    'year': now.year,
                    'month': now.month,
                    'day': now.day,
                    'time': [f"{h:02d}:00" for h in range(24)],
                    'area': area,
                },
                target_file
            )
            logger.info(f"Weather Forecast Synchronized: {target_file}")
            return target_file
        except Exception as e:
            logger.error(f"ECMWF Synchronization Failure: {e}")
            raise

    def compute_relative_humidity(self, temp_c: float, dewpoint_c: float) -> float:
        """
        Scientific calculation of RH from temp and dewpoint.
        Used at the feature engineering layer.
        """
        import numpy as np
        rh = 100 * (np.exp((17.625 * dewpoint_c) / (243.04 + dewpoint_c)) / 
                    np.exp((17.625 * temp_c) / (243.04 + temp_c)))
        return rh

if __name__ == "__main__":
    # Integration test
    ingestor = ECMWFWeatherIngestor()
    # ingestor.ingest_forecast([40, 30, 10, 80])

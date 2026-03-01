import os
import logging
import datetime
from typing import List, Optional, Dict, Any
from tenacity import retry, stop_after_attempt, wait_exponential
import cdsapi
import ee
from pydantic_settings import BaseSettings

# Professional Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SatelliteIngestor")

class IngestionConfig(BaseSettings):
    COP_API_URL: str = os.getenv("COP_API_URL", "https://ads.atmosphere.copernicus.eu/api")
    COP_API_KEY: str = os.getenv("COP_API_KEY", "dummy-key")
    GEE_PROJECT: str = os.getenv("GEE_PROJECT", "gigafield-enterprise")
    
    class Config:
        env_file = ".env"
        extra = "ignore"  # Allow extra vars like API_SECRET in .env

config = IngestionConfig()

class SatelliteIngestor:
    """
    Enterprise Satellite Ingestor for AI Desert Resilience.
    Handles Copernicus CAMS (Dust) and NASA MODIS (AOD) via GEE.
    """
    
    def __init__(self):
        self.cams_client = cdsapi.Client(url=config.COP_API_URL, key=config.COP_API_KEY)
        try:
            ee.Initialize(project=config.GEE_PROJECT)
            logger.info("Earth Engine Initialized Successfully.")
        except Exception as e:
            logger.warning(f"GEE Initialization Failed: {e}. Check GEE_PROJECT env var.")

    @retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=4, max=60))
    def fetch_eac4_reanalysis(self, start_date: str, end_date: str):
        """
        Retrieves CAMS Global Reanalysis (EAC4) for high-fidelity historical calibration.
        """
        logger.info(f"Syncing EAC4 Satellite Reanalysis: {start_date} to {end_date}")
        target_file = f"data/raw/satellite/cams_reanalysis_{start_date}.grib"
        os.makedirs(os.path.dirname(target_file), exist_ok=True)
        
        self.cams_client.retrieve(
            'cams-global-reanalysis-eac4',
            {
                'date': [f"{start_date}/{end_date}"],
                'variable': [
                    'dust_aerosol_optical_depth_550nm',
                    'total_aerosol_optical_depth_550nm',
                ],
                'time': ['00:00', '06:00', '12:00', '18:00'],
                'data_format': 'grib',
            },
            target_file
        )
        return target_file

    @retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=4, max=60))
    def fetch_cams_forecast(self, target_date: datetime.date, area: List[float]):
        """
        Pull Global Atmospheric Composition Forecasts (Dust Aerosol Optical Depth).
        """
        logger.info(f"Initiating CAMS fetch for {target_date}...")
        
        # Area: [North, West, South, East]
        target_file = f"data/raw/satellite/cams_{target_date.isoformat()}.grib"
        os.makedirs(os.path.dirname(target_file), exist_ok=True)
        
        try:
            self.cams_client.retrieve(
                'cams-global-atmospheric-composition-forecasts',
                {
                    'date': target_date.strftime('%Y-%m-%d'),
                    'type': 'forecast',
                    'format': 'grib',
                    'variable': [
                        'dust_aerosol_optical_depth_550nm',
                        'total_aerosol_optical_depth_550nm'
                    ],
                    'leadtime_hour': [str(i) for i in range(0, 73, 3)], # 72-hour forecast
                    'area': area,
                },
                target_file
            )
            logger.info(f"CAMS Data Synced: {target_file}")
            return target_file
        except Exception as e:
            logger.error(f"CAMS Ingestion Critical Failure: {e}")
            raise

    def fetch_modis_aod(self, date_range: tuple, region: ee.Geometry):
        """
        NASA MODIS (Terra/Aqua) Aerosol Products via GEE.
        Used for historical baseline and validation.
        """
        logger.info(f"Extracting MODIS AOD for region {region.toDictionary().getInfo()}...")
        
        # MODIS/061/MCD19A2_GRN (Aerosol Optical Depth)
        collection = ee.ImageCollection("MODIS/061/MCD19A2_GRN") \
            .filterDate(date_range[0], date_range[1]) \
            .filterBounds(region) \
            .select('Optical_Depth_047')
            
        mean_aod = collection.mean()
        # Quality check: ensure we have data
        count = collection.size().getInfo()
        if count == 0:
            logger.warning("No MODIS assets found for the specified window.")
            return None
            
        logger.info(f"Aggregated {count} MODIS granules for temporal alignment.")
        return mean_aod

    @retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=4, max=60))
    def fetch_deep_atmospheric_core(self, start_date: str, end_date: str):
        """
        MASSIVE DATA RETRIEVAL: CAMS Global Reanalysis (EAC4).
        Calibrated specifically for Arabian Peninsula & Red Sea Phase 2 Pilots.
        """
        logger.info(f"Initiating Deep Atmospheric Core Sync: {start_date} to {end_date}")
        target_file = f"data/raw/satellite/cams_eac4_{start_date}.grib"
        os.makedirs(os.path.dirname(target_file), exist_ok=True)

        self.cams_client.retrieve(
            'cams-global-reanalysis-eac4',
            {
                'pressure_level': [
                    '600', '700', '800',
                    '850', '925', '950',
                    '1000'
                ],
                'date': [f"{start_date}/{end_date}"],
                'time': [
                    '00:00', '03:00', '06:00',
                    '09:00', '12:00', '15:00',
                    '18:00', '21:00'
                ],
                'data_format': 'grib',
                'variable': [
                    '10m_u_component_of_wind', '10m_v_component_of_wind', '2m_dewpoint_temperature',
                    '2m_temperature', 'dust_aerosol_optical_depth_550nm', 'particulate_matter_1um',
                    'particulate_matter_10um', 'sea_salt_aerosol_optical_depth_550nm', 'surface_geopotential',
                    'surface_pressure', 'total_aerosol_optical_depth_550nm', 'total_aerosol_optical_depth_865nm',
                    'carbon_monoxide', 'dust_aerosol_0.03-0.55um_mixing_ratio', 'dust_aerosol_0.55-0.9um_mixing_ratio',
                    'dust_aerosol_0.9-20um_mixing_ratio', 'sea_salt_aerosol_0.03-0.5um_mixing_ratio',
                    'sea_salt_aerosol_5-20um_mixing_ratio', 'specific_humidity', 'temperature',
                    'near_ir_albedo_for_diffuse_radiation', 'near_ir_albedo_for_direct_radiation', 'snow_albedo',
                    'uv_visible_albedo_for_diffuse_radiation', 'uv_visible_albedo_for_direct_radiation',
                    'relative_humidity', 'u_component_of_wind', 'v_component_of_wind'
                ],
                'area': [35, 30, 15, 65]
            },
            target_file
        )
        logger.info(f"Deep Core Sync Complete: {target_file}")
        return target_file

    def validate_ingestion_integrity(self, file_path: str) -> bool:
        """
        Scientific validation of GRIB/NetCDF outputs.
        Checks for NaNs, extreme outliers, and file corruption.
        """
        # Placeholder for xarray validation
        return os.path.exists(file_path)

if __name__ == "__main__":
    # Test block for Ingestion Pipeline
    ingestor = SatelliteIngestor()
    # middle east coordinates approximate
    # ingestor.fetch_cams_forecast(datetime.date.today(), [35, 30, 15, 60])

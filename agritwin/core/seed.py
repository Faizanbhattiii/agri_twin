"""
Database Seeder for AgriTwin Pakistan.
Populates Punjab districts, representative geometries, soil profiles,
and the Pilot Research Field in Faisalabad.
"""

import json
from datetime import date, datetime, timedelta, timezone
from typing import Optional
from sqlalchemy.orm import Session

from agritwin.core.config import settings
from agritwin.core.database import SessionLocal, init_db
from agritwin.core.models import (
    District,
    Field,
    IrrigationAdvisory,
    SatelliteReading,
    SensorTelemetry,
    SoilProfile,
    YieldForecast,
)
from agritwin.data.yields import YieldDataLoader

# Urdu district name map
URDU_NAMES = {
    "Faisalabad": "فیصل آباد", "Jhang": "جھنگ", "Toba Tek Singh": "ٹوبہ ٹیک سنگھ", "Chiniot": "چنیوٹ",
    "Sahiwal": "ساہیوال", "Okara": "اوکاڑہ", "Pakpattan": "پاکپتن",
    "Multan": "ملتان", "Khanewal": "خانیوال", "Vehari": "وہاڑی", "Lodhran": "لودھراں",
    "Bahawalpur": "بہاولپور", "Bahawalnagar": "بہاولنگر", "Rahim Yar Khan": "رحیم یار خان",
    "Sargodha": "سرگودھا", "Bhakkar": "بھکر", "Khushab": "خوشاب", "Mianwali": "میانوالی",
    "Gujranwala": "گوجرانوالہ", "Hafizabad": "حافظ آباد", "Gujarat": "گجرات", "Mandi Bahauddin": "منڈی بہاؤالدین",
    "Sialkot": "سیالکوٹ", "Narowal": "نارووال",
    "Lahore": "لاہور", "Kasur": "قصور", "Sheikhupura": "شیخوپورہ", "Nankana Sahib": "ننکانہ صاحب",
    "Dera Ghazi Khan": "ڈیرہ غازی خان", "Muzaffargarh": "مظفر گڑھ", "Layyah": "لیہ", "Rajanpur": "راجن پور",
    "Rawalpindi": "راولپنڈی", "Attock": "اٹک", "Chakwal": "چکوال", "Jhelum": "جہلم"
}


def create_district_polygon(lat: float, lon: float, delta: float = 0.25) -> dict:
    """Create a representative bounding box GeoJSON polygon for map rendering."""
    return {
        "type": "Polygon",
        "coordinates": [[
            [round(lon - delta, 4), round(lat - delta, 4)],
            [round(lon + delta, 4), round(lat - delta, 4)],
            [round(lon + delta, 4), round(lat + delta, 4)],
            [round(lon - delta, 4), round(lat + delta, 4)],
            [round(lon - delta, 4), round(lat - delta, 4)]
        ]]
    }


def seed_database(db: Optional[Session] = None) -> None:
    """Run full database seeding sequence."""
    init_db()
    session = db or SessionLocal()

    try:
        # 1. Seed Districts from Punjab CRS yield dataset
        yield_loader = YieldDataLoader()
        df_yields = yield_loader.get_all()
        unique_districts = df_yields.drop_duplicates(subset=["district"])

        for _, row in unique_districts.iterrows():
            dist_id = row["district"].lower().replace(" ", "-")
            existing = session.query(District).filter(District.id == dist_id).first()
            if not existing:
                dist = District(
                    id=dist_id,
                    name=row["district"],
                    name_ur=URDU_NAMES.get(row["district"], row["district"]),
                    division=row["division"],
                    province="Punjab",
                    centroid_lat=float(row["latitude"]),
                    centroid_lon=float(row["longitude"]),
                    geometry_geojson=create_district_polygon(float(row["latitude"]), float(row["longitude"]))
                )
                session.add(dist)
                session.flush()

                # Add baseline soil profile for district
                soil = SoilProfile(
                    district_id=dist_id,
                    texture_class="Loam",
                    clay_pct=22.0,
                    sand_pct=42.0,
                    silt_pct=36.0,
                    soc_pct=0.75,
                    ph=8.1,
                    bulk_density_g_cm3=1.42,
                    cec_cmol_kg=14.5,
                    field_capacity_pct=28.0,
                    wilting_point_pct=12.0,
                    taw_mm_per_m=160.0,
                    raw_mm_per_m=88.0,
                    source="SoilGrids-2.0"
                )
                session.add(soil)

        # 2. Seed Pilot Research Field (Faisalabad plot)
        pilot_id = settings.pilot_field_id
        existing_pilot = session.query(Field).filter(Field.id == pilot_id).first()
        if not existing_pilot:
            # 5-acre polygon in Faisalabad agricultural research area
            lat, lon = settings.pilot_latitude, settings.pilot_longitude
            delta = 0.0018  # roughly 5 acres bounding box (~200m x 100m)
            pilot_polygon = {
                "type": "Polygon",
                "coordinates": [[
                    [round(lon - delta, 5), round(lat - delta, 5)],
                    [round(lon + delta, 5), round(lat - delta, 5)],
                    [round(lon + delta, 5), round(lat + delta, 5)],
                    [round(lon - delta, 5), round(lat + delta, 5)],
                    [round(lon - delta, 5), round(lat - delta, 5)]
                ]]
            }

            pilot = Field(
                id=pilot_id,
                district_id="faisalabad",
                name="Faisalabad Wheat Pilot Plot",
                name_ur="فیصل آباد گندم ریسرچ پلاٹ",
                area_acres=settings.pilot_area_acres,
                latitude=lat,
                longitude=lon,
                boundary_geojson=pilot_polygon,
                crop_type="wheat",
                sowing_date=date(2023, 11, 10),
                is_pilot=True
            )
            session.add(pilot)
            session.flush()

            # Pilot field soil profile
            pilot_soil = SoilProfile(
                field_id=pilot_id,
                texture_class="Loam",
                clay_pct=24.0,
                sand_pct=40.0,
                silt_pct=36.0,
                soc_pct=0.85,
                ph=8.0,
                bulk_density_g_cm3=1.38,
                cec_cmol_kg=15.2,
                field_capacity_pct=29.0,
                wilting_point_pct=12.5,
                taw_mm_per_m=165.0,
                raw_mm_per_m=90.75,
                source="Field-Calibration"
            )
            session.add(pilot_soil)

            # Seed sample recent telemetry (last 24 hours of 15-min readings)
            now = datetime.now(timezone.utc)
            for i in range(24):
                ts = now - timedelta(hours=23 - i)
                # Diurnal temperature cycle
                hr = ts.hour
                temp = round(18.0 + 8.0 * ((hr - 6) / 8.0 if 6 <= hr <= 14 else (22 - hr) / 10.0), 1)
                temp = max(12.0, min(30.0, temp))
                humidity = round(70.0 - (temp - 15.0) * 1.8, 1)
                moisture = round(22.5 - i * 0.15, 1)  # slow drying curve

                telemetry = SensorTelemetry(
                    field_id=pilot_id,
                    timestamp=ts,
                    soil_moisture_pct=moisture,
                    air_temp_c=temp,
                    relative_humidity_pct=humidity,
                    soil_temp_c=round(temp - 1.5, 1),
                    battery_v=4.12,
                    source="simulated"
                )
                session.add(telemetry)

            # Seed initial advisory
            advisory = IrrigationAdvisory(
                field_id=pilot_id,
                timestamp=now,
                urgency="MONITOR",
                soil_moisture_pct=19.2,
                depletion_mm=32.0,
                recommended_depth_mm=0.0,
                tubewell_hours=0.0,
                reason_en="Soil moisture is adequate (19.2%). Next irrigation expected in 4-5 days.",
                reason_ur="زمین میں نمی مناسب ہے (19.2 فیصد)۔ اگلا پانی 4 سے 5 دن بعد متوقع ہے۔",
                disclaimer="Advisory only; verify with field conditions"
            )
            session.add(advisory)

            # Seed initial yield forecast
            forecast = YieldForecast(
                field_id=pilot_id,
                season="2023-24",
                model_name="DeepAgroNet",
                predicted_yield_kgha=3650.0,
                predicted_yield_maund_acre=36.93,
                lower_bound_kgha=3420.0,
                upper_bound_kgha=3880.0
            )
            session.add(forecast)

        session.commit()
        print("Database successfully seeded.")
    except Exception as e:
        session.rollback()
        raise e
    finally:
        if db is None:
            session.close()


if __name__ == "__main__":
    seed_database()

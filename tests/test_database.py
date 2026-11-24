"""
Unit & Integration Tests for Phase 2 Relational Data Models & Database.
Verifies SQLAlchemy 2.0 ORM models, relationships, cascades, GeoJSON handling,
and database seeding for Punjab districts and pilot field.
"""

from datetime import date, datetime, timedelta, timezone
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from agritwin.core.models import (
    Base,
    District,
    Field,
    IrrigationAdvisory,
    SatelliteReading,
    SensorTelemetry,
    SoilProfile,
    WeatherObservation,
    YieldForecast,
)
from agritwin.core.seed import seed_database


@pytest.fixture
def db_session() -> Session:
    """Create an isolated in-memory SQLite database for testing."""
    test_engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=test_engine)
    SessionTest = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)
    session = SessionTest()
    try:
        yield session
    finally:
        session.close()


def test_district_and_soil_profile_relationship(db_session: Session):
    """Verify District and 1-to-1 SoilProfile relationship."""
    dist = District(
        id="faisalabad",
        name="Faisalabad",
        division="Faisalabad",
        province="Punjab",
        centroid_lat=31.4187,
        centroid_lon=73.0791,
        geometry_geojson={"type": "Polygon", "coordinates": [[[73.0, 31.0], [73.5, 31.0], [73.5, 31.5], [73.0, 31.0]]]}
    )
    db_session.add(dist)
    db_session.flush()

    soil = SoilProfile(
        district_id="faisalabad",
        texture_class="Loam",
        clay_pct=22.0,
        sand_pct=42.0,
        silt_pct=36.0,
        soc_pct=0.75,
        ph=8.1,
        bulk_density_g_cm3=1.42,
        field_capacity_pct=28.0,
        wilting_point_pct=12.0,
        taw_mm_per_m=160.0,
        raw_mm_per_m=88.0
    )
    db_session.add(soil)
    db_session.commit()

    saved = db_session.query(District).filter_by(id="faisalabad").first()
    assert saved is not None
    assert saved.soil_profile is not None
    assert saved.soil_profile.texture_class == "Loam"
    assert saved.geometry_geojson["type"] == "Polygon"


def test_field_cascading_deletes(db_session: Session):
    """Verify that deleting a Field cascades to its telemetry, satellite, and advisories."""
    dist = District(
        id="multan",
        name="Multan",
        division="Multan",
        centroid_lat=30.1575,
        centroid_lon=71.5249
    )
    db_session.add(dist)
    db_session.flush()

    field = Field(
        id="field-multan-01",
        district_id="multan",
        name="Multan Pilot",
        area_acres=10.0,
        latitude=30.1575,
        longitude=71.5249
    )
    db_session.add(field)
    db_session.flush()

    now = datetime.now(timezone.utc)
    telemetry = SensorTelemetry(
        field_id="field-multan-01",
        timestamp=now,
        soil_moisture_pct=21.5,
        air_temp_c=24.0,
        relative_humidity_pct=65.0
    )
    advisory = IrrigationAdvisory(
        field_id="field-multan-01",
        timestamp=now,
        urgency="OPTIMAL",
        soil_moisture_pct=21.5,
        depletion_mm=10.0,
        reason_en="Moisture optimal",
        reason_ur="نمی بہترین ہے"
    )
    db_session.add_all([telemetry, advisory])
    db_session.commit()

    # Confirm created
    assert db_session.query(SensorTelemetry).count() == 1
    assert db_session.query(IrrigationAdvisory).count() == 1

    # Delete field
    db_session.delete(field)
    db_session.commit()

    # Verify cascading removal
    assert db_session.query(SensorTelemetry).count() == 0
    assert db_session.query(IrrigationAdvisory).count() == 0


def test_time_series_queries(db_session: Session):
    """Verify efficient range filtering on timestamp fields."""
    dist = District(id="sargodha", name="Sargodha", division="Sargodha", centroid_lat=32.08, centroid_lon=72.67)
    field = Field(id="field-sargodha-01", district_id="sargodha", name="Sargodha Plot", area_acres=4.0, latitude=32.08, longitude=72.67)
    db_session.add_all([dist, field])
    db_session.flush()

    base_time = datetime(2024, 1, 15, 12, 0, 0)
    for hour in range(10):
        t = SensorTelemetry(
            field_id="field-sargodha-01",
            timestamp=base_time + timedelta(hours=hour),
            soil_moisture_pct=20.0 + hour * 0.5,
            air_temp_c=18.0 + hour,
            relative_humidity_pct=50.0
        )
        db_session.add(t)
    db_session.commit()

    # Query middle 4 hours
    start_q = base_time + timedelta(hours=3)
    end_q = base_time + timedelta(hours=6)
    results = db_session.query(SensorTelemetry).filter(
        SensorTelemetry.field_id == "field-sargodha-01",
        SensorTelemetry.timestamp >= start_q,
        SensorTelemetry.timestamp <= end_q
    ).all()

    assert len(results) == 4


def test_database_seeder(db_session: Session):
    """Verify seed_database populates 36 districts and pilot field in Faisalabad."""
    seed_database(db=db_session)

    districts = db_session.query(District).all()
    assert len(districts) == 36

    pilot = db_session.query(Field).filter_by(id="pilot-faisalabad-01").first()
    assert pilot is not None
    assert pilot.district_id == "faisalabad"
    assert pilot.is_pilot is True
    assert pilot.area_acres == 5.0
    assert pilot.soil_profile is not None
    assert pilot.soil_profile.taw_mm_per_m > 100.0

    # Verify telemetry and advisory were seeded for pilot field
    telemetry_count = db_session.query(SensorTelemetry).filter_by(field_id=pilot.id).count()
    assert telemetry_count == 24

    advisories = db_session.query(IrrigationAdvisory).filter_by(field_id=pilot.id).all()
    assert len(advisories) >= 1
    assert advisories[0].urgency == "MONITOR"

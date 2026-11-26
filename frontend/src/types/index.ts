export interface District {
  id: string;
  name: string;
  name_ur: string;
  division: string;
  latitude: number;
  longitude: number;
  average_yield_kgha: number;
  average_yield_maund_acre: number;
  polygon_geojson: any;
  soil_texture: string;
  field_capacity_pct: number;
  wilting_point_pct: number;
}

export interface Field {
  id: string;
  name: string;
  district_id: string;
  district_name: string;
  area_acres: number;
  crop_type: string;
  sowing_date: string;
  latitude: number;
  longitude: number;
  polygon_geojson: any;
  soil_texture: string;
  latest_soil_moisture_pct: number;
  latest_air_temp_c: number;
  latest_humidity_pct: number;
  latest_battery_v: number;
  telemetry_source: string;
  is_simulated: boolean;
  last_reading_time: string | null;
}

export interface TelemetryReading {
  id?: number;
  field_id: string;
  timestamp: string;
  soil_moisture_pct: number;
  air_temp_c: number;
  relative_humidity_pct: number;
  soil_temp_c?: number | null;
  battery_v: number;
  source: string;
  is_simulated?: boolean;
}

export interface DailyForecast {
  date: string;
  temp_max_c: number;
  temp_min_c: number;
  temp_mean_c: number;
  humidity_pct: number;
  precipitation_mm: number;
  solar_radiation_mj: number;
  et0_mm: number;
  predicted_soil_moisture_pct: number;
}

export interface WeatherForecastResponse {
  field_id: string;
  days: DailyForecast[];
  field_capacity_pct: number;
  wilting_point_pct: number;
  raw_threshold_pct: number;
}

export interface NdviPoint {
  week: number;
  date: string;
  field_ndvi: number;
  district_normal_ndvi: number;
  growth_stage_en: string;
  growth_stage_ur: string;
}

export interface NdviResponse {
  field_id: string;
  trajectory: NdviPoint[];
  peak_ndvi: number;
  peak_week: number;
  current_week: number;
}

export interface PestRisk {
  risk_level: 'LOW' | 'MODERATE' | 'HIGH';
  pest_name_en: string;
  pest_name_ur: string;
  description_en: string;
  description_ur: string;
  action_en: string;
  action_ur: string;
}

export interface AdvisoryResponse {
  field_id: string;
  urgency: 'OPTIMAL' | 'MONITOR' | 'CRITICAL_IRRIGATE' | 'RAIN_DEFERRED';
  urgency_color: string;
  current_soil_moisture_pct: number;
  field_capacity_pct: number;
  wilting_point_pct: number;
  raw_threshold_pct: number;
  net_irrigation_needed_mm: number;
  gross_irrigation_needed_mm: number;
  tubewell_hours_per_acre: number;
  days_after_sowing: number;
  growth_stage_name_en: string;
  growth_stage_name_ur: string;
  headline_en: string;
  headline_ur: string;
  reason_en: string;
  reason_ur: string;
  action_en: string;
  action_ur: string;
  disclaimer_en: string;
  disclaimer_ur: string;
  pest_risk: PestRisk;
}

export interface ScenarioPreset {
  id: string;
  name_en: string;
  name_ur: string;
  description_en: string;
  description_ur: string;
  temp_delta_c: number;
  precip_factor: number;
  irrigation_delay_days: number;
  target_stage: string;
}

export interface ScenarioRunResponse {
  district_id: string;
  district_name: string;
  model_used: string;
  baseline_yield_kgha: number;
  scenario_yield_kgha: number;
  delta_kgha: number;
  delta_pct: number;
  baseline_yield_maund_acre: number;
  scenario_yield_maund_acre: number;
  delta_maund_acre: number;
  uncertainty_bounds?: {
    base_lower_kgha: number;
    base_upper_kgha: number;
    scen_lower_kgha: number;
    scen_upper_kgha: number;
    base_lower_maund: number;
    base_upper_maund: number;
    scen_lower_maund: number;
    scen_upper_maund: number;
    sigma_kgha: number;
  };
  stress_indices: {
    heat_stress_hours: number;
    heat_days_total: number;
    grain_filling_heat_days: number;
    water_deficit_stress_days: number;
    terminal_heat_shock_severity: string;
    drought_severity: string;
  };
  mitigation_advice_en: string;
  mitigation_advice_ur: string;
  weekly_trajectory: {
    week: number;
    baseline_temp_mean_c: number;
    scenario_temp_mean_c: number;
    baseline_precip_mm: number;
    scenario_precip_mm: number;
    baseline_ndvi: number;
    scenario_ndvi: number;
    soil_moisture_pct: number;
    water_stress_active: boolean;
  }[];
  disclaimer_en: string;
  disclaimer_ur: string;
  execution_time_ms: number;
}

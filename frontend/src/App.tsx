import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Navbar } from './components/Header/Navbar';
import { TelemetryGauges } from './components/Telemetry/TelemetryGauges';
import { DigitalTwinMap } from './components/Map/DigitalTwinMap';
import { IrrigationCard } from './components/Advisories/IrrigationCard';
import { CropHealthCharts } from './components/Charts/CropHealthCharts';
import { WhatIfPlayground } from './components/Simulator/WhatIfPlayground';
import { Footer } from './components/Footer/Footer';
import { District, Field, AdvisoryResponse, WeatherForecastResponse, NdviResponse } from './types';

export const App: React.FC = () => {
  const { t } = useTranslation();
  const [currentTab, setCurrentTab] = useState<string>('overview');

  const [districts, setDistricts] = useState<District[]>([]);
  const [selectedDistrict, setSelectedDistrict] = useState<District | null>(null);
  const [pilotField, setPilotField] = useState<Field | null>(null);

  const [advisory, setAdvisory] = useState<AdvisoryResponse | null>(null);
  const [forecast, setForecast] = useState<WeatherForecastResponse | null>(null);
  const [ndvi, setNdvi] = useState<NdviResponse | null>(null);

  const [loading, setLoading] = useState<boolean>(true);

  // Initial Load: Districts and Fields
  useEffect(() => {
    Promise.all([
      fetch('/api/v1/dashboard/districts').then((r) => r.json()),
      fetch('/api/v1/dashboard/fields').then((r) => r.json()),
    ])
      .then(([distData, fieldData]: [District[], Field[]]) => {
        setDistricts(distData);
        if (distData.length > 0) {
          // Select Faisalabad by default
          const fsd = distData.find((d) => d.id === 'faisalabad') || distData[0];
          setSelectedDistrict(fsd);
        }

        if (fieldData.length > 0) {
          setPilotField(fieldData[0]);
          loadFieldDetails(fieldData[0].id);
        }
      })
      .catch((e) => console.error('Dashboard initialization error:', e))
      .finally(() => setLoading(false));
  }, []);

  const loadFieldDetails = (fieldId: string) => {
    fetch(`/api/v1/dashboard/advisories/latest/${fieldId}`)
      .then((r) => r.json())
      .then((d) => setAdvisory(d))
      .catch((e) => console.error('Advisory fetch error:', e));

    fetch(`/api/v1/dashboard/weather/forecast/${fieldId}`)
      .then((r) => r.json())
      .then((d) => setForecast(d))
      .catch((e) => console.error('Forecast fetch error:', e));

    fetch(`/api/v1/dashboard/satellite/ndvi/${fieldId}`)
      .then((r) => r.json())
      .then((d) => setNdvi(d))
      .catch((e) => console.error('NDVI fetch error:', e));
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col justify-between text-slate-800">
      <div>
        {/* Navigation Bar */}
        <Navbar
          currentTab={currentTab}
          onTabChange={setCurrentTab}
          isSimulated={pilotField ? pilotField.is_simulated : true}
        />

        {/* Main Dashboard Container */}
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
          {/* 1. Live Telemetry Gauges Header */}
          <section id="telemetry">
            <TelemetryGauges
              fieldId={pilotField ? pilotField.id : 'pilot-faisalabad-01'}
              initialData={
                pilotField
                  ? {
                      field_id: pilotField.id,
                      timestamp: pilotField.last_reading_time || new Date().toISOString(),
                      soil_moisture_pct: pilotField.latest_soil_moisture_pct,
                      air_temp_c: pilotField.latest_air_temp_c,
                      relative_humidity_pct: pilotField.latest_humidity_pct,
                      battery_v: pilotField.latest_battery_v,
                      source: pilotField.telemetry_source,
                      is_simulated: pilotField.is_simulated,
                    }
                  : null
              }
            />
          </section>

          {/* Conditional or Tab Content */}
          {currentTab === 'map' ? (
            <section id="map-view">
              <DigitalTwinMap
                districts={districts}
                selectedDistrict={selectedDistrict}
                onSelectDistrict={setSelectedDistrict}
                pilotField={pilotField}
              />
            </section>
          ) : currentTab === 'advisory' ? (
            <section id="advisory-view" className="space-y-8">
              <IrrigationCard advisory={advisory} />
              <CropHealthCharts ndviData={ndvi} forecastData={forecast} />
            </section>
          ) : currentTab === 'simulator' ? (
            <section id="simulator-view">
              <WhatIfPlayground districtId={selectedDistrict ? selectedDistrict.id : 'faisalabad'} />
            </section>
          ) : (
            /* 'overview' Tab: Complete Integrated Digital Twin View */
            <div className="space-y-8">
              {/* Map & Advisory Row */}
              <div className="grid grid-cols-1 gap-8">
                <DigitalTwinMap
                  districts={districts}
                  selectedDistrict={selectedDistrict}
                  onSelectDistrict={setSelectedDistrict}
                  pilotField={pilotField}
                />
              </div>

              {/* Irrigation Advisory & Pest Risk */}
              <section id="advisory">
                <IrrigationCard advisory={advisory} />
              </section>

              {/* Multi-Spectral NDVI & Forecast Charts */}
              <section id="charts">
                <CropHealthCharts ndviData={ndvi} forecastData={forecast} />
              </section>

              {/* What-If Climate Playground */}
              <section id="simulator">
                <WhatIfPlayground districtId={selectedDistrict ? selectedDistrict.id : 'faisalabad'} />
              </section>
            </div>
          )}
        </main>
      </div>

      {/* Attribution & Author Footer */}
      <Footer />
    </div>
  );
};

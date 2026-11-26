import React, { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import L from 'leaflet';
import { MapPin, Layers, ZoomIn, Info, CheckCircle2 } from 'lucide-react';
import { District, Field } from '../../types';

interface DigitalTwinMapProps {
  districts: District[];
  selectedDistrict: District | null;
  onSelectDistrict: (district: District) => void;
  pilotField: Field | null;
}

export const DigitalTwinMap: React.FC<DigitalTwinMapProps> = ({
  districts,
  selectedDistrict,
  onSelectDistrict,
  pilotField,
}) => {
  const { t, i18n } = useTranslation();
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const geoJsonLayerRef = useRef<L.GeoJSON | null>(null);
  const fieldLayerRef = useRef<L.GeoJSON | null>(null);
  const markerRef = useRef<L.Marker | null>(null);

  const [activeLayer, setActiveLayer] = useState<'districts' | 'field'>('districts');

  const isUrdu = i18n.language === 'ur';

  // Initialize Map
  useEffect(() => {
    if (!mapContainerRef.current || mapInstanceRef.current) return;

    // Center on Punjab, Pakistan: ~31.17° N, 72.70° E
    const map = L.map(mapContainerRef.current, {
      center: [31.17, 72.70],
      zoom: 7,
      zoomControl: true,
      minZoom: 6,
      maxZoom: 18,
    });

    // Clean OpenStreetMap tiles
    L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
      attribution: '&copy; <a href="https://carto.com/">CARTO</a>, &copy; <a href="https://openstreetmap.org">OpenStreetMap</a>',
      maxZoom: 19,
    }).addTo(map);

    mapInstanceRef.current = map;

    return () => {
      map.remove();
      mapInstanceRef.current = null;
    };
  }, []);

  // Choropleth color ramp based on wheat yield (maund/acre)
  const getYieldColor = (maund: number) => {
    return maund > 38 ? '#15803d' : // Dark Green
           maund > 34 ? '#22c55e' : // Green
           maund > 30 ? '#84cc16' : // Light Green
           maund > 26 ? '#eab308' : // Yellow
                        '#f97316';   // Orange
  };

  // Render Districts Choropleth Layer
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map || districts.length === 0) return;

    if (geoJsonLayerRef.current) {
      geoJsonLayerRef.current.remove();
    }

    const features = districts.map((d) => ({
      type: 'Feature',
      properties: {
        id: d.id,
        name: d.name,
        name_ur: d.name_ur,
        yield_maund: d.average_yield_maund_acre,
        yield_kgha: d.average_yield_kgha,
        division: d.division,
        soil: d.soil_texture,
      },
      geometry: d.polygon_geojson,
    }));

    const geoJsonData: any = {
      type: 'FeatureCollection',
      features,
    };

    const layer = L.geoJSON(geoJsonData, {
      style: (feature: any) => {
        const isSelected = selectedDistrict?.id === feature.properties.id;
        return {
          fillColor: getYieldColor(feature.properties.yield_maund),
          weight: isSelected ? 3 : 1.5,
          opacity: 1,
          color: isSelected ? '#0f172a' : '#ffffff',
          dashArray: isSelected ? '' : '2',
          fillOpacity: isSelected ? 0.85 : 0.65,
        };
      },
      onEachFeature: (feature: any, l: L.Layer) => {
        const p = feature.properties;
        l.on({
          click: () => {
            const found = districts.find((d) => d.id === p.id);
            if (found) onSelectDistrict(found);
          },
          mouseover: (e) => {
            const target = e.target;
            target.setStyle({
              fillOpacity: 0.9,
              weight: 2.5,
            });
          },
          mouseout: (e) => {
            geoJsonLayerRef.current?.resetStyle(e.target);
          },
        });

        // Popup tooltip
        l.bindTooltip(
          `<div class="p-1 text-xs">
            <strong>${isUrdu ? p.name_ur : p.name}</strong><br/>
            Yield: ${p.yield_maund} maund/ac (${p.yield_kgha} kg/ha)<br/>
            Soil: ${p.soil}
          </div>`,
          { sticky: true }
        );
      },
    }).addTo(map);

    geoJsonLayerRef.current = layer;
  }, [districts, selectedDistrict, isUrdu]);

  // Render Pilot Field & ESP32 Node Marker
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map || !pilotField) return;

    if (fieldLayerRef.current) fieldLayerRef.current.remove();
    if (markerRef.current) markerRef.current.remove();

    // Render Field boundary polygon
    if (pilotField.polygon_geojson) {
      const fieldLayer = L.geoJSON(pilotField.polygon_geojson, {
        style: {
          color: '#059669',
          weight: 3,
          fillColor: '#10b981',
          fillOpacity: 0.45,
        },
      }).addTo(map);
      fieldLayerRef.current = fieldLayer;
    }

    // Custom Icon for ESP32 Sensor Node
    const sensorIcon = L.divIcon({
      className: 'custom-sensor-marker',
      html: `
        <div style="
          width: 30px;
          height: 30px;
          background: #10b981;
          border: 3px solid white;
          border-radius: 50%;
          box-shadow: 0 4px 10px rgba(0,0,0,0.3);
          display: flex;
          align-items: center;
          justify-content: center;
          color: white;
          font-size: 14px;
        ">
          📡
        </div>
      `,
      iconSize: [30, 30],
      iconAnchor: [15, 15],
    });

    const marker = L.marker([pilotField.latitude, pilotField.longitude], { icon: sensorIcon })
      .addTo(map)
      .bindPopup(`
        <div style="font-family: sans-serif; font-size: 12px; min-width: 170px;">
          <h4 style="font-weight: bold; margin: 0 0 4px 0; color: #0f172a;">${pilotField.name}</h4>
          <p style="margin: 0; color: #475569;">ESP32 Field Node 01</p>
          <div style="margin: 6px 0; padding: 4px; background: #ecfdf5; border-radius: 4px; color: #065f46;">
            <strong>Moisture:</strong> ${pilotField.latest_soil_moisture_pct.toFixed(1)}% Vol<br/>
            <strong>Temp:</strong> ${pilotField.latest_air_temp_c.toFixed(1)}°C
          </div>
          <span style="font-size: 10px; background: #fef3c7; color: #92400e; padding: 2px 4px; border-radius: 3px;">
            ${pilotField.is_simulated ? 'SIMULATED' : 'LIVE HARDWARE'}
          </span>
        </div>
      `);

    markerRef.current = marker;
  }, [pilotField]);

  // Zoom helpers
  const zoomToPunjab = () => {
    setActiveLayer('districts');
    mapInstanceRef.current?.setView([31.17, 72.70], 7);
  };

  const zoomToPilotField = () => {
    if (!pilotField) return;
    setActiveLayer('field');
    mapInstanceRef.current?.setView([pilotField.latitude, pilotField.longitude], 15);
    markerRef.current?.openPopup();
  };

  return (
    <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-sm">
      {/* Control bar above map */}
      <div className="p-4 border-b border-slate-100 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Layers className="w-5 h-5 text-emerald-600" />
          <h3 className="font-bold text-slate-800 text-base">{t('nav.map')}</h3>
          <span className="text-xs text-slate-500 hidden sm:inline">
            • 36 Districts of Punjab & Pilot Field
          </span>
        </div>

        {/* View mode toggles */}
        <div className="flex items-center gap-2">
          <button
            onClick={zoomToPunjab}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              activeLayer === 'districts'
                ? 'bg-emerald-600 text-white shadow-sm'
                : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
            }`}
          >
            Punjab Province
          </button>

          <button
            onClick={zoomToPilotField}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1 transition-all ${
              activeLayer === 'field'
                ? 'bg-emerald-600 text-white shadow-sm'
                : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
            }`}
          >
            <ZoomIn className="w-3.5 h-3.5" />
            Pilot Research Field
          </button>
        </div>
      </div>

      {/* Leaflet Map Canvas */}
      <div className="relative h-[460px] w-full bg-slate-100">
        <div ref={mapContainerRef} className="w-full h-full" />

        {/* Floating Map Legend */}
        <div className="absolute bottom-4 left-4 z-20 bg-white/95 backdrop-blur px-3 py-2.5 rounded-xl border border-slate-200 shadow-md text-xs">
          <span className="font-semibold text-slate-800 block mb-1.5">Wheat Yield (Maund/Acre)</span>
          <div className="flex items-center gap-1 text-[11px] text-slate-600">
            <span className="w-3 h-3 rounded-sm bg-[#f97316]" />
            <span>&lt;26</span>
            <span className="w-3 h-3 rounded-sm bg-[#eab308] ml-1.5" />
            <span>26-30</span>
            <span className="w-3 h-3 rounded-sm bg-[#84cc16] ml-1.5" />
            <span>30-34</span>
            <span className="w-3 h-3 rounded-sm bg-[#22c55e] ml-1.5" />
            <span>34-38</span>
            <span className="w-3 h-3 rounded-sm bg-[#15803d] ml-1.5" />
            <span>&gt;38</span>
          </div>
        </div>

        {/* Selected District Info Overlay */}
        {selectedDistrict && (
          <div className="absolute top-4 right-4 z-20 bg-white/95 backdrop-blur p-4 rounded-xl border border-slate-200 shadow-lg max-w-xs text-xs">
            <div className="flex items-center justify-between mb-1.5">
              <span className="font-bold text-slate-900 text-sm">
                {isUrdu ? selectedDistrict.name_ur : selectedDistrict.name}
              </span>
              <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-slate-100 text-slate-700">
                {selectedDistrict.division}
              </span>
            </div>
            <div className="space-y-1 text-slate-600">
              <div className="flex justify-between">
                <span>Avg Yield:</span>
                <span className="font-semibold text-slate-800">
                  {selectedDistrict.average_yield_maund_acre} maund/ac ({selectedDistrict.average_yield_kgha} kg/ha)
                </span>
              </div>
              <div className="flex justify-between">
                <span>Soil Texture:</span>
                <span className="font-semibold text-slate-800">{selectedDistrict.soil_texture}</span>
              </div>
              <div className="flex justify-between">
                <span>Field Capacity (FC):</span>
                <span>{selectedDistrict.field_capacity_pct}%</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

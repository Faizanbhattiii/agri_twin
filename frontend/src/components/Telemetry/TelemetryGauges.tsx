import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Droplet, Thermometer, Wind, BatteryCharging, Radio, RefreshCw, AlertTriangle } from 'lucide-react';
import { TelemetryReading } from '../../types';

interface TelemetryGaugesProps {
  initialData?: TelemetryReading | null;
  fieldId: string;
}

export const TelemetryGauges: React.FC<TelemetryGaugesProps> = ({ initialData, fieldId }) => {
  const { t } = useTranslation();
  const [telemetry, setTelemetry] = useState<TelemetryReading>(
    initialData || {
      field_id: fieldId,
      timestamp: new Date().toISOString(),
      soil_moisture_pct: 23.4,
      air_temp_c: 21.5,
      relative_humidity_pct: 56.0,
      soil_temp_c: 19.8,
      battery_v: 4.12,
      source: 'simulated',
      is_simulated: true,
    }
  );
  const [wsConnected, setWsConnected] = useState(false);

  // Sync initialData if updated from parent
  useEffect(() => {
    if (initialData) {
      setTelemetry(initialData);
    }
  }, [initialData]);

  // Connect to live WebSocket
  useEffect(() => {
    let ws: WebSocket | null = null;
    let reconnectTimeout: any = null;

    const connectWebSocket = () => {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.host}/ws/telemetry`;

      try {
        ws = new WebSocket(wsUrl);

        ws.onopen = () => {
          setWsConnected(true);
        };

        ws.onmessage = (event) => {
          try {
            const msg = JSON.parse(event.data);
            if (msg.event === 'telemetry_update' && msg.data) {
              setTelemetry({
                ...msg.data,
                is_simulated: msg.is_simulated,
              });
            }
          } catch (err) {
            console.error('WS parse error:', err);
          }
        };

        ws.onclose = () => {
          setWsConnected(false);
          // Auto reconnect every 4 seconds
          reconnectTimeout = setTimeout(connectWebSocket, 4000);
        };

        ws.onerror = () => {
          setWsConnected(false);
          ws?.close();
        };
      } catch (e) {
        setWsConnected(false);
      }
    };

    connectWebSocket();

    return () => {
      if (ws) ws.close();
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
    };
  }, [fieldId]);

  // Gauge helpers
  const getMoistureColor = (pct: number) => {
    if (pct < 16.0) return 'text-rose-600 bg-rose-50 border-rose-200';
    if (pct < 22.0) return 'text-amber-600 bg-amber-50 border-amber-200';
    return 'text-emerald-600 bg-emerald-50 border-emerald-200';
  };

  const getBatteryPct = (v: number) => {
    // 3.2V (0%) to 4.2V (100%) Li-ion
    const pct = Math.round(((v - 3.2) / (4.2 - 3.2)) * 100);
    return Math.max(5, Math.min(100, pct));
  };

  const isSimulated = telemetry.source === 'simulated' || telemetry.is_simulated !== false;

  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
      {/* Header with Live Status & Badge */}
      <div className="flex flex-wrap items-center justify-between gap-3 mb-6 pb-4 border-b border-slate-100">
        <div>
          <div className="flex items-center gap-2">
            <Radio className={`w-5 h-5 ${wsConnected ? 'text-emerald-500 animate-pulse' : 'text-slate-400'}`} />
            <h3 className="font-bold text-slate-800 text-base">{t('telemetry.live_heading')}</h3>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Node ID: <span className="font-mono text-slate-700 font-semibold">{telemetry.field_id}</span> •{' '}
            {t('telemetry.last_updated')}:{' '}
            <span className="font-medium text-slate-700">
              {new Date(telemetry.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
            </span>
          </p>
        </div>

        {/* Status Badges */}
        <div className="flex items-center gap-2">
          {isSimulated ? (
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-amber-100 text-amber-900 border border-amber-300 shadow-sm animate-pulse">
              <AlertTriangle className="w-3.5 h-3.5 text-amber-700" />
              {t('badge.simulated')}
            </span>
          ) : (
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800 border border-emerald-300 shadow-sm">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-ping" />
              {t('badge.hardware')}
            </span>
          )}

          <div className={`px-2.5 py-1 rounded-full text-xs font-medium border flex items-center gap-1.5 ${
            wsConnected ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-slate-100 text-slate-600 border-slate-200'
          }`}>
            <span className={`w-2 h-2 rounded-full ${wsConnected ? 'bg-emerald-500' : 'bg-slate-400'}`} />
            {wsConnected ? 'WebSocket Live' : 'Polling'}
          </div>
        </div>
      </div>

      {/* 4 Telemetry Gauges */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Soil Moisture */}
        <div className={`p-4 rounded-xl border transition-all ${getMoistureColor(telemetry.soil_moisture_pct)}`}>
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-600">
              {t('telemetry.soil_moisture')}
            </span>
            <Droplet className="w-5 h-5 opacity-80" />
          </div>
          <div className="flex items-baseline gap-1">
            <span className="text-3xl font-extrabold tracking-tight">{telemetry.soil_moisture_pct.toFixed(1)}</span>
            <span className="text-sm font-bold">% Vol</span>
          </div>
          <div className="w-full bg-slate-200/60 rounded-full h-1.5 mt-3 overflow-hidden">
            <div
              className="bg-current h-full rounded-full transition-all duration-500"
              style={{ width: `${Math.min(100, (telemetry.soil_moisture_pct / 35.0) * 100)}%` }}
            />
          </div>
          <div className="flex justify-between text-[10px] text-slate-500 mt-1 font-mono">
            <span>WP: 12%</span>
            <span>RAW: 19%</span>
            <span>FC: 28%</span>
          </div>
        </div>

        {/* Air Temperature */}
        <div className="p-4 rounded-xl border border-slate-200 bg-orange-50/50 text-orange-950">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-600">
              {t('telemetry.air_temp')}
            </span>
            <Thermometer className="w-5 h-5 text-orange-600" />
          </div>
          <div className="flex items-baseline gap-1">
            <span className="text-3xl font-extrabold text-orange-700 tracking-tight">
              {telemetry.air_temp_c.toFixed(1)}
            </span>
            <span className="text-sm font-bold text-orange-600">°C</span>
          </div>
          <div className="text-xs text-slate-500 mt-3 flex items-center justify-between">
            <span>Soil Temp:</span>
            <span className="font-semibold text-slate-700">
              {telemetry.soil_temp_c ? `${telemetry.soil_temp_c.toFixed(1)}°C` : '19.5°C'}
            </span>
          </div>
        </div>

        {/* Relative Humidity */}
        <div className="p-4 rounded-xl border border-slate-200 bg-sky-50/50 text-sky-950">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-600">
              {t('telemetry.humidity')}
            </span>
            <Wind className="w-5 h-5 text-sky-600" />
          </div>
          <div className="flex items-baseline gap-1">
            <span className="text-3xl font-extrabold text-sky-700 tracking-tight">
              {telemetry.relative_humidity_pct.toFixed(0)}
            </span>
            <span className="text-sm font-bold text-sky-600">% RH</span>
          </div>
          <div className="w-full bg-sky-200/60 rounded-full h-1.5 mt-3 overflow-hidden">
            <div
              className="bg-sky-500 h-full rounded-full transition-all duration-500"
              style={{ width: `${Math.min(100, telemetry.relative_humidity_pct)}%` }}
            />
          </div>
          <p className="text-[10px] text-slate-500 mt-1">Canopy Microclimate</p>
        </div>

        {/* Battery & Solar */}
        <div className="p-4 rounded-xl border border-slate-200 bg-slate-50 text-slate-900">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-600">
              {t('telemetry.battery')}
            </span>
            <BatteryCharging className="w-5 h-5 text-emerald-600" />
          </div>
          <div className="flex items-baseline gap-1">
            <span className="text-3xl font-extrabold text-slate-800 tracking-tight">
              {telemetry.battery_v.toFixed(2)}
            </span>
            <span className="text-sm font-bold text-slate-600">V</span>
          </div>
          <div className="w-full bg-slate-200 rounded-full h-1.5 mt-3 overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-500 ${
                telemetry.battery_v > 3.7 ? 'bg-emerald-500' : 'bg-amber-500'
              }`}
              style={{ width: `${getBatteryPct(telemetry.battery_v)}%` }}
            />
          </div>
          <div className="flex justify-between text-[10px] text-slate-500 mt-1">
            <span>Charge: ~{getBatteryPct(telemetry.battery_v)}%</span>
            <span>Solar Normal</span>
          </div>
        </div>
      </div>
    </div>
  );
};

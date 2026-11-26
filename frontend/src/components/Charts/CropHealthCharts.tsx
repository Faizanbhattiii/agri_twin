import React from 'react';
import { useTranslation } from 'react-i18next';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js';
import { Line, Bar } from 'react-chartjs-2';
import { Satellite, CloudSun, TrendingUp, Sparkles } from 'lucide-react';
import { NdviResponse, WeatherForecastResponse } from '../../types';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

interface CropHealthChartsProps {
  ndviData: NdviResponse | null;
  forecastData: WeatherForecastResponse | null;
}

export const CropHealthCharts: React.FC<CropHealthChartsProps> = ({ ndviData, forecastData }) => {
  const { t, i18n } = useTranslation();
  const isUrdu = i18n.language === 'ur';

  // 1. NDVI Trajectory Chart Setup
  const ndviLabels = ndviData ? ndviData.trajectory.map((p) => `W${p.week}`) : [];
  const fieldNdviValues = ndviData ? ndviData.trajectory.map((p) => p.field_ndvi) : [];
  const districtNdviValues = ndviData ? ndviData.trajectory.map((p) => p.district_normal_ndvi) : [];

  const ndviChartData = {
    labels: ndviLabels,
    datasets: [
      {
        label: t('charts.ndvi_field'),
        data: fieldNdviValues,
        borderColor: '#10b981', // Emerald 500
        backgroundColor: 'rgba(16, 185, 129, 0.15)',
        borderWidth: 2.5,
        pointRadius: 2.5,
        fill: true,
        tension: 0.35,
      },
      {
        label: t('charts.ndvi_normal'),
        data: districtNdviValues,
        borderColor: '#94a3b8', // Slate 400
        borderWidth: 1.8,
        borderDash: [5, 4],
        pointRadius: 0,
        fill: false,
        tension: 0.35,
      },
    ],
  };

  const ndviChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top' as const,
        labels: { boxWidth: 12, font: { size: 11 } },
      },
      tooltip: {
        callbacks: {
          afterLabel: (context: any) => {
            const idx = context.dataIndex;
            if (ndviData && ndviData.trajectory[idx]) {
              const pt = ndviData.trajectory[idx];
              return `Stage: ${isUrdu ? pt.growth_stage_ur : pt.growth_stage_en}`;
            }
            return '';
          },
        },
      },
    },
    scales: {
      y: {
        min: 0.1,
        max: 0.9,
        title: { display: true, text: 'NDVI (0 to 1.0)', font: { size: 11 } },
      },
      x: {
        title: { display: true, text: 'Season Week (Nov 1 to May 10)', font: { size: 11 } },
      },
    },
  };

  // 2. Weather & Moisture Forecast Chart Setup
  const forecastLabels = forecastData ? forecastData.days.map((d) => d.date.slice(5)) : [];
  const moistureValues = forecastData ? forecastData.days.map((d) => d.predicted_soil_moisture_pct) : [];
  const precipValues = forecastData ? forecastData.days.map((d) => d.precipitation_mm) : [];
  const et0Values = forecastData ? forecastData.days.map((d) => d.et0_mm) : [];

  const weatherChartData = {
    labels: forecastLabels,
    datasets: [
      {
        type: 'line' as const,
        label: t('charts.soil_pred'),
        data: moistureValues,
        borderColor: '#0284c7', // Sky 600
        backgroundColor: 'rgba(2, 132, 199, 0.12)',
        borderWidth: 2.5,
        fill: true,
        tension: 0.3,
        yAxisID: 'y_moisture',
      },
      {
        type: 'bar' as const,
        label: t('charts.precip_label'),
        data: precipValues,
        backgroundColor: 'rgba(56, 189, 248, 0.7)',
        borderRadius: 4,
        yAxisID: 'y_precip',
      },
      {
        type: 'line' as const,
        label: t('charts.et0_label'),
        data: et0Values,
        borderColor: '#f97316', // Orange 500
        borderDash: [4, 3],
        pointRadius: 3,
        fill: false,
        tension: 0.3,
        yAxisID: 'y_precip',
      },
    ],
  };

  const weatherChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top' as const,
        labels: { boxWidth: 12, font: { size: 11 } },
      },
    },
    scales: {
      y_moisture: {
        type: 'linear' as const,
        display: true,
        position: 'left' as const,
        min: 10,
        max: 32,
        title: { display: true, text: 'Soil Moisture (% Vol)', font: { size: 11 } },
      },
      y_precip: {
        type: 'linear' as const,
        display: true,
        position: 'right' as const,
        min: 0,
        max: 15,
        grid: { drawOnChartArea: false },
        title: { display: true, text: 'Rain & ET0 (mm/day)', font: { size: 11 } },
      },
    },
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* 1. Sentinel-2 NDVI Curve */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
        <div className="flex items-center justify-between mb-4 pb-3 border-b border-slate-100">
          <div className="flex items-center gap-2">
            <Satellite className="w-5 h-5 text-emerald-600" />
            <h3 className="font-bold text-slate-800 text-sm sm:text-base">
              {t('charts.ndvi_title')}
            </h3>
          </div>
          {ndviData && (
            <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
              Peak: {ndviData.peak_ndvi} (W{ndviData.peak_week})
            </span>
          )}
        </div>

        <div className="h-[280px] w-full">
          <Line data={ndviChartData} options={ndviChartOptions} />
        </div>

        <div className="flex justify-between items-center text-[11px] text-slate-400 mt-3 pt-2 border-t border-slate-100">
          <span>Copernicus Sentinel-2 Level-2A 10m Resolution</span>
          <span className="font-medium text-slate-600">Current Week: W{ndviData?.current_week || 16}</span>
        </div>
      </div>

      {/* 2. 7-Day Weather & Soil Moisture Forecast */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
        <div className="flex items-center justify-between mb-4 pb-3 border-b border-slate-100">
          <div className="flex items-center gap-2">
            <CloudSun className="w-5 h-5 text-sky-600" />
            <h3 className="font-bold text-slate-800 text-sm sm:text-base">
              {t('charts.weather_title')}
            </h3>
          </div>
          <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-sky-50 text-sky-700 border border-sky-200">
            Open-Meteo & FAO-56
          </span>
        </div>

        <div className="h-[280px] w-full">
          {/* @ts-ignore */}
          <Bar data={weatherChartData} options={weatherChartOptions} />
        </div>

        <div className="flex justify-between items-center text-[11px] text-slate-500 mt-3 pt-2 border-t border-slate-100 font-mono">
          <span>FC: 28%</span>
          <span className="text-amber-600 font-semibold">RAW Stress Threshold: 19%</span>
          <span>WP: 12%</span>
        </div>
      </div>
    </div>
  );
};

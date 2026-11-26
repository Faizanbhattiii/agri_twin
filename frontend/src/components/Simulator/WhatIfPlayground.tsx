import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Sliders, Play, AlertTriangle, Flame, Droplets, ShieldCheck, Sparkles, Clock, Check } from 'lucide-react';
import { ScenarioPreset, ScenarioRunResponse } from '../../types';

interface WhatIfPlaygroundProps {
  districtId: string;
}

export const WhatIfPlayground: React.FC<WhatIfPlaygroundProps> = ({ districtId }) => {
  const { t, i18n } = useTranslation();
  const isUrdu = i18n.language === 'ur';

  const [presets, setPresets] = useState<ScenarioPreset[]>([]);
  const [selectedPresetId, setSelectedPresetId] = useState<string>('baseline');

  // Sliders state
  const [tempDelta, setTempDelta] = useState<number>(0.0);
  const [precipFactor, setPrecipFactor] = useState<number>(1.0);
  const [irrigationDelay, setIrrigationDelay] = useState<number>(0);
  const [targetStage, setTargetStage] = useState<string>('all');
  const [modelName, setModelName] = useState<string>('deepagronet');

  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [result, setResult] = useState<ScenarioRunResponse | null>(null);

  // Fetch presets
  useEffect(() => {
    fetch('/api/v1/scenarios/presets')
      .then((res) => res.json())
      .then((data: ScenarioPreset[]) => {
        setPresets(data);
      })
      .catch((err) => console.error('Failed to load scenario presets:', err));
  }, []);

  // Run initial baseline scenario
  useEffect(() => {
    runSimulation(0.0, 1.0, 0, 'all', 'deepagronet');
  }, [districtId]);

  const applyPreset = (preset: ScenarioPreset) => {
    setSelectedPresetId(preset.id);
    setTempDelta(preset.temp_delta_c);
    setPrecipFactor(preset.precip_factor);
    setIrrigationDelay(preset.irrigation_delay_days);
    setTargetStage(preset.target_stage);
    runSimulation(preset.temp_delta_c, preset.precip_factor, preset.irrigation_delay_days, preset.target_stage, modelName);
  };

  const runSimulation = async (
    tDelta = tempDelta,
    pFactor = precipFactor,
    iDelay = irrigationDelay,
    tStage = targetStage,
    mName = modelName
  ) => {
    setIsLoading(true);
    try {
      const resp = await fetch('/api/v1/scenarios/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          district_id: districtId,
          temp_delta_c: tDelta,
          precip_factor: pFactor,
          irrigation_delay_days: iDelay,
          target_stage: tStage,
          model_name: mName,
        }),
      });
      const data = await resp.json();
      setResult(data);
    } catch (e) {
      console.error('Simulation error:', e);
    } finally {
      setIsLoading(false);
    }
  };

  const getSeverityBadge = (level: string) => {
    switch (level) {
      case 'EXTREME':
        return 'bg-purple-100 text-purple-900 border-purple-300';
      case 'SEVERE':
        return 'bg-rose-100 text-rose-800 border-rose-300';
      case 'MODERATE':
        return 'bg-amber-100 text-amber-800 border-amber-300';
      case 'MILD':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      default:
        return 'bg-emerald-100 text-emerald-800 border-emerald-300';
    }
  };

  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
      {/* Title */}
      <div className="mb-6 pb-4 border-b border-slate-100 flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <Sliders className="w-5 h-5 text-emerald-600" />
            <h3 className="font-bold text-slate-900 text-base sm:text-lg">{t('simulator.title')}</h3>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">{t('simulator.subtitle')}</p>
        </div>

        {result && (
          <span className="text-xs font-mono font-medium text-slate-500 bg-slate-100 px-3 py-1 rounded-full flex items-center gap-1.5">
            <Clock className="w-3.5 h-3.5 text-slate-400" />
            Simulated in {result.execution_time_ms} ms
          </span>
        )}
      </div>

      {/* Preset Scenario Quick-Select Pills */}
      <div className="mb-6">
        <label className="text-xs font-bold text-slate-700 uppercase tracking-wider block mb-2">
          {t('simulator.presets')}
        </label>
        <div className="flex flex-wrap gap-2">
          {presets.map((preset) => {
            const isSelected = selectedPresetId === preset.id;
            return (
              <button
                key={preset.id}
                onClick={() => applyPreset(preset)}
                className={`px-3 py-1.5 rounded-xl text-xs font-medium border transition-all ${
                  isSelected
                    ? 'bg-emerald-600 text-white border-emerald-600 shadow-sm'
                    : 'bg-slate-50 text-slate-700 border-slate-200 hover:bg-slate-100'
                }`}
              >
                {isUrdu ? preset.name_ur : preset.name_en}
              </button>
            );
          })}
        </div>
      </div>

      {/* Main Grid: Controls vs Results */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left Column: Interactive Sliders (5 Cols) */}
        <div className="lg:col-span-5 space-y-5 bg-slate-50/80 p-5 rounded-xl border border-slate-200/80">
          {/* Slider 1: Temperature Offset */}
          <div>
            <div className="flex justify-between items-center text-xs font-semibold text-slate-700 mb-1.5">
              <span className="flex items-center gap-1.5">
                <Flame className="w-4 h-4 text-orange-500" />
                {t('simulator.temp_slider')}
              </span>
              <span className="font-mono text-sm px-2 py-0.5 rounded bg-orange-100 text-orange-800 font-bold">
                {tempDelta >= 0 ? `+${tempDelta.toFixed(1)}` : tempDelta.toFixed(1)}°C
              </span>
            </div>
            <input
              type="range"
              min="-2.0"
              max="6.0"
              step="0.5"
              value={tempDelta}
              onChange={(e) => {
                setSelectedPresetId('custom');
                setTempDelta(parseFloat(e.target.value));
              }}
              className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-orange-600"
            />
            <div className="flex justify-between text-[10px] text-slate-400 mt-1 font-mono">
              <span>-2°C</span>
              <span>Baseline (0°C)</span>
              <span>+6°C</span>
            </div>
          </div>

          {/* Slider 2: Precipitation Multiplier */}
          <div>
            <div className="flex justify-between items-center text-xs font-semibold text-slate-700 mb-1.5">
              <span className="flex items-center gap-1.5">
                <Droplets className="w-4 h-4 text-sky-500" />
                {t('simulator.precip_slider')}
              </span>
              <span className="font-mono text-sm px-2 py-0.5 rounded bg-sky-100 text-sky-800 font-bold">
                {precipFactor.toFixed(2)}x ({Math.round((precipFactor - 1.0) * 100)}%)
              </span>
            </div>
            <input
              type="range"
              min="0.0"
              max="2.5"
              step="0.1"
              value={precipFactor}
              onChange={(e) => {
                setSelectedPresetId('custom');
                setPrecipFactor(parseFloat(e.target.value));
              }}
              className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-sky-600"
            />
            <div className="flex justify-between text-[10px] text-slate-400 mt-1 font-mono">
              <span>0.0x (Drought)</span>
              <span>1.0x (Normal)</span>
              <span>2.5x (Heavy Rain)</span>
            </div>
          </div>

          {/* Slider 3: Irrigation Delay */}
          <div>
            <div className="flex justify-between items-center text-xs font-semibold text-slate-700 mb-1.5">
              <span className="flex items-center gap-1.5">
                <Clock className="w-4 h-4 text-amber-500" />
                {t('simulator.delay_slider')}
              </span>
              <span className="font-mono text-sm px-2 py-0.5 rounded bg-amber-100 text-amber-800 font-bold">
                +{irrigationDelay} Days
              </span>
            </div>
            <input
              type="range"
              min="0"
              max="28"
              step="7"
              value={irrigationDelay}
              onChange={(e) => {
                setSelectedPresetId('custom');
                setIrrigationDelay(parseInt(e.target.value));
              }}
              className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-amber-600"
            />
            <div className="flex justify-between text-[10px] text-slate-400 mt-1 font-mono">
              <span>0d (On Time)</span>
              <span>+7d</span>
              <span>+14d</span>
              <span>+21d</span>
              <span>+28d</span>
            </div>
          </div>

          {/* Model and Stage Selectors */}
          <div className="grid grid-cols-2 gap-3 pt-2">
            <div>
              <label className="text-[11px] font-semibold text-slate-600 block mb-1">
                {t('simulator.stage_select')}
              </label>
              <select
                value={targetStage}
                onChange={(e) => setTargetStage(e.target.value)}
                className="w-full text-xs font-medium bg-white border border-slate-300 rounded-lg p-2 focus:ring-1 focus:ring-emerald-500"
              >
                <option value="all">Whole Season (نومبر تا مئی)</option>
                <option value="grain_filling">March Grain-Filling (دانہ بھرائی)</option>
                <option value="flowering">Anthesis / Flowering (پھول آنا)</option>
                <option value="late_season">Late Ripening (پکاؤ کا مرحلہ)</option>
              </select>
            </div>

            <div>
              <label className="text-[11px] font-semibold text-slate-600 block mb-1">
                {t('simulator.model_select')}
              </label>
              <select
                value={modelName}
                onChange={(e) => setModelName(e.target.value)}
                className="w-full text-xs font-medium bg-white border border-slate-300 rounded-lg p-2 focus:ring-1 focus:ring-emerald-500"
              >
                <option value="deepagronet">DeepAgroNet (BiLSTM + Attn + NLL)</option>
                <option value="random_forest">Random Forest Baseline</option>
                <option value="xgboost">XGBoost Baseline</option>
              </select>
            </div>
          </div>

          {/* Run Button */}
          <button
            onClick={() => runSimulation()}
            disabled={isLoading}
            className="w-full mt-2 py-2.5 px-4 rounded-xl font-bold text-sm text-white bg-emerald-600 hover:bg-emerald-700 shadow-md shadow-emerald-600/20 flex items-center justify-center gap-2 transition-all disabled:opacity-50"
          >
            {isLoading ? (
              <span>{t('simulator.running')}</span>
            ) : (
              <>
                <Play className="w-4 h-4 fill-current" />
                <span>{t('simulator.run_btn')}</span>
              </>
            )}
          </button>
        </div>

        {/* Right Column: Output Metrics & Stress Indices (7 Cols) */}
        <div className="lg:col-span-7 flex flex-col justify-between space-y-5">
          {result ? (
            <>
              {/* Primary Yield Comparison Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                {/* Baseline Yield */}
                <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
                  <span className="text-xs text-slate-500 font-medium block mb-1">
                    {t('simulator.baseline_yield')}
                  </span>
                  <div className="flex items-baseline gap-1">
                    <span className="text-2xl font-black text-slate-800">
                      {result.baseline_yield_maund_acre.toFixed(1)}
                    </span>
                    <span className="text-xs font-bold text-slate-500">maund/ac</span>
                  </div>
                  <p className="text-[11px] text-slate-400 mt-0.5">({result.baseline_yield_kgha.toFixed(0)} kg/ha)</p>
                </div>

                {/* Simulated Yield */}
                <div className="p-4 rounded-xl bg-emerald-50/70 border border-emerald-200">
                  <span className="text-xs text-emerald-800 font-medium block mb-1">
                    {t('simulator.scenario_yield')}
                  </span>
                  <div className="flex items-baseline gap-1">
                    <span className="text-2xl font-black text-emerald-900">
                      {result.scenario_yield_maund_acre.toFixed(1)}
                    </span>
                    <span className="text-xs font-bold text-emerald-700">maund/ac</span>
                  </div>
                  <p className="text-[11px] text-emerald-600 mt-0.5">({result.scenario_yield_kgha.toFixed(0)} kg/ha)</p>
                </div>

                {/* Delta Yield % */}
                <div className={`p-4 rounded-xl border ${
                  result.delta_pct >= 0 ? 'bg-emerald-50 border-emerald-200 text-emerald-900' : 'bg-rose-50 border-rose-200 text-rose-900'
                }`}>
                  <span className="text-xs font-medium block mb-1 opacity-80">
                    {t('simulator.yield_delta')}
                  </span>
                  <div className="flex items-baseline gap-1">
                    <span className="text-2xl font-black">
                      {result.delta_pct >= 0 ? `+${result.delta_pct.toFixed(1)}` : result.delta_pct.toFixed(1)}%
                    </span>
                  </div>
                  <p className="text-[11px] opacity-75 mt-0.5">
                    {result.delta_maund_acre >= 0 ? `+${result.delta_maund_acre.toFixed(1)}` : result.delta_maund_acre.toFixed(1)} maund/ac
                  </p>
                </div>
              </div>

              {/* Uncertainty Bounds if DeepAgroNet */}
              {result.uncertainty_bounds && (
                <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 text-xs flex items-center justify-between">
                  <span className="text-slate-500 font-medium">95% Calibrated Prediction Interval:</span>
                  <span className="font-mono font-semibold text-slate-800">
                    {result.uncertainty_bounds.scen_lower_maund.toFixed(1)} – {result.uncertainty_bounds.scen_upper_maund.toFixed(1)} maund/acre
                  </span>
                </div>
              )}

              {/* Stress Severity Badges & Indexes */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="p-3 bg-white rounded-xl border border-slate-200">
                  <span className="text-[11px] text-slate-500 block mb-0.5">Heat Hours (&gt;32°C)</span>
                  <span className="text-lg font-bold text-orange-700">{result.stress_indices.heat_stress_hours} hrs</span>
                </div>

                <div className="p-3 bg-white rounded-xl border border-slate-200">
                  <span className="text-[11px] text-slate-500 block mb-0.5">Water Deficit Days</span>
                  <span className="text-lg font-bold text-sky-700">{result.stress_indices.water_deficit_stress_days} days</span>
                </div>

                <div className="p-3 bg-white rounded-xl border border-slate-200">
                  <span className="text-[11px] text-slate-500 block mb-0.5">{t('simulator.heat_severity')}</span>
                  <span className={`inline-block px-2 py-0.5 text-[11px] font-bold rounded border ${getSeverityBadge(result.stress_indices.terminal_heat_shock_severity)}`}>
                    {result.stress_indices.terminal_heat_shock_severity}
                  </span>
                </div>

                <div className="p-3 bg-white rounded-xl border border-slate-200">
                  <span className="text-[11px] text-slate-500 block mb-0.5">{t('simulator.drought_severity')}</span>
                  <span className={`inline-block px-2 py-0.5 text-[11px] font-bold rounded border ${getSeverityBadge(result.stress_indices.drought_severity)}`}>
                    {result.stress_indices.drought_severity}
                  </span>
                </div>
              </div>

              {/* Agronomic Mitigation Guidance */}
              <div className="p-4 rounded-xl bg-emerald-50/50 border border-emerald-200/80 text-xs">
                <div className="flex items-center gap-1.5 font-bold text-emerald-900 mb-1.5">
                  <ShieldCheck className="w-4 h-4 text-emerald-600" />
                  <span>{t('simulator.mitigation_advice')}</span>
                </div>
                <p className="text-emerald-950 leading-relaxed font-medium">
                  {isUrdu ? result.mitigation_advice_ur : result.mitigation_advice_en}
                </p>
              </div>
            </>
          ) : (
            <div className="h-full flex items-center justify-center p-8 text-center text-slate-400">
              Run a scenario to see projected impacts.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

import React from 'react';
import { useTranslation } from 'react-i18next';
import { AlertCircle, Clock, Droplets, Bug, ShieldAlert, Sparkles, Sprout } from 'lucide-react';
import { AdvisoryResponse } from '../../types';

interface IrrigationCardProps {
  advisory: AdvisoryResponse | null;
}

export const IrrigationCard: React.FC<IrrigationCardProps> = ({ advisory }) => {
  const { t, i18n } = useTranslation();
  const isUrdu = i18n.language === 'ur';

  if (!advisory) {
    return (
      <div className="bg-white rounded-2xl border border-slate-200 p-8 text-center text-slate-500">
        Loading agricultural advisories...
      </div>
    );
  }

  // Visual styling based on urgency status
  const urgencyStyles = {
    OPTIMAL: {
      border: 'border-emerald-300',
      bg: 'bg-emerald-50/60',
      badge: 'bg-emerald-100 text-emerald-800 border-emerald-300',
      glow: 'shadow-emerald-500/10',
      iconColor: 'text-emerald-600',
    },
    MONITOR: {
      border: 'border-amber-300',
      bg: 'bg-amber-50/60',
      badge: 'bg-amber-100 text-amber-800 border-amber-300',
      glow: 'shadow-amber-500/10',
      iconColor: 'text-amber-600',
    },
    CRITICAL_IRRIGATE: {
      border: 'border-rose-400',
      bg: 'bg-rose-50/70',
      badge: 'bg-rose-100 text-rose-800 border-rose-300 animate-pulse',
      glow: 'shadow-rose-500/15',
      iconColor: 'text-rose-600',
    },
    RAIN_DEFERRED: {
      border: 'border-sky-300',
      bg: 'bg-sky-50/60',
      badge: 'bg-sky-100 text-sky-800 border-sky-300',
      glow: 'shadow-sky-500/10',
      iconColor: 'text-sky-600',
    },
  }[advisory.urgency] || {
    border: 'border-slate-200',
    bg: 'bg-slate-50',
    badge: 'bg-slate-100 text-slate-700 border-slate-200',
    glow: '',
    iconColor: 'text-slate-600',
  };

  const pestRiskStyles = {
    HIGH: 'bg-rose-100 text-rose-800 border-rose-300',
    MODERATE: 'bg-amber-100 text-amber-800 border-amber-300',
    LOW: 'bg-emerald-100 text-emerald-800 border-emerald-300',
  }[advisory.pest_risk.risk_level] || 'bg-slate-100 text-slate-700';

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* 1. Main Irrigation Advisory Card (Span 2) */}
      <div className={`lg:col-span-2 rounded-2xl border p-6 shadow-sm transition-all ${urgencyStyles.border} ${urgencyStyles.bg} ${urgencyStyles.glow}`}>
        {/* Top Header */}
        <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
          <div className="flex items-center gap-2">
            <Droplets className={`w-6 h-6 ${urgencyStyles.iconColor}`} />
            <div>
              <h3 className="font-bold text-slate-900 text-lg">
                {isUrdu ? advisory.headline_ur : advisory.headline_en}
              </h3>
              <p className="text-xs text-slate-600 flex items-center gap-1.5 mt-0.5">
                <Sprout className="w-3.5 h-3.5 text-emerald-600" />
                <span>
                  {isUrdu ? advisory.growth_stage_name_ur : advisory.growth_stage_name_en}
                </span>
                <span>• DAS: {advisory.days_after_sowing}</span>
              </p>
            </div>
          </div>

          <span className={`px-3 py-1 rounded-full text-xs font-bold border ${urgencyStyles.badge}`}>
            {advisory.urgency}
          </span>
        </div>

        {/* Action Callout Box */}
        <div className="bg-white/90 backdrop-blur rounded-xl p-4 border border-slate-200 shadow-sm mb-5">
          <p className="text-sm font-semibold text-slate-800 mb-1 leading-relaxed">
            {isUrdu ? advisory.action_ur : advisory.action_en}
          </p>
          <p className="text-xs text-slate-600 leading-relaxed">
            {isUrdu ? advisory.reason_ur : advisory.reason_en}
          </p>
        </div>

        {/* Agronomic Numerical Quantities */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-5">
          {/* Tubewell runtime */}
          <div className="bg-white p-3 rounded-xl border border-slate-200 shadow-xs">
            <div className="flex items-center gap-1.5 text-xs text-slate-500 mb-1">
              <Clock className="w-3.5 h-3.5 text-emerald-600" />
              <span>1-Cusec Tubewell</span>
            </div>
            <div className="flex items-baseline gap-1">
              <span className="text-2xl font-black text-slate-900">
                {advisory.tubewell_hours_per_acre.toFixed(1)}
              </span>
              <span className="text-xs font-bold text-slate-600">hrs/acre</span>
            </div>
            <p className="text-[10px] text-slate-400 mt-0.5">Standard 102 m³/hr</p>
          </div>

          {/* Gross depth */}
          <div className="bg-white p-3 rounded-xl border border-slate-200 shadow-xs">
            <div className="flex items-center gap-1.5 text-xs text-slate-500 mb-1">
              <Droplets className="w-3.5 h-3.5 text-sky-600" />
              <span>Gross Depth</span>
            </div>
            <div className="flex items-baseline gap-1">
              <span className="text-2xl font-black text-slate-900">
                {advisory.gross_irrigation_needed_mm.toFixed(0)}
              </span>
              <span className="text-xs font-bold text-slate-600">mm</span>
            </div>
            <p className="text-[10px] text-slate-400 mt-0.5">Application eff. ~75%</p>
          </div>

          {/* Current moisture */}
          <div className="bg-white p-3 rounded-xl border border-slate-200 shadow-xs">
            <span className="text-xs text-slate-500 block mb-1">Current Moisture</span>
            <div className="flex items-baseline gap-1">
              <span className="text-2xl font-black text-slate-900">
                {advisory.current_soil_moisture_pct.toFixed(1)}
              </span>
              <span className="text-xs font-bold text-slate-600">% Vol</span>
            </div>
            <p className="text-[10px] text-slate-400 mt-0.5">Root-zone 0-30cm</p>
          </div>

          {/* Stress threshold */}
          <div className="bg-white p-3 rounded-xl border border-slate-200 shadow-xs">
            <span className="text-xs text-slate-500 block mb-1">RAW Threshold</span>
            <div className="flex items-baseline gap-1">
              <span className="text-2xl font-black text-slate-900">
                {advisory.raw_threshold_pct.toFixed(1)}
              </span>
              <span className="text-xs font-bold text-slate-600">% Vol</span>
            </div>
            <p className="text-[10px] text-slate-400 mt-0.5">FC: {advisory.field_capacity_pct}% | WP: {advisory.wilting_point_pct}%</p>
          </div>
        </div>

        {/* Ethical Disclaimer */}
        <div className="flex items-start gap-2 pt-3 border-t border-slate-200/80 text-[11px] text-slate-500">
          <AlertCircle className="w-4 h-4 text-slate-400 shrink-0 mt-0.5" />
          <p>{isUrdu ? advisory.disclaimer_ur : advisory.disclaimer_en}</p>
        </div>
      </div>

      {/* 2. Pest & Disease Alert Card */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm flex flex-col justify-between">
        <div>
          <div className="flex items-center justify-between mb-4 pb-3 border-b border-slate-100">
            <div className="flex items-center gap-2">
              <Bug className="w-5 h-5 text-rose-600" />
              <h3 className="font-bold text-slate-900 text-base">{t('advisory.pest_title')}</h3>
            </div>
            <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold border ${pestRiskStyles}`}>
              {advisory.pest_risk.risk_level} RISK
            </span>
          </div>

          <div className="mb-4">
            <span className="text-xs text-slate-500 block mb-1">Potential Threat:</span>
            <h4 className="font-bold text-slate-800 text-sm">
              {isUrdu ? advisory.pest_risk.pest_name_ur : advisory.pest_risk.pest_name_en}
            </h4>
          </div>

          <div className="bg-slate-50 rounded-xl p-3.5 border border-slate-200/80 mb-4 text-xs space-y-2">
            <p className="text-slate-600 leading-relaxed">
              {isUrdu ? advisory.pest_risk.description_ur : advisory.pest_risk.description_en}
            </p>
            <div className="pt-2 border-t border-slate-200 font-medium text-slate-800 leading-relaxed">
              <span className="font-bold text-emerald-800 block mb-0.5">Recommended Field Action:</span>
              {isUrdu ? advisory.pest_risk.action_ur : advisory.pest_risk.action_en}
            </div>
          </div>
        </div>

        <div className="text-[11px] text-slate-400 flex items-center gap-1.5 pt-3 border-t border-slate-100">
          <ShieldAlert className="w-3.5 h-3.5" />
          <span>Microclimate temperature & humidity epidemiological model</span>
        </div>
      </div>
    </div>
  );
};

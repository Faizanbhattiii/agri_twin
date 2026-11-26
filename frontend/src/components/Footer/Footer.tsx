import React from 'react';
import { useTranslation } from 'react-i18next';
import { ShieldCheck, Database, Satellite, CloudSun, Leaf } from 'lucide-react';

export const Footer: React.FC = () => {
  const { t } = useTranslation();

  return (
    <footer className="mt-16 bg-white border-t border-slate-200 py-10 text-slate-600 text-xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-6">
        {/* Attributions Grid */}
        <div>
          <h4 className="font-semibold text-slate-800 text-sm mb-3 flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-emerald-600" />
            {t('footer.attribution')}
          </h4>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 flex items-start gap-2.5">
              <Database className="w-4 h-4 text-slate-600 mt-0.5 shrink-0" />
              <div>
                <span className="font-medium text-slate-800 block">Punjab CRS</span>
                <span className="text-slate-500">{t('footer.crs')}</span>
              </div>
            </div>

            <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 flex items-start gap-2.5">
              <CloudSun className="w-4 h-4 text-sky-600 mt-0.5 shrink-0" />
              <div>
                <span className="font-medium text-slate-800 block">Open-Meteo API</span>
                <span className="text-slate-500">{t('footer.open_meteo')}</span>
              </div>
            </div>

            <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 flex items-start gap-2.5">
              <Satellite className="w-4 h-4 text-indigo-600 mt-0.5 shrink-0" />
              <div>
                <span className="font-medium text-slate-800 block">Copernicus Sentinel-2</span>
                <span className="text-slate-500">{t('footer.sentinel')}</span>
              </div>
            </div>

            <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 flex items-start gap-2.5">
              <Leaf className="w-4 h-4 text-emerald-600 mt-0.5 shrink-0" />
              <div>
                <span className="font-medium text-slate-800 block">SoilGrids 250m</span>
                <span className="text-slate-500">{t('footer.soilgrids')}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Authors & Supervision */}
        <div className="pt-4 border-t border-slate-100 flex flex-col sm:flex-row items-center justify-between gap-3 text-slate-500">
          <p>© {new Date().getFullYear()} AgriTwin Pakistan. All rights reserved.</p>
          <p className="font-medium text-slate-700">{t('footer.authors')}</p>
        </div>
      </div>
    </footer>
  );
};

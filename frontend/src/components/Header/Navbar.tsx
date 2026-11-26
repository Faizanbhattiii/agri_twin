import React from 'react';
import { useTranslation } from 'react-i18next';
import { Globe, Sprout, Activity } from 'lucide-react';

interface NavbarProps {
  currentTab: string;
  onTabChange: (tab: string) => void;
  isSimulated: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({ currentTab, onTabChange, isSimulated }) => {
  const { t, i18n } = useTranslation();
  const isUrdu = i18n.language === 'ur';

  const toggleLanguage = () => {
    const nextLang = isUrdu ? 'en' : 'ur';
    i18n.changeLanguage(nextLang);
    document.documentElement.dir = nextLang === 'ur' ? 'rtl' : 'ltr';
    document.documentElement.lang = nextLang;
  };

  const navItems = [
    { id: 'overview', label: t('nav.dashboard') },
    { id: 'map', label: t('nav.map') },
    { id: 'advisory', label: t('nav.advisory') },
    { id: 'simulator', label: t('nav.simulator') },
  ];

  return (
    <header className="sticky top-0 z-50 bg-white/95 backdrop-blur border-b border-slate-200 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Brand Logo & Title */}
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-emerald-600 to-emerald-400 flex items-center justify-center text-white shadow-md shadow-emerald-500/20">
              <Sprout className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-lg text-slate-900 tracking-tight">{t('app_title')}</span>
                {isSimulated && (
                  <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-amber-100 text-amber-800 border border-amber-300 animate-pulse">
                    {t('badge.simulated')}
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-500 hidden sm:block truncate max-w-md">
                {t('app_subtitle')}
              </p>
            </div>
          </div>

          {/* Navigation Tabs */}
          <nav className="hidden md:flex items-center gap-1 bg-slate-100 p-1 rounded-xl">
            {navItems.map((item) => (
              <button
                key={item.id}
                onClick={() => onTabChange(item.id)}
                className={`px-3.5 py-1.5 rounded-lg text-sm font-medium transition-all ${
                  currentTab === item.id
                    ? 'bg-white text-emerald-700 shadow-sm'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/60'
                }`}
              >
                {item.label}
              </button>
            ))}
          </nav>

          {/* Language Toggle & Status */}
          <div className="flex items-center gap-3">
            <div className="hidden lg:flex items-center gap-2 text-xs font-medium text-emerald-700 bg-emerald-50 border border-emerald-200 px-2.5 py-1 rounded-full">
              <Activity className="w-3.5 h-3.5 animate-pulse text-emerald-500" />
              <span>{t('badge.online')}</span>
            </div>

            <button
              onClick={toggleLanguage}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-300 text-sm font-medium text-slate-700 hover:bg-slate-100 transition-colors"
              title="Toggle Language / زبان تبدیل کریں"
            >
              <Globe className="w-4 h-4 text-slate-500" />
              <span>{t('nav.lang_toggle')}</span>
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Navigation bar */}
      <div className="md:hidden border-t border-slate-200 bg-slate-50 px-2 py-1 flex items-center justify-around">
        {navItems.map((item) => (
          <button
            key={item.id}
            onClick={() => onTabChange(item.id)}
            className={`px-2 py-1.5 text-xs font-medium rounded-md ${
              currentTab === item.id ? 'bg-emerald-600 text-white' : 'text-slate-600'
            }`}
          >
            {item.label}
          </button>
        ))}
      </div>
    </header>
  );
};

export interface ThemePreset {
  name: string;
  label: string;
  gradient: string;
  isDark: boolean;
  antToken: {
    colorPrimary: string;
    colorBgContainer: string;
    colorBorderBg: string;
    colorText: string;
    colorTextSecondary: string;
    borderRadius: number;
  };
  sidebar: {
    bg: string;
    borderColor: string;
    textColor: string;
    textColorMuted: string;
    menuTheme: 'dark' | 'light';
  };
  glass: {
    bg: string;
    border: string;
  };
}

export const themes: ThemePreset[] = [
  {
    name: 'aurora',
    label: '极光',
    gradient: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    isDark: true,
    antToken: { colorPrimary: '#7c6fe0', colorBgContainer: 'rgba(255,255,255,0.12)', colorBorderBg: 'rgba(255,255,255,0.18)', colorText: '#ffffff', colorTextSecondary: 'rgba(255,255,255,0.65)', borderRadius: 14 },
    sidebar: { bg: 'rgba(0,0,0,0.2)', borderColor: 'rgba(255,255,255,0.1)', textColor: 'rgba(255,255,255,0.85)', textColorMuted: 'rgba(255,255,255,0.45)', menuTheme: 'dark' },
    glass: { bg: 'rgba(255,255,255,0.12)', border: 'rgba(255,255,255,0.18)' },
  },
  {
    name: 'ocean',
    label: '深海',
    gradient: 'linear-gradient(135deg, #0f2027 0%, #203a43 50%, #2c5364 100%)',
    isDark: true,
    antToken: { colorPrimary: '#4a9ead', colorBgContainer: 'rgba(255,255,255,0.08)', colorBorderBg: 'rgba(255,255,255,0.12)', colorText: '#ffffff', colorTextSecondary: 'rgba(255,255,255,0.6)', borderRadius: 14 },
    sidebar: { bg: 'rgba(0,0,0,0.25)', borderColor: 'rgba(255,255,255,0.08)', textColor: 'rgba(255,255,255,0.85)', textColorMuted: 'rgba(255,255,255,0.4)', menuTheme: 'dark' },
    glass: { bg: 'rgba(255,255,255,0.08)', border: 'rgba(255,255,255,0.12)' },
  },
  {
    name: 'night',
    label: '暗夜',
    gradient: 'linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%)',
    isDark: true,
    antToken: { colorPrimary: '#6c63ff', colorBgContainer: 'rgba(255,255,255,0.06)', colorBorderBg: 'rgba(255,255,255,0.1)', colorText: '#ffffff', colorTextSecondary: 'rgba(255,255,255,0.55)', borderRadius: 14 },
    sidebar: { bg: 'rgba(0,0,0,0.3)', borderColor: 'rgba(255,255,255,0.06)', textColor: 'rgba(255,255,255,0.8)', textColorMuted: 'rgba(255,255,255,0.35)', menuTheme: 'dark' },
    glass: { bg: 'rgba(255,255,255,0.06)', border: 'rgba(255,255,255,0.1)' },
  },
  {
    name: 'emerald',
    label: '翡翠',
    gradient: 'linear-gradient(135deg, #11998e 0%, #38ef7d 100%)',
    isDark: false,
    antToken: { colorPrimary: '#0e8c73', colorBgContainer: 'rgba(255,255,255,0.35)', colorBorderBg: 'rgba(0,0,0,0.08)', colorText: '#1a3a32', colorTextSecondary: 'rgba(26,58,50,0.55)', borderRadius: 14 },
    sidebar: { bg: 'rgba(0,0,0,0.12)', borderColor: 'rgba(0,0,0,0.06)', textColor: 'rgba(255,255,255,0.9)', textColorMuted: 'rgba(255,255,255,0.5)', menuTheme: 'dark' },
    glass: { bg: 'rgba(255,255,255,0.35)', border: 'rgba(0,0,0,0.08)' },
  },
  {
    name: 'sunset',
    label: '日落',
    gradient: 'linear-gradient(135deg, #ee9ca7 0%, #ffdde1 100%)',
    isDark: false,
    antToken: { colorPrimary: '#c2586a', colorBgContainer: 'rgba(255,255,255,0.5)', colorBorderBg: 'rgba(0,0,0,0.06)', colorText: '#4a2030', colorTextSecondary: 'rgba(74,32,48,0.55)', borderRadius: 14 },
    sidebar: { bg: 'rgba(180,80,100,0.25)', borderColor: 'rgba(180,80,100,0.15)', textColor: '#5a2540', textColorMuted: 'rgba(90,37,64,0.5)', menuTheme: 'light' },
    glass: { bg: 'rgba(255,255,255,0.5)', border: 'rgba(0,0,0,0.06)' },
  },
  {
    name: 'peach',
    label: '蜜桃',
    gradient: 'linear-gradient(135deg, #f6d365 0%, #fda085 100%)',
    isDark: false,
    antToken: { colorPrimary: '#c87540', colorBgContainer: 'rgba(255,255,255,0.5)', colorBorderBg: 'rgba(0,0,0,0.06)', colorText: '#4a3020', colorTextSecondary: 'rgba(74,48,32,0.55)', borderRadius: 14 },
    sidebar: { bg: 'rgba(180,100,50,0.2)', borderColor: 'rgba(180,100,50,0.12)', textColor: '#5a3820', textColorMuted: 'rgba(90,56,32,0.5)', menuTheme: 'light' },
    glass: { bg: 'rgba(255,255,255,0.5)', border: 'rgba(0,0,0,0.06)' },
  },
  {
    name: 'snow',
    label: '素白',
    gradient: 'linear-gradient(135deg, #e0e5ec 0%, #f0f2f5 50%, #e8ecf1 100%)',
    isDark: false,
    antToken: { colorPrimary: '#4a6fa5', colorBgContainer: 'rgba(255,255,255,0.8)', colorBorderBg: 'rgba(0,0,0,0.08)', colorText: '#2c3e50', colorTextSecondary: 'rgba(44,62,80,0.5)', borderRadius: 14 },
    sidebar: { bg: 'rgba(255,255,255,0.7)', borderColor: 'rgba(0,0,0,0.06)', textColor: '#2c3e50', textColorMuted: 'rgba(44,62,80,0.4)', menuTheme: 'light' },
    glass: { bg: 'rgba(255,255,255,0.8)', border: 'rgba(0,0,0,0.08)' },
  },
];

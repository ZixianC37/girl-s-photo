import { createContext, useContext, useState, useEffect } from 'react';
import type { ReactNode } from 'react';
import { ConfigProvider, theme as antTheme } from 'antd';
import { themes } from './themes';
import type { ThemePreset } from './themes';
import './glass.css';

const ThemeContext = createContext<{
  current: ThemePreset;
  setTheme: (name: string) => void;
}>({ current: themes[0], setTheme: () => {} });

export const useTheme = () => useContext(ThemeContext);

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [current, setCurrent] = useState<ThemePreset>(() => {
    const saved = localStorage.getItem('theme_name');
    return themes.find(t => t.name === saved) || themes[0];
  });

  const setTheme = (name: string) => {
    const t = themes.find(t => t.name === name);
    if (t) {
      setCurrent(t);
      localStorage.setItem('theme_name', name);
    }
  };

  // Set data-theme attribute for CSS targeting
  useEffect(() => {
    document.body.setAttribute('data-theme', current.isDark ? 'dark' : 'light');
  }, [current]);

  return (
    <ThemeContext.Provider value={{ current, setTheme }}>
      <ConfigProvider
        theme={{
          algorithm: antTheme.defaultAlgorithm,
          token: {
            ...current.antToken,
            fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
          },
        }}
      >
        <div style={{ background: current.gradient, minHeight: '100vh', position: 'relative' }}>
          {children}
        </div>
      </ConfigProvider>
    </ThemeContext.Provider>
  );
}

import { useTheme } from '../theme/ThemeContext';
import { themes } from '../theme/themes';

export function ThemeSwitcher() {
  const { current, setTheme } = useTheme();
  const activeBorder = current.isDark ? '#fff' : current.antToken.colorPrimary;
  const activeShadow = current.isDark ? 'rgba(255,255,255,0.4)' : current.antToken.colorPrimary;

  return (
    <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', padding: '8px 0' }}>
      {themes.map(t => (
        <div
          key={t.name}
          onClick={() => setTheme(t.name)}
          title={t.label}
          style={{
            width: 24, height: 24, borderRadius: '50%',
            background: t.gradient,
            cursor: 'pointer',
            border: current.name === t.name ? `2px solid ${activeBorder}` : '2px solid transparent',
            boxShadow: current.name === t.name ? `0 0 8px ${activeShadow}` : 'none',
            transition: 'transform 0.2s, border 0.2s',
          }}
          onMouseEnter={e => (e.currentTarget.style.transform = 'scale(1.15)')}
          onMouseLeave={e => (e.currentTarget.style.transform = 'scale(1)')}
        />
      ))}
    </div>
  );
}

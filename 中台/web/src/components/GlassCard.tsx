import type { ReactNode } from 'react';
import { useTheme } from '../theme/ThemeContext';

export function GlassCard({ title, children, style }: { title?: string; children: ReactNode; style?: React.CSSProperties }) {
  const { current } = useTheme();
  const g = current.glass;

  return (
    <div style={{
      background: g.bg,
      backdropFilter: 'blur(16px)',
      WebkitBackdropFilter: 'blur(16px)',
      border: `1px solid ${g.border}`,
      borderRadius: 14,
      padding: 16,
      ...style,
    }}>
      {title && <div style={{ fontSize: 14, fontWeight: 500, marginBottom: 12, opacity: 0.9 }}>{title}</div>}
      {children}
    </div>
  );
}

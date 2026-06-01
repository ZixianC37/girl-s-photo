import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { Menu } from 'antd';
import {
  DashboardOutlined,
  ExperimentOutlined,
  WarningOutlined,
  LogoutOutlined,
  SettingOutlined,
  ApiOutlined,
  TeamOutlined,
  MonitorOutlined,
} from '@ant-design/icons';
import { ThemeSwitcher } from './ThemeSwitcher';
import { useTheme } from '../theme/ThemeContext';

const menuItems = [
  { key: '/', icon: <DashboardOutlined />, label: '仪表盘' },
  { key: '/projects', icon: <ExperimentOutlined />, label: '研发项目' },
  { key: '/anomalies', icon: <WarningOutlined />, label: '异常中心' },
  {
    key: 'settings',
    icon: <SettingOutlined />,
    label: '系统配置',
    children: [
      { key: '/routes', icon: <ApiOutlined />, label: '任务路由' },
      { key: '/users', icon: <TeamOutlined />, label: '用户映射' },
      { key: '/tasks', icon: <MonitorOutlined />, label: '任务监控' },
    ],
  },
];

export default function AppLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const { current } = useTheme();
  const sb = current.sidebar;

  const handleLogout = () => {
    localStorage.removeItem('admin_token');
    navigate('/login');
  };

  const selectedKeys = [location.pathname];
  const openKeys = ['/routes', '/users', '/tasks'].includes(location.pathname)
    ? ['settings'] : [];

  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      <div
        style={{
          width: 220,
          flexShrink: 0,
          display: 'flex',
          flexDirection: 'column',
          background: sb.bg,
          backdropFilter: 'blur(20px)',
          WebkitBackdropFilter: 'blur(20px)',
          borderRight: `1px solid ${sb.borderColor}`,
          color: sb.textColor,
        }}
      >
        <div style={{ padding: '20px 16px', fontSize: 16, fontWeight: 700, borderBottom: `1px solid ${sb.borderColor}`, color: sb.textColor }}>
          业务中台
        </div>

        <Menu
          mode="inline"
          selectedKeys={selectedKeys}
          defaultOpenKeys={openKeys}
          items={menuItems}
          onClick={({ key }) => { if (key.startsWith('/')) navigate(key); }}
          theme={sb.menuTheme}
          style={{
            flex: 1,
            background: 'transparent',
            border: 'none',
          }}
        />

        <div style={{ padding: '12px 16px', borderTop: `1px solid ${sb.borderColor}` }}>
          <div style={{ fontSize: 11, color: sb.textColorMuted, marginBottom: 8 }}>主题色</div>
          <ThemeSwitcher />
          <div
            onClick={handleLogout}
            style={{
              display: 'flex', alignItems: 'center', gap: 8,
              padding: '8px 0', marginTop: 12,
              color: sb.textColorMuted, cursor: 'pointer', fontSize: 12,
            }}
          >
            <LogoutOutlined /> 退出登录
          </div>
        </div>
      </div>

      <div style={{ flex: 1, padding: 24, overflowY: 'auto' }}>
        <Outlet />
      </div>
    </div>
  );
}

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Input, Button } from 'antd';

export default function Login() {
  const [token, setToken] = useState('');
  const navigate = useNavigate();

  const handleLogin = () => {
    if (token.trim()) {
      localStorage.setItem('admin_token', token.trim());
      navigate('/');
    }
  };

  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh' }}>
      <div style={{
        background: 'rgba(255,255,255,0.12)',
        backdropFilter: 'blur(20px)',
        WebkitBackdropFilter: 'blur(20px)',
        border: '1px solid rgba(255,255,255,0.18)',
        borderRadius: 16,
        padding: 40,
        width: 360,
        textAlign: 'center',
      }}>
        <h1 style={{ color: '#fff', marginBottom: 8, fontSize: 24 }}>业务中台</h1>
        <p style={{ color: 'rgba(255,255,255,0.6)', marginBottom: 32, fontSize: 14 }}>管理后台</p>
        <Input.Password
          size="large"
          placeholder="请输入管理 Token"
          value={token}
          onChange={e => setToken(e.target.value)}
          onPressEnter={handleLogin}
          style={{ marginBottom: 16 }}
        />
        <Button type="primary" size="large" block onClick={handleLogin}>
          进入系统
        </Button>
      </div>
    </div>
  );
}

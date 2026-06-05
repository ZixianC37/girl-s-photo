#!/usr/bin/env python3
"""本地开发服务器 — 静态文件 + 飞书 API 代理"""

import http.server
import json
import urllib.request
import os
import sys

PORT = 9090
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 从 config-local.js 提取凭证
APP_ID = ''
APP_SECRET = ''

def load_credentials():
    global APP_ID, APP_SECRET
    config_path = os.path.join(BASE_DIR, 'js', 'config-local.js')
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            for line in f:
                line = line.strip()
                if 'FEISHU_APP_ID' in line and '=' in line and 'cli_' in line:
                    APP_ID = line.split("'")[1]
                elif 'FEISHU_APP_SECRET' in line and '=' in line and 'HsH' in line:
                    APP_SECRET = line.split("'")[1]

load_credentials()

# Token 缓存
cached_token = None
token_expire = 0

def get_token():
    global cached_token, token_expire
    import time
    if cached_token and time.time() < token_expire - 300:
        return cached_token

    url = 'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal'
    data = json.dumps({'app_id': APP_ID, 'app_secret': APP_SECRET}).encode()
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read())
    if result.get('code') != 0:
        raise Exception(f"获取 token 失败: {result.get('msg')}")
    cached_token = result['tenant_access_token']
    token_expire = time.time() + result.get('expire', 7200)
    print(f"✅ Token 获取成功，有效期 {result.get('expire', 7200)}s")
    return cached_token


class ProxyHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE_DIR, **kwargs)

    def do_GET(self):
        # API 代理路由
        if self.path.startswith('/api/records/'):
            self.proxy_bitable()
            return
        if self.path == '/api/token':
            self.send_json({'token': get_token()})
            return
        # 静态文件
        super().do_GET()

    def proxy_bitable(self):
        """代理飞书 Bitable API 请求"""
        try:
            token = get_token()
            # path: /api/records/{table_id}?page_size=500
            parts = self.path.split('/')
            table_id = parts[3].split('?')[0]

            # 解析查询参数
            query = self.path.split('?', 1)
            page_size = 500
            page_token = ''
            if len(query) > 1:
                for param in query[1].split('&'):
                    if param.startswith('page_size='):
                        page_size = param.split('=')[1]
                    elif param.startswith('page_token='):
                        page_token = param.split('=')[1]

            # 读取 config.js 中的 APP_TOKEN
            app_token = 'LCHzbZfDhaaSX4s4NAucQ8KPnDc'

            url = f'https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records?page_size={page_size}'
            if page_token:
                url += f'&page_token={page_token}'

            req = urllib.request.Request(url, headers={
                'Authorization': f'Bearer {token}',
            })
            with urllib.request.urlopen(req) as resp:
                data = resp.read()

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(data)

        except Exception as e:
            print(f"❌ API 代理错误: {e}")
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())

    def send_json(self, obj):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(obj).encode())

    def log_message(self, format, *args):
        print(f"  {args[0]}")


if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else PORT
    with http.server.HTTPServer(('', port), ProxyHandler) as httpd:
        print(f"🚀 热力图开发服务器启动: http://localhost:{port}")
        print(f"   静态文件 + 飞书 API 代理")
        print(f"   App ID: {APP_ID[:8]}...")
        print(f"   按 Ctrl+C 停止")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n🛑 服务器已停止")

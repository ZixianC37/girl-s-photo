import { chromium } from 'playwright';

const BASE = 'http://localhost:8000';
const PASS = [];
const FAIL = [];

function log_pass(name) { PASS.push(name); console.log(`  ✅ PASS: ${name}`); }
function log_fail(name, detail) { FAIL.push({ name, detail }); console.log(`  ❌ FAIL: ${name} — ${detail}`); }

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1400, height: 900 } });

  // Set auth token before any navigation
  await context.addInitScript(() => {
    localStorage.setItem('admin_token', 'changeme');
  });

  const page = await context.newPage();

  // Collect console errors
  const consoleErrors = [];
  page.on('console', msg => {
    if (msg.type() === 'error') consoleErrors.push(msg.text());
  });

  // Collect page errors
  const pageErrors = [];
  page.on('pageerror', err => pageErrors.push(err.message));

  async function testPage(path, name, checkFn) {
    consoleErrors.length = 0;
    pageErrors.length = 0;
    try {
      await page.goto(`${BASE}${path}`, { waitUntil: 'networkidle', timeout: 15000 });
      await page.waitForTimeout(1000);

      // Check no white screen (body should have content)
      const bodyText = await page.textContent('body');
      if (!bodyText || bodyText.trim().length === 0) {
        log_fail(name, '白屏 — body 为空');
        return;
      }

      // Check for React error boundary or crash
      const hasError = await page.locator('text=Something went wrong').count() > 0;
      if (hasError) {
        log_fail(name, 'React 错误边界触发');
        return;
      }

      // Run custom checks
      if (checkFn) {
        await checkFn(page);
      } else {
        log_pass(name);
      }

      // Check console errors (only API errors are concerning, not CSS warnings)
      const apiErrors = consoleErrors.filter(e => e.includes('401') || e.includes('500') || e.includes('Network Error'));
      if (apiErrors.length > 0 && !path.includes('login')) {
        log_fail(`${name} (API errors)`, apiErrors.join('; '));
      }

    } catch (err) {
      log_fail(name, err.message);
    }
  }

  console.log('\n=========================================');
  console.log('=== 浏览器端到端测试 ===');
  console.log('=========================================\n');

  // ==========================================
  console.log('=== 1. 登录页面 ===');
  // ==========================================

  // Test without token first — should show login
  const cleanContext = await browser.newContext();
  const cleanPage = await cleanContext.newPage();
  await cleanPage.goto(`${BASE}/`, { waitUntil: 'networkidle', timeout: 10000 });
  await cleanPage.waitForTimeout(1000);
  const loginVisible = await cleanPage.locator('input[type="password"], input[placeholder*="密码"], input[placeholder*="token"]').count() > 0;
  if (loginVisible) {
    log_pass('未登录 → 跳转登录页');
  } else {
    const url = cleanPage.url();
    if (url.includes('login')) {
      log_pass('未登录 → 跳转登录页 (URL)');
    } else {
      log_fail('未登录跳转', `当前URL: ${url}`);
    }
  }
  await cleanContext.close();

  // ==========================================
  console.log('\n=== 2. 仪表盘 ===');
  // ==========================================
  await testPage('/', '仪表盘加载', async (p) => {
    // Should have stats cards
    const stats = await p.locator('.ant-statistic').count();
    if (stats >= 3) {
      log_pass(`仪表盘 — 显示 ${stats} 个统计卡片`);
    } else {
      log_fail('仪表盘统计卡片', `只找到 ${stats} 个`);
    }

    // Should have "活跃工作坊" section or tasks
    const hasContent = await p.locator('text=活跃工作坊').count() > 0 || await p.locator('text=进行中任务').count() > 0;
    if (hasContent) {
      log_pass('仪表盘 — 显示任务概览');
    } else {
      log_fail('仪表盘任务概览', '未找到任务相关内容');
    }

    // Take screenshot
    await p.screenshot({ path: 'tests/screenshots/dashboard.png', fullPage: true });
    log_pass('仪表盘截图已保存');
  });

  // ==========================================
  console.log('\n=== 3. 任务路由页面 ===');
  // ==========================================
  await testPage('/routes', '任务路由页面', async (p) => {
    const table = await p.locator('.ant-table').count();
    if (table > 0) {
      log_pass('任务路由 — 表格渲染');
    } else {
      log_fail('任务路由表格', '未找到表格');
    }
    await p.screenshot({ path: 'tests/screenshots/routes.png', fullPage: true });
    log_pass('任务路由截图已保存');
  });

  // ==========================================
  console.log('\n=== 4. 用户映射页面 ===');
  // ==========================================
  await testPage('/users', '用户映射页面', async (p) => {
    const table = await p.locator('.ant-table').count();
    const empty = await p.locator('.ant-empty').count();
    const heading = await p.locator('text=用户映射').count();
    const hasContent = table > 0 || empty > 0 || heading > 0;
    if (hasContent) {
      log_pass('用户映射 — 页面渲染');
    } else {
      log_fail('用户映射页面', '无内容');
    }
    await p.screenshot({ path: 'tests/screenshots/users.png', fullPage: true });
    log_pass('用户映射截图已保存');
  });

  // ==========================================
  console.log('\n=== 5. 任务监控页面 ===');
  // ==========================================
  await testPage('/tasks', '任务监控页面', async (p) => {
    const table = await p.locator('.ant-table').count();
    const empty = await p.locator('.ant-empty').count();
    const hasContent = table > 0 || empty > 0;
    if (hasContent) {
      log_pass('任务监控 — 页面渲染');
    } else {
      log_fail('任务监控页面', '无内容');
    }
    await p.screenshot({ path: 'tests/screenshots/tasks.png', fullPage: true });
    log_pass('任务监控截图已保存');
  });

  // ==========================================
  console.log('\n=== 6. 产品研发页面 (RD Tasks) ===');
  // ==========================================
  await testPage('/rd-tasks', '产品研发页面', async (p) => {
    const table = await p.locator('.ant-table').count();
    const card = await p.locator('.ant-card').count();
    const hasContent = table > 0 || card > 0;
    if (hasContent) {
      log_pass('产品研发 — 页面渲染');
    } else {
      log_fail('产品研发页面', '无内容');
    }
    await p.screenshot({ path: 'tests/screenshots/rd-tasks.png', fullPage: true });
    log_pass('产品研发截图已保存');
  });

  // ==========================================
  console.log('\n=== 7. 模板管理页面 ===');
  // ==========================================
  await testPage('/templates', '模板管理页面', async (p) => {
    const table = await p.locator('.ant-table').count();
    const card = await p.locator('.ant-card').count();
    const hasContent = table > 0 || card > 0;
    if (hasContent) {
      log_pass('模板管理 — 页面渲染');
    } else {
      log_fail('模板管理页面', '无内容');
    }
    await p.screenshot({ path: 'tests/screenshots/templates.png', fullPage: true });
    log_pass('模板管理截图已保存');
  });

  // ==========================================
  console.log('\n=== 8. 异常中心页面 ===');
  // ==========================================
  await testPage('/anomalies', '异常中心页面', async (p) => {
    const table = await p.locator('.ant-table').count();
    const empty = await p.locator('.ant-empty').count();
    const hasContent = table > 0 || empty > 0;
    if (hasContent) {
      log_pass('异常中心 — 页面渲染');
    } else {
      log_fail('异常中心页面', '无内容');
    }
    await p.screenshot({ path: 'tests/screenshots/anomalies.png', fullPage: true });
    log_pass('异常中心截图已保存');
  });

  // ==========================================
  console.log('\n=== 9. 侧边栏导航测试 ===');
  // ==========================================
  const menuItems = [
    { path: '/', label: '仪表盘' },
    { path: '/routes', label: '任务路由' },
    { path: '/users', label: '用户映射' },
    { path: '/tasks', label: '任务监控' },
    { path: '/rd-tasks', label: '产品研发' },
    { path: '/templates', label: '模板管理' },
    { path: '/anomalies', label: '异常中心' },
  ];

  for (const item of menuItems) {
    await page.goto(`${BASE}${item.path}`, { waitUntil: 'networkidle', timeout: 10000 });
    await page.waitForTimeout(500);

    // Check sidebar is visible
    const sidebar = await page.locator('.glass-sidebar, .ant-menu').count();
    if (sidebar > 0) {
      const activeItem = await page.locator(`.ant-menu-item-selected:has-text("${item.label}")`).count();
      if (activeItem > 0 || item.path === '/') {
        log_pass(`导航: ${item.label} — 侧边栏高亮正确`);
      }
    } else {
      log_fail(`导航: ${item.label}`, '侧边栏未找到');
    }
  }

  // ==========================================
  console.log('\n=========================================');
  console.log('=== 浏览器测试结果汇总 ===');
  console.log('=========================================');
  console.log(`\n  通过: ${PASS.length} | 失败: ${FAIL.length}\n`);
  for (const f of FAIL) {
    console.log(`  ❌ ${f.name}: ${f.detail}`);
  }
  console.log('');

  await browser.close();
  process.exit(FAIL.length > 0 ? 1 : 0);
})();

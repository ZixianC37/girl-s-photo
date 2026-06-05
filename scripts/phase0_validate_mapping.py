#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 0: 数据映射校验脚本
校验门店日拍摄清单中的「拍摄风格」字段和执行output表的「方案名称」字段是否一一对应
这是所有后续指标计算的前提条件。
"""

import json
import urllib.request
import urllib.error
import os
import sys
import re

# 配置常量
APP_TOKEN = "LCHzbZfDhaaSX4s4NAucQ8KPnDc"
EXEC_OUTPUT_TABLE_ID = "tblnNUnerqMCcjaz"
EXEC_OUTPUT_FIELD_NAME = "方案名称"
EXEC_OUTPUT_APPLET_FIELD = "小程序端"
EXEC_OUTPUT_NEW_DATE_FIELD = "上新时间"

# 门店日拍摄清单配置
STORE_TABLES = {
    "麦芽纪滨江": "tblGZA041E5o5PUU",
    "麦芽纪下沙": "tblIdWwwM2Gyu1fG",
    "甜熊下沙": "tblV3qt3aDNz6663",
}

STORE_FIELD_NAME = "拍摄风格"
STORE_AMOUNT_FIELD = "本次拍摄金额"


class FeishuAPIError(Exception):
    """飞书API错误"""
    pass


def load_credentials():
    """从 config-local.js 加载凭证"""
    config_path = os.path.join(os.path.dirname(__file__), "..", "heatmap", "js", "config-local.js")

    if not os.path.exists(config_path):
        raise FileNotFoundError(f"配置文件不存在: {config_path}")

    with open(config_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 解析 JavaScript 变量
    app_id_match = re.search(r"var FEISHU_APP_ID = '([^']+)'", content)
    app_secret_match = re.search(r"var FEISHU_APP_SECRET = '([^']+)'", content)

    if not app_id_match or not app_secret_match:
        raise ValueError("无法从配置文件中解析 FEISHU_APP_ID 或 FEISHU_APP_SECRET")

    return app_id_match.group(1), app_secret_match.group(1)


def get_tenant_access_token(app_id, app_secret):
    """获取 tenant_access_token"""
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    data = json.dumps({
        "app_id": app_id,
        "app_secret": app_secret
    }).encode('utf-8')

    req = urllib.request.Request(url, data=data, method='POST')
    req.add_header('Content-Type', 'application/json')

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode('utf-8'))

        if result.get('code') != 0:
            raise FeishuAPIError(f"获取 token 失败: {result.get('msg')}")

        return result.get('tenant_access_token')
    except urllib.error.URLError as e:
        raise FeishuAPIError(f"网络请求失败: {e}")


def get_all_records(access_token, table_id, page_size=500):
    """获取表格所有记录，自动处理分页"""
    base_url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{table_id}/records"
    all_records = []
    page_token = None

    while True:
        params = {"page_size": page_size}
        if page_token:
            params["page_token"] = page_token

        query_string = urllib.parse.urlencode(params)
        url = f"{base_url}?{query_string}"

        req = urllib.request.Request(url, method='GET')
        req.add_header('Authorization', f'Bearer {access_token}')

        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode('utf-8'))

            if result.get('code') != 0:
                raise FeishuAPIError(f"获取记录失败: {result.get('msg')}")

            data = result.get('data', {})
            records = data.get('items', [])
            all_records.extend(records)

            has_more = data.get('has_more', False)
            if not has_more:
                break

            page_token = data.get('page_token')

        except urllib.error.URLError as e:
            raise FeishuAPIError(f"网络请求失败: {e}")

    return all_records


def extract_field_values(records, field_name):
    """从记录中提取指定字段的所有值"""
    values = set()

    for record in records:
        fields = record.get('fields', {})
        value = fields.get(field_name)

        if value is None:
            continue

        # 飞书字段值格式：单选返回字符串，多选返回字符串数组
        if isinstance(value, list):
            for item in value:
                if item:  # 过滤空字符串
                    values.add(item)
        elif isinstance(value, str) and value:
            values.add(value)

    return values


def calculate_amount_stats(records, field_name):
    """计算金额字段统计信息"""
    total_count = len(records)
    filled_count = 0
    total_amount = 0.0

    for record in records:
        fields = record.get('fields', {})
        value = fields.get(field_name)

        if value is not None and value != "":
            filled_count += 1
            try:
                # 尝试转换为数字（处理可能的字符串格式）
                amount = float(str(value).replace(',', '').replace('¥', '').replace('￥', ''))
                total_amount += amount
            except (ValueError, TypeError):
                # 如果转换失败，不计入总和但计数
                pass

    fill_rate = (filled_count / total_count * 100) if total_count > 0 else 0

    return {
        "total_count": total_count,
        "filled_count": filled_count,
        "fill_rate": fill_rate,
        "total_amount": total_amount
    }


def validate_new_date_fill_rate(records):
    """计算上新时间字段填充率（仅统计已上架产品）"""
    total_count = 0
    filled_count = 0

    for record in records:
        fields = record.get('fields', {})
        applet_value = fields.get(EXEC_OUTPUT_APPLET_FIELD)

        # 检查小程序端字段是否包含"已上架"
        is_launched = False
        if isinstance(applet_value, list):
            is_launched = any("已上架" in str(item) for item in applet_value)
        elif isinstance(applet_value, str):
            is_launched = "已上架" in applet_value

        if is_launched:
            total_count += 1
            new_date_value = fields.get(EXEC_OUTPUT_NEW_DATE_FIELD)
            if new_date_value is not None and new_date_value != "":
                filled_count += 1

    fill_rate = (filled_count / total_count * 100) if total_count > 0 else 0

    return {
        "total_launched": total_count,
        "filled_count": filled_count,
        "fill_rate": fill_rate
    }


def calculate_mapping_rate(source_set, target_set):
    """计算映射率（源集合中能在目标集合中找到匹配的比例）"""
    if not source_set:
        return 100.0  # 空集合视为100%匹配

    matched = sum(1 for item in source_set if item in target_set)
    return (matched / len(source_set) * 100)


def main():
    print("=" * 80)
    print("Phase 0: 数据映射校验")
    print("=" * 80)
    print()

    try:
        # 1. 加载凭证
        print("📋 加载飞书凭证...")
        app_id, app_secret = load_credentials()
        print(f"   APP_ID: {app_id}")
        print()

        # 2. 获取 token
        print("🔑 获取访问令牌...")
        access_token = get_tenant_access_token(app_id, app_secret)
        print("   ✓ 令牌获取成功")
        print()

        # 3. 拉取执行output表数据
        print(f"📊 拉取执行output表数据...")
        exec_output_records = get_all_records(access_token, EXEC_OUTPUT_TABLE_ID)
        print(f"   ✓ 共获取 {len(exec_output_records)} 条记录")

        # 提取方案名称集合
        output_schemes = extract_field_values(exec_output_records, EXEC_OUTPUT_FIELD_NAME)
        print(f"   ✓ 方案名称共 {len(output_schemes)} 个唯一值")
        print()

        # 4. 检查上新时间填充率
        print("📅 检查执行output表上新时间填充率...")
        new_date_stats = validate_new_date_fill_rate(exec_output_records)
        print(f"   已上架产品数: {new_date_stats['total_launched']}")
        print(f"   已填充上新时间: {new_date_stats['filled_count']}")
        print(f"   填充率: {new_date_stats['fill_rate']:.1f}%")
        print()

        # 5. 拉取各门店数据并校验
        print("🏪 拉取门店数据并校验映射关系...")
        print()

        results = {}
        lowest_mapping_rate = 100.0

        for store_name, table_id in STORE_TABLES.items():
            print(f"   处理门店: {store_name}")

            try:
                # 拉取数据
                records = get_all_records(access_token, table_id)
                print(f"     ✓ 共获取 {len(records)} 条记录")

                # 提取拍摄风格集合
                store_styles = extract_field_values(records, STORE_FIELD_NAME)
                print(f"     ✓ 拍摄风格共 {len(store_styles)} 个唯一值")

                # 计算映射率
                mapping_rate = calculate_mapping_rate(store_styles, output_schemes)
                print(f"     ✓ 映射率: {mapping_rate:.1f}%")

                if mapping_rate < lowest_mapping_rate:
                    lowest_mapping_rate = mapping_rate

                # 计算金额字段统计
                amount_stats = calculate_amount_stats(records, STORE_AMOUNT_FIELD)
                print(f"     💰 本次拍摄金额:")
                print(f"        总记录数: {amount_stats['total_count']}")
                print(f"        填充记录数: {amount_stats['filled_count']}")
                print(f"        填充率: {amount_stats['fill_rate']:.1f}%")
                print(f"        金额总和: ¥{amount_stats['total_amount']:.2f}")

                # 找出未匹配的风格
                unmatched = store_styles - output_schemes
                if unmatched:
                    print(f"     ⚠️  未匹配的风格 ({len(unmatched)}):")
                    for style in sorted(unmatched):
                        print(f"        - {style}")

                results[store_name] = {
                    "mapping_rate": mapping_rate,
                    "amount_stats": amount_stats,
                    "unmatched_styles": list(unmatched)
                }

            except FeishuAPIError as e:
                print(f"     ❌ 失败: {e}")
                results[store_name] = {
                    "error": str(e)
                }

            print()

        # 6. 输出结论
        print("=" * 80)
        print("📋 校验结论")
        print("=" * 80)
        print(f"最低映射率: {lowest_mapping_rate:.1f}%")
        print()

        if lowest_mapping_rate >= 90:
            print("✅ 可直接进入 Phase 1")
            exit_code = 0
        elif lowest_mapping_rate >= 80:
            print("⚠️  需建立映射表")
            exit_code = 1
        else:
            print("❌ 需修复数据结构")
            exit_code = 2

        print()

        # 输出详细结果摘要
        print("详细结果摘要:")
        for store_name, result in results.items():
            if "error" in result:
                print(f"  {store_name}: ❌ {result['error']}")
            else:
                print(f"  {store_name}: 映射率 {result['mapping_rate']:.1f}%, "
                      f"金额填充率 {result['amount_stats']['fill_rate']:.1f}%")

        return exit_code

    except Exception as e:
        print(f"❌ 脚本执行失败: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 3


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
# mx_moni - 妙想模拟组合管理技能

import os
import sys
import json
import re
import requests
from typing import Dict, Any, Optional, Tuple
from time import sleep

# 加载环境变量
MX_APIKEY = os.environ.get('MX_APIKEY')
MX_API_URL = os.environ.get('MX_API_URL', 'https://mkapi2.dfcfs.com/finskillshub')
OUTPUT_DIR = '/root/.openclaw/workspace/mx_data/output'

os.makedirs(OUTPUT_DIR, exist_ok=True)

def check_apikey() -> None:
    """检查API密钥是否配置"""
    if not MX_APIKEY:
        print("错误: 未配置MX_APIKEY环境变量，请先配置API密钥")
        print("示例: export MX_APIKEY=your_api_key_here")
        sys.exit(1)

def make_request(endpoint: str, body: Dict[str, Any], output_prefix: str) -> None:
    """发送POST请求并保存结果"""
    check_apikey()
    full_url = f"{MX_API_URL}{endpoint}"
    headers = {
        'apikey': MX_APIKEY,
        'Content-Type': 'application/json'
    }

    try:
        response = requests.post(full_url, headers=headers, json=body)
        response.raise_for_status()
        result = response.json()

        output_path = os.path.join(OUTPUT_DIR, f"{output_prefix}_raw.json")
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        print(f"请求完成，结果保存在 {output_path}")

        # 打印结果摘要
        if result.get('success') or str(result.get('code')) == '200':
            print("\n操作结果: 成功")
            if 'message' in result:
                print(f"提示信息: {result['message']}")
            if 'data' in result and isinstance(result['data'], dict):
                data = result['data']
                if 'totalAssets' in data:
                    print(f"\n账户资金:")
                    print(f"  总资产: {data['totalAssets']:.2f} 元")
                    print(f"  可用资金: {data['availBalance']:.2f} 元")
                if data.get('orderId'):
                    print(f"\n委托成功:")
                    print(f"  委托编号: {data['orderId']}")
        else:
            print(f"\n操作结果: 失败")
            print(f"错误码: {result.get('code')}")
            print(f"错误信息: {result.get('message')}")
    except Exception as e:
        print(f"网络请求失败: {str(e)}")
        sys.exit(1)

def parse_buy_sell(query: str) -> Tuple[Optional[str], Optional[float], Optional[int], bool]:
    """解析买入卖出命令，返回(股票代码, 价格, 数量, 是否市价)"""
    # 提取6位股票代码
    code_match = re.search(r'(\d{6})', query)
    if not code_match:
        return None, None, None, False
    stock_code = code_match.group(1)

    # 提取数量（单位：股，必须是100倍数）
    # 优先匹配 "全部"
    has_all = any(word in query for word in ['全部', '清仓', '全仓', '全卖', '全买'])

    quantity_match = re.search(r'(\d+)\s*(股|手)', query)
    quantity = -1 if has_all else None  # -1 标记全部
    if quantity_match:
        qty = int(quantity_match.group(1))
        if quantity_match.group(2) == '手':
            qty = qty * 100
        quantity = qty

    # 检查是否市价委托
    is_market = any(word in query for word in ['市价', '市价买入', '市价卖出', '现价买入', '现价卖出'])

    # 提取价格 — 找明确带"元"标记的，或小数点两位的数字
    price = None
    if has_all or is_market:
        pass  # 清仓/市价不取价格
    else:
        # 找带元或小数点的数字（排除股票代码6位数字）
        price_candidates = re.findall(r'\d+\.\d+|\d+(?=\s*元)', query)
        for candidate in price_candidates:
            if candidate != stock_code:
                price = float(candidate)
                break
        if price is None and quantity and quantity > 0:
            # 回退：去重后看有没有非股票代码开头的数字
            raw = re.findall(r'\d+\.?\d*', query)
            unique = [v for v in raw if v != stock_code]
            for v in unique:
                pf = float(v)
                if pf < 1000:  # 股票价格不会这么高
                    price = pf
                    break

    return stock_code, price, quantity, is_market

def parse_cancel(query: str) -> Tuple[Optional[str], Optional[str], bool]:
    """解析撤单命令，返回(委托编号, 股票代码, 是否全部撤单)"""
    if any(word in query for word in ['全部', '所有', '一键撤单']):
        return None, None, True

    # 提取委托编号
    order_id_match = re.search(r'(\d{16,20})', query)
    order_id = order_id_match.group(1) if order_id_match else None

    # 提取股票代码
    code_match = re.search(r'(\d{6})', query)
    stock_code = code_match.group(1) if code_match else None

    return order_id, stock_code, False

def main():
    if len(sys.argv) < 2:
        print("请提供操作指令，例如：")
        print("  python mx_moni.py 我的持仓      # 查询持仓")
        print("  python mx_moni.py 我的资金      # 查询资金")
        print("  python mx_moni.py 我的委托      # 查询委托订单")
        print("  python mx_moni.py 买入 600519 价格 1700 数量 100 股")
        print("  python mx_moni.py 市价买入 600519 100 股")
        print("  python mx_moni.py 卖出 600519 价格 1750 数量 100 股")
        print("  python mx_moni.py 撤单 123456789012345678")
        print("  python mx_moni.py 一键撤单")
        sys.exit(1)

    query = ' '.join(sys.argv[1:])
    output_prefix = f"mx_moni_{query.replace(' ', '_')}"

    # 根据意图识别调用不同接口
    if any(word in query for word in ['持仓', '我的持仓', '持仓情况']):
        make_request('/api/claw/mockTrading/positions', {'moneyUnit': 1}, output_prefix)
    elif any(word in query for word in ['资金', '我的资金', '账户余额', '资金情况']):
        make_request('/api/claw/mockTrading/balance', {'moneyUnit': 1}, output_prefix)
    elif any(word in query for word in ['委托', '我的委托', '订单', '委托记录']):
        make_request('/api/claw/mockTrading/orders', {'fltOrderDrt': 0, 'fltOrderStatus': 0}, output_prefix)
    elif any(word in query for word in ['买入', '买进', '建仓']):
        stock_code, price, quantity, is_market = parse_buy_sell(query)
        if not stock_code or not quantity:
            print("错误: 无法解析买入指令，请确保包含股票代码(6位)和数量(100的整数倍)")
            print("示例: python mx_moni.py 买入 600519 价格 1700 数量 100 股")
            print("示例: python mx_moni.py 市价买入 600519 100 股")
            sys.exit(1)
        if quantity < 0:
            print("错误: 买入不支持'全部'，请指定数量")
            sys.exit(1)
        if not is_market and price is None:
            print("错误: 限价买入需要提供价格，或使用市价买入")
            sys.exit(1)
        if quantity % 100 != 0:
            print(f"错误: 委托数量({quantity})必须为100的整数倍")
            sys.exit(1)

        body = {
            'type': 'buy',
            'stockCode': stock_code,
            'quantity': quantity,
            'useMarketPrice': is_market
        }
        if not is_market and price:
            body['price'] = price

        make_request('/api/claw/mockTrading/trade', body, output_prefix)
    elif any(word in query for word in ['卖出', '抛售', '减仓']):
        stock_code, price, quantity, is_market = parse_buy_sell(query)
        if not stock_code or not quantity:
            print("错误: 无法解析卖出指令，请确保包含股票代码(6位)和数量(100的整数倍)")
            print("示例: python mx_moni.py 卖出 600519 价格 1750 数量 100 股")
            print("示例: python mx_moni.py 市价卖出 600519 100 股")
            print("示例: python mx_moni.py 市价卖出 000063 全部")
            sys.exit(1)
        if quantity < 0:
            # 全部卖出 = 先查持仓拿可用数量
            make_request('/api/claw/mockTrading/positions', {'moneyUnit': 1}, f'{output_prefix}_poscheck')
            pos_file = os.path.join(OUTPUT_DIR, f'{output_prefix}_poscheck_raw.json')
            with open(pos_file, encoding='utf-8') as f:
                pos_data = json.load(f)
            pos_list = (pos_data.get('data') or {}).get('posList', [])
            avail = 0
            for p in pos_list:
                if str(p.get('secCode', '')).zfill(6) == stock_code:
                    avail = int(p.get('availCount') or p.get('count') or 0)
                    break
            if avail <= 0:
                print(f"错误: 未找到股票 {stock_code} 的可卖持仓")
                sys.exit(1)
            quantity = avail
            is_market = True  # 全部清仓默认市价
        if not is_market and price is None and quantity > 0:
            print("错误: 限价卖出需要提供价格，或使用市价卖出（推荐）")
            sys.exit(1)
        if quantity % 100 != 0:
            print(f"错误: 委托数量({quantity})必须为100的整数倍")
            sys.exit(1)

        body = {
            'type': 'sell',
            'stockCode': stock_code,
            'quantity': quantity,
            'useMarketPrice': is_market
        }
        if not is_market and price:
            body['price'] = price

        make_request('/api/claw/mockTrading/trade', body, output_prefix)
    elif any(word in query for word in ['撤单', '撤销', '撤单']):
        order_id, stock_code, is_all = parse_cancel(query)
        if is_all:
            body = {'type': 'all'}
            make_request('/api/claw/mockTrading/cancel', body, output_prefix)
        else:
            if not order_id:
                print("错误: 请提供委托编号，或使用一键撤单撤销所有未成交委托")
                print("示例: python mx_moni.py 撤单 260854300000078983")
                print("示例: python mx_moni.py 一键撤单")
                sys.exit(1)
            body = {
                'type': 'order',
                'orderId': order_id
            }
            if stock_code:
                body['stockCode'] = stock_code
            make_request('/api/claw/mockTrading/cancel', body, output_prefix)
    elif any(word in query for word in ['行情', '股价', '当前价', '最新价', '报价', '实时', '价格']):
        # 查单个股票最新行情 — 从 MX 持仓数据拿当前价
        stock_code, _, _, _ = parse_buy_sell(query)
        if not stock_code:
            # 从存量的 posList 中查
            make_request('/api/claw/mockTrading/positions', {'moneyUnit': 1}, f'{output_prefix}_poscheck')
            pos_file = os.path.join(OUTPUT_DIR, f'{output_prefix}_poscheck_raw.json')
            with open(pos_file, encoding='utf-8') as f:
                pos_data = json.load(f)
            pos_list = (pos_data.get('data') or {}).get('posList', [])
            print(f"\n{'名称':<10} {'代码':<8} {'现价':>8} {'涨跌幅':>8} {'持仓':>8} {'市值':>10}")
            print('-' * 60)
            for p in pos_list:
                name = p.get('secName', '?')
                code = str(p.get('secCode', '')).zfill(6)
                cur = float(p.get('price', 0)) / 100
                pct = float(p.get('dayProfitPct', 0))
                cnt = int(p.get('count', 0))
                val = float(p.get('value', 0))
                print(f'{name:<10} {code:<8} ¥{cur:>6.2f} {pct:>+7.2f}% {cnt:>6}股 ¥{val:>8.0f}')
        else:
            # 单股票用 MX 行情接口
            make_request('/api/claw/mockTrading/positions', {'moneyUnit': 1}, f'{output_prefix}_poscheck')
            pos_file = os.path.join(OUTPUT_DIR, f'{output_prefix}_poscheck_raw.json')
            with open(pos_file, encoding='utf-8') as f:
                pos_data = json.load(f)
            pos_list = (pos_data.get('data') or {}).get('posList', [])
            for p in pos_list:
                if str(p.get('secCode', '')).zfill(6) == stock_code:
                    cur = float(p.get('price', 0)) / 100
                    pct = float(p.get('dayProfitPct', 0))
                    name = p.get('secName', '?')
                    print(f"\n{name}({stock_code}) ¥{cur:.2f} ({pct:+.2f}%)")
                    break
            else:
                print(f"未找到 {stock_code} 的行情数据，当前非交易时间或未持仓")
    elif any(word in query for word in ['清仓', '一键清仓', '全卖']):
        # 先查持仓取所有股票
        make_request('/api/claw/mockTrading/positions', {'moneyUnit': 1}, f'{output_prefix}_poscheck')
        pos_file = os.path.join(OUTPUT_DIR, f'{output_prefix}_poscheck_raw.json')
        with open(pos_file, encoding='utf-8') as f:
            pos_data = json.load(f)
        pos_list = (pos_data.get('data') or {}).get('posList', [])
        if not pos_list:
            print("当前无持仓，无需清仓")
            sys.exit(0)
        print(f"\n将清仓 {len(pos_list)} 只股票：")
        for p in pos_list:
            name = p.get('secName', '?')
            code = str(p.get('secCode', '')).zfill(6)
            count = int(p.get('availCount') or p.get('count') or 0)
            print(f"  {name}({code}): {count}股")
        print("\n开始逐只市价清仓...")
        for p in pos_list:
            code = str(p.get('secCode', '')).zfill(6)
            name = p.get('secName', '?')
            count = int(p.get('availCount') or p.get('count') or 0)
            if count <= 0:
                print(f"  跳过 {name}: 无可卖数量")
                continue
            from time import sleep
            sleep(1)  # 避免频率限制
            final_body = {
                'type': 'sell',
                'stockCode': code,
                'quantity': count,
                'useMarketPrice': True
            }
            try:
                full_url = f"{MX_API_URL}/api/claw/mockTrading/trade"
                headers = {'apikey': MX_APIKEY, 'Content-Type': 'application/json'}
                resp = requests.post(full_url, headers=headers, json=final_body)
                result = resp.json()
                if result.get('success') or str(result.get('code')) == '200':
                    print(f"  ✅ 清仓 {name}({code}): {count}股 成功")
                else:
                    print(f"  ❌ 清仓 {name}({code}): {result.get('message','?')}")
            except Exception as e:
                print(f"  ❌ 清仓 {name}({code}): 网络错误 {str(e)}")
        print("\n清仓完成")
    else:
        print("无法识别意图，请使用以下操作之一：")
        print("  持仓查询: 我的持仓 / 查询持仓")
        print("  资金查询: 我的资金 / 查询资金")
        print("  委托查询: 我的委托 / 查询委托")
        print("  行情查询: 行情 / 查行情 [代码]")
        print("  买入操作: 买入 [股票代码] [价格] [数量] 股 / 市价买入 [股票代码] [数量] 股")
        print("  卖出操作: 卖出 [股票代码] [价格] [数量] 股 / 市价卖出 [股票代码] [数量] 股")
        print("  卖出全部: 市价卖出 [代码] 全部")
        print("  一键清仓: 清仓")
        print("  撤单操作: 撤单 [委托编号] / 一键撤单")
        sys.exit(1)

if __name__ == '__main__':
    main()

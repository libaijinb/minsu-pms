"""临时 API 端到端验证：覆盖用户/房源/订单状态机/并发占房/派工冲突/查房/月结/隔离。跑完即删。"""
import json
import threading
import urllib.error
import urllib.request
from datetime import date, timedelta

BASE = 'http://127.0.0.1:8000/api'
TODAY = date.today()
PASSWORD = '123456'

failed = 0


def check(name, cond, extra=''):
    global failed
    print(f"{'PASS' if cond else 'FAIL'}  {name}{'' if cond else '  ' + str(extra)[:200]}")
    if not cond:
        failed += 1


def call(method, path, data=None, token=None):
    body = json.dumps(data).encode('utf-8') if data is not None else None
    req = urllib.request.Request(BASE + path, data=body, method=method)
    req.add_header('Content-Type', 'application/json')
    if token:
        req.add_header('Authorization', f'Bearer {token}')
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode('utf-8')
            return resp.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as e:
        raw = e.read().decode('utf-8')
        try:
            return e.code, (json.loads(raw) if raw else {})
        except json.JSONDecodeError:
            return e.code, {'raw': raw[:200]}


def login(username):
    s, r = call('POST', '/auth/login/', {'username': username, 'password': PASSWORD})
    assert s == 200, f'login {username} failed: {r}'
    return r['access']


tokens = {u: login(u) for u in ['guest01', 'landlord01', 'operator01', 'cleaner01', 'finance01']}
guest, landlord, operator = tokens['guest01'], tokens['landlord01'], tokens['operator01']

# 1. 游客浏览房源（无需登录）
s, r = call('GET', '/listings/')
check('游客可浏览已上架房源', s == 200 and r['count'] == 3, r)
listing_id = r['results'][0]['id']

# 2. 动态查找空闲日期段：从 30 天后起找第一段连续 2 晚可订（保证脚本可重复运行）
s, r = call('GET', f'/listings/{listing_id}/calendar/?start={TODAY + timedelta(days=30)}&end={TODAY + timedelta(days=58)}')
avail = [c['date'] for c in r if c['status'] == 'available']
ci = co = None
for i in range(len(avail) - 1):
    d1, d2 = date.fromisoformat(avail[i]), date.fromisoformat(avail[i + 1])
    if (d2 - d1).days == 1:
        ci, co = d1, d2 + timedelta(days=1)
        break
assert ci, 'no available slot found'

# 3. 客人创建订单
s, r = call('POST', '/orders/', {'listing': listing_id, 'checkin_date': str(ci),
           'checkout_date': str(co), 'guests_count': 2}, token=guest)
check('客人创建订单', s == 201 and r['status'] == 'pending_pay', r)
order_no = r['order_no']

# 4. 日历被占用
s, r = call('GET', f'/listings/{listing_id}/calendar/?start={ci}&end={co}')
booked = [c for c in r if c['status'] == 'booked']
check('下单后日历置已订', len(booked) == 2, r)

# 5. 并发抢订同一晚：5 线程只有 1 单成功（核心技术难点验证）
s, r = call('GET', f'/listings/{listing_id}/calendar/?start={TODAY + timedelta(days=30)}&end={TODAY + timedelta(days=58)}')
avail = [c['date'] for c in r if c['status'] == 'available']
race_ci = date.fromisoformat(avail[-1]) if avail else None
assert race_ci, 'no available night for race test'
results = []


def grab():
    results.append(call('POST', '/orders/',
                        {'listing': listing_id, 'checkin_date': str(race_ci),
                         'checkout_date': str(race_ci + timedelta(days=1)),
                         'guests_count': 1}, token=guest)[0])


threads = [threading.Thread(target=grab) for _ in range(5)]
[t.start() for t in threads]
[t.join() for t in threads]
ok = sum(1 for c in results if c == 201)
check('并发抢订仅 1 单成功（零超售）', ok == 1, results)

# 6. 同一区间重复预订被拒（日历已占用）
s, r = call('POST', '/orders/', {'listing': listing_id, 'checkin_date': str(ci),
           'checkout_date': str(co), 'guests_count': 2}, token=guest)
check('重复预订同区间被拒', s == 409, r)

# 7. 支付 -> 确认 -> 入住 -> 退房 全链路
s, r = call('POST', f'/orders/{order_no}/pay/', {}, token=guest)
check('支付成功转待确认', s == 200 and r['status'] == 'pending_confirm', r)
s, r = call('POST', f'/orders/{order_no}/confirm/', {}, token=landlord)
check('房东确认订单', s == 200 and r['status'] == 'confirmed', r)
s, r = call('POST', f'/orders/{order_no}/checkin/',
            {'guest_names': ['测试客人'], 'id_card': '330102199001011234',
             'phone': '13800002222', 'deposit_amount': 500}, token=operator)
check('运营办理入住', s == 200 and r['status'] == 'checked_in' and r['checkin']['deposit_status'] == 'held', r)
s, r = call('POST', f'/orders/{order_no}/checkout/', {}, token=operator)
check('退房转已退房', s == 200 and r['status'] == 'checked_out', r)
check('退房自动生成清洁任务', r.get('cleaning') is not None, r)

# 8. 非法状态转换被拒（已退房不能再支付）
s, r = call('POST', f'/orders/{order_no}/pay/', {}, token=guest)
check('非法状态转换被拒绝', s == 400, r)

# 9. 运营查房：定损 80 -> 自动生成维修工单 + 押金扣减
s, r = call('POST', '/inspections/submit/', {
    'order_no': order_no,
    'items': [{'name': '卧室卫生', 'result': 'normal', 'note': '', 'amount': 0},
              {'name': '电视屏幕', 'result': 'damage', 'note': '碎裂', 'amount': 80}]}, token=operator)
check('查房提交成功', s == 201 and float(r['damage_total']) == 80 and r['conclusion'] == 'fail', r)
s, r = call('GET', '/repair-tickets/', token=operator)
inspection_tickets = [t for t in r['results'] if t['source'] == 'inspection' and t['order_no'] == order_no]
check('定损自动生成维修工单', len(inspection_tickets) >= 1, r)
s, r = call('GET', f'/orders/{order_no}/', token=operator)
check('押金状态转已扣减', r['checkin']['deposit_status'] == 'deducted', r.get('checkin'))

# 10. 派工冲突：保洁明天上午已有任务（种子数据），再派同时段任务应 409
s, r = call('GET', '/cleaning-tasks/', token=operator)
pending = [t for t in r['results'] if t['status'] == 'pending']
conflict_slot = [t for t in r['results'] if t['cleaner'] is not None and t['status'] == 'assigned']
s, r = call('GET', '/users/?role=cleaner', token=operator)
cleaner_id = r['results'][0]['id']
# 动态找一个该保洁未占用的下午时段（唯一约束与状态无关，必须避开历史占用）
occupied = {(t['task_date'], t['slot']) for t in call('GET', '/cleaning-tasks/', token=operator)[1]['results']
            if t['cleaner'] == cleaner_id}
free_date = TODAY + timedelta(days=40)
while (str(free_date), 'afternoon') in occupied:
    free_date += timedelta(days=1)
s, r = call('POST', f'/cleaning-tasks/{pending[0]["id"]}/assign/',
            {'cleaner': cleaner_id, 'task_date': conflict_slot[0]['task_date'],
             'slot': conflict_slot[0]['slot']}, token=operator)
check('派工冲突被唯一约束拦截', s == 409, r)
s, r = call('POST', f'/cleaning-tasks/{pending[0]["id"]}/assign/',
            {'cleaner': cleaner_id, 'task_date': str(free_date),
             'slot': 'afternoon'}, token=operator)
check('无人占用的时段可派工', s == 200 and r['status'] == 'assigned', r)

# 11. 保洁完成任务 -> 运营复核
task_id = r['id']
s, r = call('POST', f'/cleaning-tasks/{task_id}/finish/', {'photos': ['https://picsum.photos/200']},
            token=tokens['cleaner01'])
check('保洁提交完成', s == 200 and r['status'] == 'reviewing', r)
s, r = call('POST', f'/cleaning-tasks/{task_id}/review/', {}, token=operator)
check('运营复核关单', s == 200 and r['status'] == 'done', r)

# 12. 月结：landlord01 + 本测试订单退房所在月（脚本动态找的日期可能不在当前月）
s, r = call('GET', '/users/?role=landlord', token=operator)
landlord_id = r['results'][0]['id']
s, r = call('GET', f'/orders/{order_no}/', token=operator)
period = r['checkout_date'][:7]  # 'YYYY-MM'
s, r = call('POST', '/settlements/run/', {'landlord': landlord_id, 'period': period}, token=operator)
check('月结生成结算单', s in (200, 201) and float(r.get('net_amount', 0)) > 0, r)
settlement_id = r['id']
s, r = call('POST', f'/settlements/{settlement_id}/payout/', {}, token=tokens['finance01'])
check('财务分账成功', s == 200 and r['status'] == 'success', r)

# 13. 数据隔离：房东只见自己房源订单
s, r = call('GET', '/orders/', token=landlord)
check('房东订单列表按数据范围隔离', s == 200, r)

# 14. 评价：用本测试创建的已退房订单（order_no）
s, r = call('POST', '/reviews/', {'order': order_no, 'type': 'guest_to_listing',
                                  'rating': 5, 'content': '测试评价：房间很干净'}, token=guest)
check('客人评价提交', s == 201, r)
s, r = call('POST', '/reviews/', {'order': order_no, 'type': 'guest_to_listing', 'rating': 4}, token=guest)
check('重复评价被拒', s == 400, r)
s, r = call('GET', f'/reviews/?listing={listing_id}')
check('评价列表公开可读', s == 200 and len(r['results']) >= 1, r)

# 15. 统计与站内信
s, r = call('GET', '/stats/overview/', token=landlord)
check('经营统计 6 个月趋势', s == 200 and len(r['trend']) == 6, r)
s, r = call('GET', '/notifications/', token=guest)
check('站内信列表', s == 200, r)
s, r = call('POST', '/notifications/read-all/', {}, token=guest)
check('全部已读', s == 200, r)

# 16. 未登录 401
s, r = call('GET', '/orders/')
check('未登录访问订单 401', s == 401, r)

print(f"\n{'=== 全部通过 ===' if failed == 0 else f'=== {failed} 项失败 ==='}")

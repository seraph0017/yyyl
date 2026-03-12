"""
某露营地 — Celery 异步任务模块

任务分类：
- inventory: 库存（开票/释放/一致性校验）
- order: 订单（超时取消/自动完成）
- member: 会员（到期处理/积分过期）
- finance: 财务（收入确认/押金超时）
- notification: 通知（行程提醒/活动提醒）
- stats: 统计（Dashboard/报表）
- cleanup: 清理（Token/日志归档）
"""

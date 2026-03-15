"""
秒杀增强路由

C端：
- PUT  /api/v1/orders/seckill/prefill               — 保存秒杀预填数据（👤 用户）
- GET  /api/v1/orders/seckill/prefill/{product_id}   — 获取已保存的预填数据（👤 用户）
- GET  /api/v1/products/{product_id}/seckill-status  — 获取秒杀实时状态（🌐 游客）

B端：
- GET  /api/v1/admin/seckill/monitor/{product_id}    — 秒杀实时监控（🔑 管理员）
- GET  /api/v1/admin/seckill/report/{product_id}     — 秒杀复盘报告（🔑 管理员）
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query, Request

from middleware.auth import get_current_admin, get_current_user, get_optional_user
from middleware.site import get_site_id
from models.admin import AdminUser
from models.user import User
from redis_client import get_redis
from schemas.common import ResponseModel
from schemas.seckill import (
    SeckillMonitorResponse,
    SeckillPrefillResponse,
    SeckillPrefillSave,
    SeckillStatusResponse,
)
from services import seckill_service

router = APIRouter(tags=["秒杀"])


# ========== C端接口 ==========


@router.put("/api/v1/orders/seckill/prefill", summary="保存秒杀预填数据")
async def save_seckill_prefill(
    body: SeckillPrefillSave,
    request: Request,
    user: User = Depends(get_current_user),
):
    """用户在秒杀开始前预填出行人、联系方式等信息

    秒杀开始时直接提交，减少操作时间。数据保存在 Redis，24小时过期。
    """
    redis = get_redis()
    await seckill_service.save_seckill_prefill(
        redis,
        product_id=body.product_id,
        user_id=user.id,
        data=body.model_dump(),
    )
    return ResponseModel.success(message="预填数据保存成功")


@router.get(
    "/api/v1/orders/seckill/prefill/{product_id}",
    summary="获取秒杀预填数据",
)
async def get_seckill_prefill(
    product_id: int,
    request: Request,
    user: User = Depends(get_current_user),
):
    """获取用户已保存的秒杀预填数据"""
    redis = get_redis()
    data = await seckill_service.get_seckill_prefill(
        redis,
        product_id=product_id,
        user_id=user.id,
    )
    if data is None:
        return ResponseModel.success(data=None, message="暂无预填数据")
    result = SeckillPrefillResponse.model_validate(data)
    return ResponseModel.success(data=result)


@router.get(
    "/api/v1/products/{product_id}/seckill-status",
    summary="获取秒杀实时状态",
)
async def get_seckill_status(
    product_id: int,
    request: Request,
    booking_date: Optional[str] = Query(
        default=None, description="预约日期（YYYY-MM-DD）",
    ),
    user: Optional[User] = Depends(get_optional_user),
):
    """C端获取秒杀实时状态：剩余库存、在线人数、状态（游客可访问）"""
    redis = get_redis()
    data = await seckill_service.get_seckill_status(
        redis,
        product_id=product_id,
        booking_date=booking_date,
    )
    result = SeckillStatusResponse.model_validate(data)
    return ResponseModel.success(data=result)


# ========== B端接口 ==========


@router.get(
    "/api/v1/admin/seckill/monitor/{product_id}",
    summary="秒杀实时监控",
)
async def get_seckill_monitor(
    product_id: int,
    request: Request,
    booking_date: Optional[str] = Query(
        default=None, description="预约日期（YYYY-MM-DD）",
    ),
    admin: AdminUser = Depends(get_current_admin),
):
    """B端秒杀实时监控：在线人数、库存、已创建/已支付订单数、峰值QPS"""
    redis = get_redis()
    data = await seckill_service.get_seckill_monitor(
        redis,
        product_id=product_id,
        booking_date=booking_date,
    )
    result = SeckillMonitorResponse.model_validate(data)
    return ResponseModel.success(data=result)


@router.get(
    "/api/v1/admin/seckill/report/{product_id}",
    summary="秒杀复盘报告",
)
async def get_seckill_report(
    product_id: int,
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
):
    """B端秒杀复盘报告

    TODO: 实现完整的秒杀复盘报告（转化率、支付率、响应时间分布等）
    """
    redis = get_redis()
    # 复用监控数据作为基础复盘信息
    data = await seckill_service.get_seckill_monitor(
        redis,
        product_id=product_id,
    )
    result = SeckillMonitorResponse.model_validate(data)
    return ResponseModel.success(data=result)

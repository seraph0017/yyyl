"""
创建初始商品数据的种子脚本

包含:
- 6个日常营位 (daily_camping)
- 2个活动营位 (event_camping)
- 3个装备租赁 (rental)
- 2个日常活动 (daily_activity)
- 1个特定活动 (special_activity)
- 3个营地小商店 (shop)
- 1个周边商品 (merchandise)
- Banner 和首页配置

用法:
    cd server
    python seed_products.py
"""

import asyncio
import sys
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import text

from database import async_session_factory, engine


# ---- 营位数据 ----

PRODUCTS = [
    # ===== 日常露营 (daily_camping) =====
    {
        "name": "A区阳光营位 · 有电有木平台",
        "type": "daily_camping",
        "booking_mode": "by_position",
        "status": "on_sale",
        "base_price": 168.00,
        "images": '[{"url": "/images/campsite-a1.jpg", "sort_order": 1}]',
        "description": "<p>A区精品营位，配备独立电源和高架木平台，日照充足，视野开阔。适合2-4人家庭或朋友团队。</p>",
        "category": "daily_camping",
        "sort_order": 1,
        "ext_camping": {
            "has_electricity": True,
            "has_platform": True,
            "sun_exposure": "sunny",
            "position_name": "A01",
            "area": "A区",
            "max_persons": 4,
        },
    },
    {
        "name": "A区草坪营位 · 有电无平台",
        "type": "daily_camping",
        "booking_mode": "by_position",
        "status": "on_sale",
        "base_price": 128.00,
        "images": '[{"url": "/images/campsite-a2.jpg", "sort_order": 1}]',
        "description": "<p>A区草坪营位，配备独立电源，天然草地，亲近自然。适合2-4人。</p>",
        "category": "daily_camping",
        "sort_order": 2,
        "ext_camping": {
            "has_electricity": True,
            "has_platform": False,
            "sun_exposure": "mixed",
            "position_name": "A02",
            "area": "A区",
            "max_persons": 4,
        },
    },
    {
        "name": "B区林间营位 · 自然风",
        "type": "daily_camping",
        "booking_mode": "by_position",
        "status": "on_sale",
        "base_price": 98.00,
        "images": '[{"url": "/images/campsite-b1.jpg", "sort_order": 1}]',
        "description": "<p>B区林间营位，被绿荫环绕，夏日凉爽，适合追求静谧的露营爱好者。无电源供应。</p>",
        "category": "daily_camping",
        "sort_order": 3,
        "ext_camping": {
            "has_electricity": False,
            "has_platform": False,
            "sun_exposure": "shaded",
            "position_name": "B01",
            "area": "B区",
            "max_persons": 6,
        },
    },
    {
        "name": "C区湖景营位 · 有电有木平台",
        "type": "daily_camping",
        "booking_mode": "by_position",
        "status": "on_sale",
        "base_price": 238.00,
        "images": '[{"url": "/images/campsite-c1.jpg", "sort_order": 1}]',
        "description": "<p>C区湖景精品营位，独享湖景一线位置，配备电源和木平台。营地最佳景观位，非常适合拍照打卡。</p>",
        "category": "daily_camping",
        "sort_order": 4,
        "ext_camping": {
            "has_electricity": True,
            "has_platform": True,
            "sun_exposure": "sunny",
            "position_name": "C01",
            "area": "C区",
            "max_persons": 4,
        },
    },
    {
        "name": "D区亲子营位 · 有电有木平台",
        "type": "daily_camping",
        "booking_mode": "by_position",
        "status": "on_sale",
        "base_price": 198.00,
        "images": '[{"url": "/images/campsite-d1.jpg", "sort_order": 1}]',
        "description": "<p>D区亲子专属营位，紧邻儿童乐园和卫生间，配备电源和木平台。安全围栏设计，专为带娃家庭打造。</p>",
        "category": "daily_camping",
        "sort_order": 5,
        "ext_camping": {
            "has_electricity": True,
            "has_platform": True,
            "sun_exposure": "mixed",
            "position_name": "D01",
            "area": "D区",
            "max_persons": 6,
        },
    },
    {
        "name": "E区山顶营位 · 观星位",
        "type": "daily_camping",
        "booking_mode": "by_position",
        "status": "on_sale",
        "base_price": 268.00,
        "images": '[{"url": "/images/campsite-e1.jpg", "sort_order": 1}]',
        "description": "<p>E区山顶观星营位，全营地最高点，远离光污染，夜晚可裸眼观星。有木平台但无电源（可租用移动电源）。</p>",
        "category": "daily_camping",
        "sort_order": 6,
        "ext_camping": {
            "has_electricity": False,
            "has_platform": True,
            "sun_exposure": "sunny",
            "position_name": "E01",
            "area": "E区",
            "max_persons": 4,
        },
    },

    # ===== 活动露营 (event_camping) =====
    {
        "name": "春日露营季 · 花海营位",
        "type": "event_camping",
        "booking_mode": "by_quantity",
        "status": "on_sale",
        "base_price": 188.00,
        "images": '[{"url": "/images/event-spring.jpg", "sort_order": 1}]',
        "description": "<p>🌸 春日限定！花海中的露营体验，含营位+篝火晚会+早餐。限时特惠，先到先得！</p>",
        "category": "event_camping",
        "sort_order": 10,
        "is_seckill": False,
        "ext_camping": {
            "has_electricity": True,
            "has_platform": True,
            "sun_exposure": "sunny",
            "area": "活动区",
            "max_persons": 4,
            "event_start_date": date.today() + timedelta(days=14),
            "event_end_date": date.today() + timedelta(days=44),
        },
    },
    {
        "name": "仲夏夜星空音乐节 · 限定营位",
        "type": "event_camping",
        "booking_mode": "by_quantity",
        "status": "on_sale",
        "base_price": 298.00,
        "images": '[{"url": "/images/event-music.jpg", "sort_order": 1}]',
        "description": "<p>🎶 星空下的音乐派对！含营位+音乐节门票+深夜DJ+特调饮品。仅限100组名额，秒杀开抢！</p>",
        "category": "event_camping",
        "sort_order": 11,
        "is_seckill": True,
        "seckill_payment_timeout": 300,
        "ext_camping": {
            "has_electricity": True,
            "has_platform": True,
            "sun_exposure": "mixed",
            "area": "音乐节专区",
            "max_persons": 6,
            "event_start_date": date.today() + timedelta(days=30),
            "event_end_date": date.today() + timedelta(days=32),
        },
    },

    # ===== 装备租赁 (rental) =====
    {
        "name": "帐篷租赁 · 4人家庭帐",
        "type": "rental",
        "booking_mode": "by_quantity",
        "status": "on_sale",
        "base_price": 120.00,
        "images": '[{"url": "/images/rental-tent.jpg", "sort_order": 1}]',
        "description": "<p>4人家庭帐篷，含地钉地垫。双层防雨设计，通风透气，展开尺寸 240x210x130cm。</p>",
        "category": "equipment_rental",
        "sort_order": 20,
        "require_disclaimer": False,
        "require_camping_ticket": True,
        "ext_rental": {
            "deposit_amount": 200.00,
            "rental_category": "overnight",
            "damage_config": '[{"level": "轻微磨损", "rate": 0.1}, {"level": "严重损坏", "rate": 0.5}, {"level": "无法修复", "rate": 1.0}]',
        },
    },
    {
        "name": "天幕租赁 · 六角蝶形",
        "type": "rental",
        "booking_mode": "by_quantity",
        "status": "on_sale",
        "base_price": 80.00,
        "images": '[{"url": "/images/rental-tarp.jpg", "sort_order": 1}]',
        "description": "<p>六角蝶形天幕，遮阳面积约12㎡，银胶涂层UPF50+。含天幕杆和地钉。</p>",
        "category": "equipment_rental",
        "sort_order": 21,
        "require_disclaimer": False,
        "require_camping_ticket": True,
        "ext_rental": {
            "deposit_amount": 150.00,
            "rental_category": "overnight",
            "damage_config": '[{"level": "轻微磨损", "rate": 0.1}, {"level": "严重损坏", "rate": 0.5}]',
        },
    },
    {
        "name": "露营桌椅套装 · 一桌四椅",
        "type": "rental",
        "booking_mode": "by_quantity",
        "status": "on_sale",
        "base_price": 50.00,
        "images": '[{"url": "/images/rental-table.jpg", "sort_order": 1}]',
        "description": "<p>铝合金折叠桌+4把月亮椅。桌子 120x60cm，承重50kg。轻便易搬运。</p>",
        "category": "equipment_rental",
        "sort_order": 22,
        "require_disclaimer": False,
        "require_camping_ticket": True,
        "ext_rental": {
            "deposit_amount": 100.00,
            "rental_category": "furniture",
            "damage_config": '[{"level": "轻微磨损", "rate": 0.1}, {"level": "严重损坏", "rate": 0.5}]',
        },
    },

    # ===== 日常活动 (daily_activity) =====
    {
        "name": "皮划艇体验 · 单人艇",
        "type": "daily_activity",
        "booking_mode": "by_quantity",
        "status": "on_sale",
        "base_price": 88.00,
        "images": '[{"url": "/images/activity-kayak.jpg", "sort_order": 1}]',
        "description": "<p>单人皮划艇体验，含救生衣和教练指导。湖面巡游约40分钟，初学者也能轻松上手。</p>",
        "category": "daily_activity",
        "sort_order": 30,
        "require_disclaimer": True,
        "ext_activity": {
            "booking_unit": "person",
            "time_slots": '[{"start": "09:00", "end": "09:40", "capacity": 8}, {"start": "10:00", "end": "10:40", "capacity": 8}, {"start": "14:00", "end": "14:40", "capacity": 8}, {"start": "15:00", "end": "15:40", "capacity": 8}]',
        },
    },
    {
        "name": "射箭体验 · 10支装",
        "type": "daily_activity",
        "booking_mode": "by_quantity",
        "status": "on_sale",
        "base_price": 58.00,
        "images": '[{"url": "/images/activity-archery.jpg", "sort_order": 1}]',
        "description": "<p>专业射箭场体验，含10支箭+教练指导。适合6岁以上，需佩戴护具。</p>",
        "category": "daily_activity",
        "sort_order": 31,
        "require_disclaimer": True,
        "ext_activity": {
            "booking_unit": "person",
            "time_slots": '[{"start": "09:00", "end": "09:30", "capacity": 6}, {"start": "10:00", "end": "10:30", "capacity": 6}, {"start": "14:00", "end": "14:30", "capacity": 6}, {"start": "15:00", "end": "15:30", "capacity": 6}, {"start": "16:00", "end": "16:30", "capacity": 6}]',
        },
    },

    # ===== 特定活动 (special_activity) =====
    {
        "name": "亲子手作工坊 · 植物拓印",
        "type": "special_activity",
        "booking_mode": "by_quantity",
        "status": "on_sale",
        "base_price": 128.00,
        "images": '[{"url": "/images/activity-workshop.jpg", "sort_order": 1}]',
        "description": "<p>🌿 亲子植物拓印手作，用营地里的花草叶片创作独一无二的帆布包。含材料包+老师指导。每场限12组家庭。</p>",
        "category": "special_activity",
        "sort_order": 35,
        "require_disclaimer": False,
        "ext_activity": {
            "booking_unit": "group",
            "time_slots": '[{"start": "14:00", "end": "16:00", "capacity": 12}]',
            "event_date": date.today() + timedelta(days=7),
        },
    },

    # ===== 营地小商店 (shop) =====
    {
        "name": "营地柴火 · 一捆(约5kg)",
        "type": "shop",
        "booking_mode": None,
        "status": "on_sale",
        "base_price": 25.00,
        "images": '[{"url": "/images/shop-firewood.jpg", "sort_order": 1}]',
        "description": "<p>天然劈柴，约5公斤一捆。篝火、壁炉专用，干燥易燃。</p>",
        "category": "camp_shop",
        "sort_order": 40,
        "require_disclaimer": False,
        "require_camping_ticket": False,
        "ext_shop": {
            "has_sku": False,
            "shipping_required": False,
            "shop_type": "onsite",
        },
    },
    {
        "name": "冰镇饮料 · 多口味",
        "type": "shop",
        "booking_mode": None,
        "status": "on_sale",
        "base_price": 5.00,
        "images": '[{"url": "/images/shop-drinks.jpg", "sort_order": 1}]',
        "description": "<p>冰箱现取，可乐/雪碧/矿泉水/果汁，露营解渴必备。</p>",
        "category": "camp_shop",
        "sort_order": 41,
        "require_disclaimer": False,
        "require_camping_ticket": False,
        "ext_shop": {
            "has_sku": True,
            "spec_definitions": '[{"name": "口味", "values": ["可乐", "雪碧", "矿泉水", "橙汁"]}]',
            "shipping_required": False,
            "shop_type": "onsite",
        },
    },
    {
        "name": "速食泡面 · 多口味",
        "type": "shop",
        "booking_mode": None,
        "status": "on_sale",
        "base_price": 8.00,
        "images": '[{"url": "/images/shop-noodles.jpg", "sort_order": 1}]',
        "description": "<p>深夜必备！多种口味方便面，可提供热水泡制。</p>",
        "category": "camp_shop",
        "sort_order": 42,
        "require_disclaimer": False,
        "require_camping_ticket": False,
        "ext_shop": {
            "has_sku": True,
            "spec_definitions": '[{"name": "口味", "values": ["红烧牛肉", "酸菜牛肉", "香辣", "海鲜"]}]',
            "shipping_required": False,
            "shop_type": "onsite",
        },
    },

    # ===== 周边商品 (merchandise) =====
    {
        "name": "一月一露品牌T恤 · 纯棉",
        "type": "merchandise",
        "booking_mode": None,
        "status": "on_sale",
        "base_price": 128.00,
        "images": '[{"url": "/images/merch-tshirt.jpg", "sort_order": 1}]',
        "description": "<p>100%纯棉品牌T恤，230g厚度，前胸露营图案印花。支持邮寄。</p>",
        "category": "merchandise",
        "sort_order": 50,
        "require_disclaimer": False,
        "require_camping_ticket": False,
        "ext_shop": {
            "has_sku": True,
            "spec_definitions": '[{"name": "颜色", "values": ["森林绿", "卡其", "白色"]}, {"name": "尺码", "values": ["S", "M", "L", "XL"]}]',
            "shipping_required": True,
            "shop_type": "online",
        },
    },
]


# ---- SKU 数据 ----

SKUS = {
    # 按商品名匹配
    "冰镇饮料 · 多口味": [
        {"sku_code": "DRINK-COLA", "spec_values": '{"口味": "可乐"}', "price": 5.00, "stock": 200},
        {"sku_code": "DRINK-SPRITE", "spec_values": '{"口味": "雪碧"}', "price": 5.00, "stock": 200},
        {"sku_code": "DRINK-WATER", "spec_values": '{"口味": "矿泉水"}', "price": 3.00, "stock": 300},
        {"sku_code": "DRINK-OJ", "spec_values": '{"口味": "橙汁"}', "price": 8.00, "stock": 100},
    ],
    "速食泡面 · 多口味": [
        {"sku_code": "NOODLE-BEEF", "spec_values": '{"口味": "红烧牛肉"}', "price": 8.00, "stock": 100},
        {"sku_code": "NOODLE-PICKLE", "spec_values": '{"口味": "酸菜牛肉"}', "price": 8.00, "stock": 100},
        {"sku_code": "NOODLE-SPICY", "spec_values": '{"口味": "香辣"}', "price": 8.00, "stock": 80},
        {"sku_code": "NOODLE-SEAFOOD", "spec_values": '{"口味": "海鲜"}', "price": 8.00, "stock": 80},
    ],
    "一月一露品牌T恤 · 纯棉": [
        {"sku_code": "TSHIRT-GREEN-S", "spec_values": '{"颜色": "森林绿", "尺码": "S"}', "price": 128.00, "stock": 20},
        {"sku_code": "TSHIRT-GREEN-M", "spec_values": '{"颜色": "森林绿", "尺码": "M"}', "price": 128.00, "stock": 30},
        {"sku_code": "TSHIRT-GREEN-L", "spec_values": '{"颜色": "森林绿", "尺码": "L"}', "price": 128.00, "stock": 30},
        {"sku_code": "TSHIRT-GREEN-XL", "spec_values": '{"颜色": "森林绿", "尺码": "XL"}', "price": 128.00, "stock": 20},
        {"sku_code": "TSHIRT-KHAKI-M", "spec_values": '{"颜色": "卡其", "尺码": "M"}', "price": 128.00, "stock": 25},
        {"sku_code": "TSHIRT-KHAKI-L", "spec_values": '{"颜色": "卡其", "尺码": "L"}', "price": 128.00, "stock": 25},
        {"sku_code": "TSHIRT-WHITE-M", "spec_values": '{"颜色": "白色", "尺码": "M"}', "price": 128.00, "stock": 20},
        {"sku_code": "TSHIRT-WHITE-L", "spec_values": '{"颜色": "白色", "尺码": "L"}', "price": 128.00, "stock": 20},
    ],
}


# ---- 库存数据（为营位生成未来30天的库存） ----

def generate_inventory_sql(product_id: int, product_name: str, days: int = 30) -> list:
    """生成营位的每日库存 SQL"""
    records = []
    today = date.today()
    for i in range(days):
        d = today + timedelta(days=i)
        total = 1 if "A0" in product_name or "B0" in product_name or "C0" in product_name or "D0" in product_name or "E0" in product_name else 20
        records.append({
            "product_id": product_id,
            "date": d.isoformat(),
            "total": total,
            "available": total,
            "locked": 0,
            "sold": 0,
            "status": "open",
        })
    return records


# ---- 首页配置 ----

HOME_BANNERS = [
    {"id": 1, "image": "/images/banner-spring.jpg", "title": "🌲 春日露营季 · 限时特惠", "link": "", "color": "#2E7D32"},
    {"id": 2, "image": "/images/banner-music.jpg", "title": "🎶 仲夏夜星空音乐节 · 火热报名", "link": "", "color": "#FF6B35"},
    {"id": 3, "image": "/images/banner-gear.jpg", "title": "⛺ 新品装备上线 · 全场9折", "link": "", "color": "#2196F3"},
]

HOME_NOTICE = "欢迎来到一月一露营地！周末营位火热预定中，新用户首单立减20元 🎉"


# ---- 定价规则 ----

PRICING_RULES = {
    # 按商品名匹配，只给营位加定价规则
    "A区阳光营位 · 有电有木平台": [
        {"rule_type": "date_type", "date_type": "weekday", "price": 138.00},
        {"rule_type": "date_type", "date_type": "weekend", "price": 198.00},
        {"rule_type": "date_type", "date_type": "holiday", "price": 258.00},
    ],
    "A区草坪营位 · 有电无平台": [
        {"rule_type": "date_type", "date_type": "weekday", "price": 108.00},
        {"rule_type": "date_type", "date_type": "weekend", "price": 158.00},
        {"rule_type": "date_type", "date_type": "holiday", "price": 198.00},
    ],
    "B区林间营位 · 自然风": [
        {"rule_type": "date_type", "date_type": "weekday", "price": 78.00},
        {"rule_type": "date_type", "date_type": "weekend", "price": 128.00},
        {"rule_type": "date_type", "date_type": "holiday", "price": 168.00},
    ],
    "C区湖景营位 · 有电有木平台": [
        {"rule_type": "date_type", "date_type": "weekday", "price": 198.00},
        {"rule_type": "date_type", "date_type": "weekend", "price": 288.00},
        {"rule_type": "date_type", "date_type": "holiday", "price": 358.00},
    ],
    "D区亲子营位 · 有电有木平台": [
        {"rule_type": "date_type", "date_type": "weekday", "price": 168.00},
        {"rule_type": "date_type", "date_type": "weekend", "price": 238.00},
        {"rule_type": "date_type", "date_type": "holiday", "price": 298.00},
    ],
    "E区山顶营位 · 观星位": [
        {"rule_type": "date_type", "date_type": "weekday", "price": 228.00},
        {"rule_type": "date_type", "date_type": "weekend", "price": 318.00},
        {"rule_type": "date_type", "date_type": "holiday", "price": 398.00},
    ],
}


async def seed():
    async with async_session_factory() as session:
        try:
            # 检查是否已有商品数据
            result = await session.execute(text("SELECT COUNT(*) FROM product"))
            count = result.scalar_one()
            if count > 0:
                print(f"ℹ️  数据库中已有 {count} 件商品，跳过种子数据")
                print("   如需重新初始化，请先清空 product 表")
                await engine.dispose()
                return

            print("🌱 开始创建商品种子数据...\n")

            product_id_map = {}  # name -> id

            for p in PRODUCTS:
                ext_camping = p.pop("ext_camping", None)
                ext_rental = p.pop("ext_rental", None)
                ext_activity = p.pop("ext_activity", None)
                ext_shop = p.pop("ext_shop", None)

                # 插入商品主体
                cols = ", ".join(p.keys())
                placeholders = ", ".join(f":{k}" for k in p.keys())
                result = await session.execute(
                    text(f"INSERT INTO product ({cols}, site_id) VALUES ({placeholders}, 1) RETURNING id"),
                    p,
                )
                product_id = result.scalar_one()
                product_id_map[p["name"]] = product_id
                print(f"  ✅ 商品: {p['name']} (id={product_id})")

                # 插入扩展表
                if ext_camping:
                    # 处理 date 类型字段
                    event_start = ext_camping.pop("event_start_date", None)
                    event_end = ext_camping.pop("event_end_date", None)
                    ext_camping["product_id"] = product_id
                    if event_start:
                        ext_camping["event_start_date"] = event_start
                    if event_end:
                        ext_camping["event_end_date"] = event_end
                    cols = ", ".join(ext_camping.keys())
                    placeholders = ", ".join(f":{k}" for k in ext_camping.keys())
                    await session.execute(
                        text(f"INSERT INTO product_ext_camping ({cols}) VALUES ({placeholders})"),
                        ext_camping,
                    )

                if ext_rental:
                    ext_rental["product_id"] = product_id
                    cols = ", ".join(ext_rental.keys())
                    placeholders = ", ".join(f":{k}" for k in ext_rental.keys())
                    await session.execute(
                        text(f"INSERT INTO product_ext_rental ({cols}) VALUES ({placeholders})"),
                        ext_rental,
                    )

                if ext_activity:
                    # 处理 date 类型字段
                    event_date = ext_activity.pop("event_date", None)
                    ext_activity["product_id"] = product_id
                    if event_date:
                        ext_activity["event_date"] = event_date
                    cols = ", ".join(ext_activity.keys())
                    placeholders = ", ".join(f":{k}" for k in ext_activity.keys())
                    await session.execute(
                        text(f"INSERT INTO product_ext_activity ({cols}) VALUES ({placeholders})"),
                        ext_activity,
                    )

                if ext_shop:
                    spec_defs = ext_shop.pop("spec_definitions", None)
                    ext_shop["product_id"] = product_id
                    if spec_defs:
                        ext_shop["spec_definitions"] = spec_defs
                    cols = ", ".join(ext_shop.keys())
                    placeholders = ", ".join(f":{k}" for k in ext_shop.keys())
                    await session.execute(
                        text(f"INSERT INTO product_ext_shop ({cols}) VALUES ({placeholders})"),
                        ext_shop,
                    )

            # 插入 SKU
            print(f"\n📦 创建 SKU...")
            sku_count = 0
            for product_name, skus in SKUS.items():
                product_id = product_id_map.get(product_name)
                if not product_id:
                    continue
                for sku in skus:
                    sku["product_id"] = product_id
                    cols = ", ".join(sku.keys())
                    placeholders = ", ".join(f":{k}" for k in sku.keys())
                    await session.execute(
                        text(f"INSERT INTO sku ({cols}) VALUES ({placeholders})"),
                        sku,
                    )
                    sku_count += 1
            print(f"  ✅ 共 {sku_count} 个 SKU")

            # 插入定价规则
            print(f"\n💰 创建定价规则...")
            pricing_count = 0
            for product_name, rules in PRICING_RULES.items():
                product_id = product_id_map.get(product_name)
                if not product_id:
                    continue
                for rule in rules:
                    rule["product_id"] = product_id
                    cols = ", ".join(rule.keys())
                    placeholders = ", ".join(f":{k}" for k in rule.keys())
                    await session.execute(
                        text(f"INSERT INTO pricing_rule ({cols}) VALUES ({placeholders})"),
                        rule,
                    )
                    pricing_count += 1
            print(f"  ✅ 共 {pricing_count} 条定价规则")

            # 生成营位库存（未来30天）
            print(f"\n📊 生成营位库存（未来30天）...")
            inv_count = 0
            for product_name, product_id in product_id_map.items():
                product_data = next((p for p in PRODUCTS if p.get("name") == product_name), None)
                if not product_data:
                    # 数据已经被 pop 修改过，用 product_id_map 的名字查
                    pass
                # 只给营位 + 活动生成库存
                ptype = None
                for p in PRODUCTS:
                    if p.get("name") == product_name:
                        ptype = p.get("type")
                        break
                # PRODUCTS 里的数据已经被 pop 了 type 等，需要从原始判断
                # 用 product_name 来判断
                is_camping = "营位" in product_name
                is_activity = "体验" in product_name or "射箭" in product_name or "工坊" in product_name
                is_shop_item = "柴火" in product_name or "饮料" in product_name or "泡面" in product_name or "T恤" in product_name

                if is_camping:
                    # 营位按位，每天1个
                    is_by_position = "A0" in product_name or "B0" in product_name or "C0" in product_name or "D0" in product_name or "E0" in product_name
                    total = 1 if is_by_position else 20
                    today = date.today()
                    for i in range(30):
                        d = today + timedelta(days=i)
                        await session.execute(
                            text("""
                                INSERT INTO inventory (product_id, date, total, available, locked, sold, status, site_id)
                                VALUES (:pid, :d, :total, :avail, 0, 0, 'open', 1)
                            """),
                            {"pid": product_id, "d": d, "total": total, "avail": total},
                        )
                        inv_count += 1

            print(f"  ✅ 共 {inv_count} 条库存记录")

            # 插入首页配置 (PageConfig)
            print(f"\n🏠 创建首页配置...")
            import json

            # Banner 配置
            await session.execute(
                text("""
                    INSERT INTO page_config (page_key, config_data, status, site_id)
                    VALUES ('home_banner', :data, 'active', 1)
                """),
                {"data": json.dumps({"banners": HOME_BANNERS}, ensure_ascii=False)},
            )
            print(f"  ✅ 首页 Banner 配置（{len(HOME_BANNERS)} 条）")

            # 公告配置
            await session.execute(
                text("""
                    INSERT INTO page_config (page_key, config_data, status, site_id)
                    VALUES ('home_notice', :data, 'active', 1)
                """),
                {"data": json.dumps({"text": HOME_NOTICE}, ensure_ascii=False)},
            )
            print(f"  ✅ 首页公告配置")

            # 优惠规则（连住折扣）
            print(f"\n🎫 创建优惠规则...")
            await session.execute(
                text("""
                    INSERT INTO discount_rule (rule_type, threshold, discount_rate, status, site_id)
                    VALUES ('consecutive_days', 3, 0.90, 'active', 1)
                """),
            )
            await session.execute(
                text("""
                    INSERT INTO discount_rule (rule_type, threshold, discount_rate, status, site_id)
                    VALUES ('consecutive_days', 5, 0.85, 'active', 1)
                """),
            )
            await session.execute(
                text("""
                    INSERT INTO discount_rule (rule_type, threshold, discount_rate, status, site_id)
                    VALUES ('multi_person', 3, 0.95, 'active', 1)
                """),
            )
            print(f"  ✅ 3条全局优惠规则（连住3天9折、5天85折、3人同行95折）")

            await session.commit()

            # 统计
            result = await session.execute(text("SELECT COUNT(*) FROM product"))
            total_products = result.scalar_one()
            result = await session.execute(text("SELECT COUNT(*) FROM sku"))
            total_skus = result.scalar_one()
            result = await session.execute(text("SELECT COUNT(*) FROM inventory"))
            total_inv = result.scalar_one()
            result = await session.execute(text("SELECT COUNT(*) FROM pricing_rule"))
            total_pricing = result.scalar_one()
            result = await session.execute(text("SELECT COUNT(*) FROM page_config"))
            total_pages = result.scalar_one()

            print("\n" + "=" * 50)
            print("🎉 商品种子数据创建完成!")
            print(f"   商品: {total_products} 件")
            print(f"     - 日常营位: 6 (A/B/C/D/E 区)")
            print(f"     - 活动营位: 2 (春日/音乐节)")
            print(f"     - 装备租赁: 3 (帐篷/天幕/桌椅)")
            print(f"     - 日常活动: 2 (皮划艇/射箭)")
            print(f"     - 特定活动: 1 (亲子手作)")
            print(f"     - 营地小店: 3 (柴火/饮料/泡面)")
            print(f"     - 周边商品: 1 (品牌T恤)")
            print(f"   SKU:    {total_skus} 个")
            print(f"   库存:   {total_inv} 条（未来30天）")
            print(f"   定价规则: {total_pricing} 条")
            print(f"   页面配置: {total_pages} 条")
            print(f"   优惠规则: 3 条")
            print("=" * 50)

        except Exception as e:
            await session.rollback()
            print(f"❌ 错误: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            raise
        finally:
            await session.close()

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())

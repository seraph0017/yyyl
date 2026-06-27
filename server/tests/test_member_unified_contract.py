import unittest
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch


class _FakeResult:
    def __init__(self, *, scalar_value=None, rows=None):
        self._scalar_value = scalar_value
        self._rows = rows or []

    def scalar(self):
        return self._scalar_value

    def scalar_one_or_none(self):
        return self._scalar_value

    def scalars(self):
        return self

    def all(self):
        return list(self._rows)


class _FakeDb:
    def __init__(self, scalar_values=None):
        self.added = []
        self.flushed = False
        self._scalar_values = list(scalar_values or [])

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        self.flushed = True

    async def execute(self, *args, **kwargs):
        value = self._scalar_values.pop(0) if self._scalar_values else None
        return _FakeResult(scalar_value=value)


class MemberUnifiedContractTest(unittest.IsolatedAsyncioTestCase):
    def test_unified_schema_and_mapping_shape(self):
        from schemas.member import MembershipCardConfigSchema, MembershipCardInfo
        from services import member_service

        annual_config = SimpleNamespace(
            id=11,
            card_name="西郊林场年卡",
            price=Decimal("399.00"),
            duration_days=365,
            privileges={"101": {"free": True}, 102: {"free": True}},
            daily_limit_position=1,
            daily_limit_quantity=2,
            max_consecutive_days=5,
            gap_days=2,
            refund_days=7,
            status="active",
            site_id=1,
            created_at=datetime.now(timezone.utc),
        )
        annual_card = SimpleNamespace(
            id=21,
            user_id=7,
            config_id=11,
            order_id=3001,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            real_name="张三",
            id_card_masked="310***********1234",
            status="active",
            created_at=datetime.now(timezone.utc),
        )
        times_config = SimpleNamespace(
            id=12,
            card_name="次数卡礼包",
            total_times=10,
            validity_days=180,
            applicable_products=[201, 202],
            daily_limit=3,
            status="active",
            site_id=1,
            created_at=datetime.now(timezone.utc),
        )
        times_card = SimpleNamespace(
            id=22,
            user_id=7,
            config_id=12,
            total_times=10,
            remaining_times=6,
            start_date=date(2026, 2, 1),
            end_date=date(2026, 7, 30),
            activated_at=datetime.now(timezone.utc),
            status="active",
            created_at=datetime.now(timezone.utc),
        )

        annual_config_data = member_service.serialize_membership_card_config(annual_config)
        annual_card_data = member_service.serialize_membership_card_info(annual_card, annual_config)
        times_config_data = member_service.serialize_membership_card_config(times_config)
        times_card_data = member_service.serialize_membership_card_info(times_card, times_config)

        annual_config_model = MembershipCardConfigSchema.model_validate(annual_config_data)
        annual_card_model = MembershipCardInfo.model_validate(annual_card_data)
        times_config_model = MembershipCardConfigSchema.model_validate(times_config_data)
        times_card_model = MembershipCardInfo.model_validate(times_card_data)

        self.assertEqual(annual_config_model.card_kind, "annual")
        self.assertEqual(annual_config_model.usage_mode, "unlimited")
        self.assertEqual(annual_config_model.config_name, "西郊林场年卡")
        self.assertEqual(annual_config_model.daily_limit, 2)
        self.assertEqual(annual_config_model.applicable_products, [101, 102])

        self.assertEqual(annual_card_model.card_kind, "annual")
        self.assertEqual(annual_card_model.usage_mode, "unlimited")
        self.assertEqual(annual_card_model.config_name, "西郊林场年卡")
        self.assertEqual(annual_card_model.status, "active")
        self.assertIsNone(annual_card_model.total_times)
        self.assertIsNone(annual_card_model.remaining_times)

        self.assertEqual(times_config_model.card_kind, "times")
        self.assertEqual(times_config_model.usage_mode, "limited_times")
        self.assertEqual(times_config_model.total_times, 10)
        self.assertEqual(times_config_model.remaining_times, 10)
        self.assertEqual(times_config_model.daily_limit, 3)
        self.assertEqual(times_config_model.applicable_products, [201, 202])

        self.assertEqual(times_card_model.card_kind, "times")
        self.assertEqual(times_card_model.usage_mode, "limited_times")
        self.assertEqual(times_card_model.total_times, 10)
        self.assertEqual(times_card_model.remaining_times, 6)
        self.assertEqual(times_card_model.config_name, "次数卡礼包")

    async def test_user_membership_card_route_returns_aggregated_structure(self):
        from routers import members
        from schemas.member import MembershipCardConfigSchema, MembershipCardInfo

        current_cards = [
            MembershipCardInfo.model_validate(
                {
                    "id": 21,
                    "user_id": 7,
                    "config_id": 11,
                    "order_id": 3001,
                    "card_kind": "annual",
                    "usage_mode": "unlimited",
                    "config_name": "西郊林场年卡",
                    "status": "active",
                    "start_date": "2026-01-01",
                    "end_date": "2026-12-31",
                    "remaining_days": 365,
                }
            ),
            MembershipCardInfo.model_validate(
                {
                    "id": 22,
                    "user_id": 7,
                    "config_id": 12,
                    "card_kind": "times",
                    "usage_mode": "limited_times",
                    "config_name": "次数卡礼包",
                    "status": "active",
                    "start_date": "2026-02-01",
                    "end_date": "2026-07-30",
                    "remaining_days": 180,
                    "total_times": 10,
                    "remaining_times": 6,
                }
            ),
        ]
        available_configs = [
            MembershipCardConfigSchema.model_validate(
                {
                    "id": 11,
                    "card_kind": "annual",
                    "usage_mode": "unlimited",
                    "config_name": "西郊林场年卡",
                    "status": "active",
                    "daily_limit": 2,
                    "applicable_products": [101, 102],
                }
            ),
            MembershipCardConfigSchema.model_validate(
                {
                    "id": 12,
                    "card_kind": "times",
                    "usage_mode": "limited_times",
                    "config_name": "次数卡礼包",
                    "status": "active",
                    "total_times": 10,
                    "remaining_times": 10,
                    "daily_limit": 3,
                    "applicable_products": [201, 202],
                }
            ),
        ]

        with (
            patch.object(members.member_service, "get_user_membership_cards", AsyncMock(return_value=current_cards)),
            patch.object(members.member_service, "get_membership_card_configs", AsyncMock(return_value=available_configs)),
        ):
            result = await members.get_membership_card(
                request=SimpleNamespace(headers={"X-Site-Id": "1"}),
                db=SimpleNamespace(),
                user=SimpleNamespace(id=7),
            )

        self.assertEqual(result.data["current_cards"][0].card_kind, "annual")
        self.assertEqual(result.data["current_cards"][1].card_kind, "times")
        self.assertEqual(result.data["available_configs"][0].config_name, "西郊林场年卡")
        self.assertEqual(result.data["available_configs"][1].usage_mode, "limited_times")

    async def test_activate_times_card_uses_site_scope_and_sets_card_site(self):
        from models.member import TimesCard
        from services import member_service

        code_record = SimpleNamespace(
            id=501,
            code="DLG2026CARD00001",
            config_id=12,
            status="unused",
            expires_at=datetime.now(timezone.utc) + timedelta(days=3),
            site_id=2,
            used_by=None,
            used_at=None,
        )
        config = SimpleNamespace(
            id=12,
            site_id=2,
            total_times=10,
            validity_days=180,
        )
        db = _FakeDb([code_record, config])

        card = await member_service.activate_times_card(
            db,
            user_id=7,
            activation_code="DLG2026CARD00001",
            site_id=2,
        )

        self.assertIsInstance(card, TimesCard)
        self.assertEqual(card.site_id, 2)
        self.assertEqual(card.config_id, 12)
        self.assertEqual(card.activation_code_id, 501)
        self.assertEqual(card.total_times, 10)
        self.assertEqual(card.remaining_times, 10)
        self.assertEqual(code_record.status, "used")
        self.assertEqual(code_record.used_by, 7)
        self.assertIsNotNone(code_record.used_at)
        self.assertTrue(db.flushed)

    async def test_times_card_activate_route_passes_site_id_to_service(self):
        from routers import members
        from schemas.member import ActivationCodeActivateRequest

        activated_card = SimpleNamespace(
            id=22,
            user_id=7,
            config_id=12,
            total_times=10,
            remaining_times=10,
            start_date=date(2026, 2, 1),
            end_date=date(2026, 7, 30),
            activated_at=datetime.now(timezone.utc),
            status="active",
            created_at=datetime.now(timezone.utc),
            site_id=2,
        )

        with patch.object(
            members.member_service,
            "activate_times_card",
            AsyncMock(return_value=activated_card),
        ) as activate:
            db = SimpleNamespace()
            result = await members.activate_times_card(
                body=ActivationCodeActivateRequest(code="DLG2026CARD00001"),
                request=SimpleNamespace(headers={"X-Site-Id": "2"}),
                db=db,
                user=SimpleNamespace(id=7),
            )

        activate.assert_awaited_once_with(
            db,
            7,
            "DLG2026CARD00001",
            site_id=2,
        )
        self.assertEqual(result.data.id, 22)

    async def test_annual_card_booking_check_route_passes_site_id_to_service(self):
        from routers import members

        booking_check_result = {
            "can_book": True,
            "reason": None,
            "daily_limit_position": 1,
            "daily_limit_quantity": 2,
            "used_today_position": 0,
            "used_today_quantity": 0,
            "max_consecutive_days": 5,
            "current_consecutive_days": 1,
            "gap_days": 2,
            "next_available_date": None,
        }

        db = SimpleNamespace()
        with patch.object(
            members.member_service,
            "check_annual_card_booking",
            AsyncMock(return_value=booking_check_result),
        ) as check_booking:
            result = await members.check_annual_card_booking(
                annual_card_id=21,
                booking_dates="2026-06-27,2026-06-28",
                request=SimpleNamespace(headers={"X-Site-Id": "2"}),
                db=db,
                user=SimpleNamespace(id=7),
            )

        self.assertTrue(result.success)
        check_booking.assert_awaited_once()
        self.assertEqual(check_booking.await_args.args[:4], (
            db,
            7,
            21,
            [date(2026, 6, 27), date(2026, 6, 28)],
        ))
        self.assertEqual(check_booking.await_args.kwargs["site_id"], 2)

    async def test_membership_card_activate_route_passes_site_id_to_service(self):
        from routers import members
        from schemas.member import ActivationCodeActivateRequest

        activated_card = SimpleNamespace(
            id=22,
            user_id=7,
            config_id=12,
            total_times=10,
            remaining_times=10,
            start_date=date(2026, 2, 1),
            end_date=date(2026, 7, 30),
            activated_at=datetime.now(timezone.utc),
            status="active",
            created_at=datetime.now(timezone.utc),
            site_id=2,
        )
        config = SimpleNamespace(
            id=12,
            card_name="大聋谷次数卡",
            total_times=10,
            validity_days=180,
            applicable_products=[201],
            daily_limit=3,
            status="active",
            site_id=2,
            created_at=datetime.now(timezone.utc),
        )
        db = _FakeDb([config])

        with patch.object(
            members.member_service,
            "activate_times_card",
            AsyncMock(return_value=activated_card),
        ) as activate:
            result = await members.activate_membership_card(
                body=ActivationCodeActivateRequest(code="DLG2026CARD00001"),
                request=SimpleNamespace(headers={"X-Site-Id": "2"}),
                db=db,
                user=SimpleNamespace(id=7),
            )

        activate.assert_awaited_once_with(
            db,
            7,
            "DLG2026CARD00001",
            site_id=2,
        )
        self.assertEqual(result.data.config_name, "大聋谷次数卡")

    async def test_admin_member_list_and_detail_expose_unified_fields(self):
        from routers import admin as admin_router

        request = SimpleNamespace(headers={"X-Site-Id": "1"})
        admin = SimpleNamespace(id=1, site_id=1, role=SimpleNamespace(role_code="super_admin"))

        users = [
            SimpleNamespace(
                id=7,
                nickname="会员A",
                avatar_url=None,
                phone="13800000000",
                member_level="annual_card",
                points_balance=120,
                status="active",
                last_login_at=datetime.now(timezone.utc),
                created_at=datetime.now(timezone.utc),
            )
        ]
        annual_cards = [
            SimpleNamespace(
                id=21,
                user_id=7,
                config_id=11,
                order_id=3001,
                start_date=date(2026, 1, 1),
                end_date=date(2026, 12, 31),
                real_name="张三",
                id_card_masked="310***********1234",
                status="active",
                created_at=datetime.now(timezone.utc),
            )
        ]
        times_cards = [
            SimpleNamespace(
                id=22,
                user_id=7,
                config_id=12,
                total_times=10,
                remaining_times=6,
                start_date=date(2026, 2, 1),
                end_date=date(2026, 7, 30),
                activated_at=datetime.now(timezone.utc),
                status="active",
                created_at=datetime.now(timezone.utc),
            )
        ]

        list_results = iter(
            [
                _FakeResult(scalar_value=1),
                _FakeResult(rows=users),
                _FakeResult(rows=annual_cards),
                _FakeResult(rows=times_cards),
            ]
        )

        async def execute_side_effect(*args, **kwargs):
            return next(list_results)

        db = SimpleNamespace(execute=AsyncMock(side_effect=execute_side_effect))
        list_result = await admin_router.list_members(request=request, pagination=SimpleNamespace(offset=0, page=1, page_size=20), db=db, admin=admin)

        self.assertTrue(list_result.data.list[0]["has_membership_card"])
        self.assertEqual(list_result.data.list[0]["membership_card_count"], 2)
        self.assertEqual(list_result.data.list[0]["membership_cards"][0]["card_kind"], "annual")
        self.assertEqual(list_result.data.list[0]["membership_cards"][1]["card_kind"], "times")
        self.assertIn("annual_card", list_result.data.list[0])
        self.assertIn("times_cards", list_result.data.list[0])

        detail_results = iter(
            [
                _FakeResult(scalar_value=users[0]),
                _FakeResult(scalar_value=annual_cards[0]),
                _FakeResult(rows=times_cards),
            ]
        )

        async def detail_execute_side_effect(*args, **kwargs):
            return next(detail_results)

        detail_db = SimpleNamespace(execute=AsyncMock(side_effect=detail_execute_side_effect))
        detail_result = await admin_router.get_member_detail(user_id=7, db=detail_db, admin=admin)

        self.assertTrue(detail_result.data["has_membership_card"])
        self.assertEqual(detail_result.data["membership_card_count"], 2)
        self.assertEqual(detail_result.data["membership_cards"][0]["card_kind"], "annual")
        self.assertEqual(detail_result.data["membership_cards"][1]["card_kind"], "times")
        self.assertIn("annual_card", detail_result.data)
        self.assertIn("times_cards", detail_result.data)


if __name__ == "__main__":
    unittest.main()

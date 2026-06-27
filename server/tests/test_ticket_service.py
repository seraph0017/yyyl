import unittest
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException


class FakeScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar_one(self):
        return self.value

    def scalar_one_or_none(self):
        return self.value

    def all(self):
        return self.value


class FakeDb:
    def __init__(self, *execute_values):
        self.execute_values = list(execute_values)
        self.added = []
        self.flush_count = 0
        self.queries = []

    async def execute(self, query):
        self.queries.append(query)
        if not self.execute_values:
            raise AssertionError(f"unexpected query: {query}")
        return FakeScalarResult(self.execute_values.pop(0))

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        self.flush_count += 1


class FakeRedis:
    def __init__(self, values=None):
        self.values = values or {}

    async def set(self, key, value, ex=None):
        self.values[key] = {"value": value, "ex": ex}

    async def get(self, key):
        value = self.values.get(key)
        if isinstance(value, dict):
            return value.get("value")
        return value

    async def incr(self, key):
        value = int(self.values.get(key, 0)) + 1
        self.values[key] = value
        return value

    async def expire(self, key, seconds):
        return True

    async def delete(self, *keys):
        for key in keys:
            self.values.pop(key, None)


class FakeAuditSession:
    def __init__(self):
        self.added = []
        self.commit_count = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        self.commit_count += 1


def make_audit_factory(session: FakeAuditSession):
    def factory():
        return session
    return factory


def compile_query(query) -> str:
    return str(query.compile(compile_kwargs={"literal_binds": True}))


def query_where_clause(query) -> str:
    sql = compile_query(query)
    return sql.split(" WHERE ", 1)[1] if " WHERE " in sql else ""


class TicketServiceTest(unittest.IsolatedAsyncioTestCase):
    async def test_refresh_qr_token_updates_only_hash(self):
        from services import ticket_service

        ticket = SimpleNamespace(
            id=12,
            site_id=2,
            user_id=101,
            verify_status="pending",
            qr_token_hash="old-hash",
        )
        db = FakeDb(ticket)

        with patch.object(ticket_service, "generate_qr_token", return_value="fresh-token"):
            result = await ticket_service.refresh_qr_token(
                db,
                ticket_id=12,
                user_id=101,
                site_id=2,
            )

        self.assertEqual(result["qr_token"], "fresh-token")
        self.assertEqual(result["qrcode_token"], "fresh-token")
        self.assertNotEqual(ticket.qr_token_hash, "fresh-token")
        self.assertEqual(ticket.qr_token_hash, ticket_service._hash_qr_token("fresh-token"))
        self.assertFalse(hasattr(ticket, "qr_token"))
        self.assertEqual(db.flush_count, 1)

    async def test_refresh_qr_token_rejects_non_pending_ticket_status(self):
        from services import ticket_service

        for verify_status in ["verified", "expired", "refunded"]:
            with self.subTest(verify_status=verify_status):
                ticket = SimpleNamespace(
                    id=12,
                    site_id=2,
                    user_id=101,
                    verify_status=verify_status,
                    qr_token_hash="old-hash",
                )
                db = FakeDb(ticket)

                with self.assertRaises(HTTPException) as ctx:
                    await ticket_service.refresh_qr_token(
                        db,
                        ticket_id=12,
                        user_id=101,
                        site_id=2,
                    )

                self.assertEqual(ctx.exception.status_code, 400)
                self.assertEqual(ticket.qr_token_hash, "old-hash")
                self.assertEqual(db.flush_count, 0)

    async def test_build_ticket_response_does_not_issue_qr_for_non_pending_ticket(self):
        from services import ticket_service

        ticket = SimpleNamespace(
            id=12,
            order_id=34,
            order_item_id=56,
            user_id=101,
            ticket_no="T20260627001",
            ticket_type="camping",
            verify_status="refunded",
            verify_date=date.today(),
            verified_at=None,
            verified_by=None,
            current_verify_count=0,
            total_verify_count=1,
            created_at=datetime.now(timezone.utc),
            qr_token_hash="old-hash",
            qr_token_expires_at=None,
        )
        db = FakeDb()

        with patch.object(ticket_service, "generate_qr_token", return_value="fresh-token") as generate:
            result = await ticket_service.build_ticket_response(db, ticket)

        generate.assert_not_called()
        self.assertEqual(result["qr_token"], "")
        self.assertEqual(ticket.qr_token_hash, "old-hash")
        self.assertEqual(db.flush_count, 0)

    async def test_invalid_qr_log_uses_staff_site_id(self):
        from services import ticket_service

        db = FakeDb(None)
        audit_session = FakeAuditSession()

        with patch.object(ticket_service, "async_session_factory", make_audit_factory(audit_session)):
            with self.assertRaises(HTTPException):
                await ticket_service.scan_ticket(
                    db,
                    "bad-qr-token",
                    staff_id=88,
                    device_info="scanner-02",
                    staff_site_id=2,
                )

        logs = [obj for obj in audit_session.added if obj.__class__.__name__ == "TicketVerifyLog"]
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0].site_id, 2)
        self.assertEqual(logs[0].failure_reason, "二维码无效")
        self.assertEqual(audit_session.commit_count, 1)

    async def test_scan_ticket_records_success_log(self):
        from services import ticket_service

        qr_token = "qr-token-success"
        ticket = SimpleNamespace(
            id=12,
            site_id=2,
            ticket_no="T20260626001",
            ticket_type="camping",
            order_id=34,
            order_item_id=56,
            qr_token_expires_at=datetime.now(timezone.utc) + timedelta(seconds=30),
            verify_status="pending",
            verify_date=date.today(),
            verified_at=None,
            verified_by=None,
            current_verify_count=0,
            is_deleted=False,
        )
        order = SimpleNamespace(
            id=34,
            payment_method="wechat",
            payment_status="paid",
            status="paid",
            is_deleted=False,
        )
        order_item = SimpleNamespace(id=56, product_id=78)
        product = SimpleNamespace(id=78, name="林间营位")
        db = FakeDb(ticket, order, order_item, product)
        redis = FakeRedis()

        with patch.object(ticket_service, "get_redis", return_value=redis):
            result = await ticket_service.scan_ticket(
                db,
                qr_token,
                staff_id=99,
                device_info="wx-devtools",
                staff_source="user",
            )

        logs = [obj for obj in db.added if obj.__class__.__name__ == "TicketVerifyLog"]
        self.assertEqual(result["ticket_id"], 12)
        self.assertEqual(result["product_name"], "林间营位")
        self.assertEqual(ticket.verify_status, "verified")
        self.assertEqual(ticket.verified_by, 99)
        self.assertEqual(ticket.current_verify_count, 1)
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0].site_id, 2)
        self.assertEqual(logs[0].ticket_id, 12)
        self.assertEqual(logs[0].order_id, 34)
        self.assertEqual(logs[0].order_item_id, 56)
        self.assertEqual(logs[0].staff_id, 99)
        self.assertEqual(logs[0].staff_source, "user")
        self.assertEqual(logs[0].verify_result, "success")
        self.assertEqual(logs[0].device_info, "wx-devtools")
        self.assertNotEqual(logs[0].qr_token_hash, qr_token)
        self.assertEqual(len(logs[0].qr_token_hash), 64)
        owner = redis.values.get("verify_session_owner:" + result["session_id"])
        self.assertEqual(owner["value"], "12:99:2:user")
        self.assertGreaterEqual(db.flush_count, 2)

    async def test_scan_ticket_rejects_unworkable_order_status(self):
        from services import ticket_service

        cases = [
            ("paid", "cancelled", "none"),
            ("paid", "refunded", "none"),
            ("paid", "refund_pending", "none"),
            ("paid", "partial_refunded", "none"),
            ("paid", "paid", "pending"),
            ("paid", "paid", "partial"),
            ("paid", "paid", "refunded"),
            ("unpaid", "paid", "none"),
            ("refunded", "paid", "none"),
        ]
        for payment_status, order_status, refund_status in cases:
            with self.subTest(
                payment_status=payment_status,
                order_status=order_status,
                refund_status=refund_status,
            ):
                qr_token = f"qr-token-{payment_status}-{order_status}-{refund_status}"
                ticket = SimpleNamespace(
                    id=12,
                    site_id=2,
                    ticket_no="T20260626001",
                    ticket_type="camping",
                    order_id=34,
                    order_item_id=56,
                    qr_token_expires_at=datetime.now(timezone.utc) + timedelta(seconds=30),
                    verify_status="pending",
                    verify_date=date.today(),
                    verified_at=None,
                    verified_by=None,
                    current_verify_count=0,
                    is_deleted=False,
                )
                order = SimpleNamespace(
                    id=34,
                    site_id=2,
                    payment_method="wechat_pay",
                    payment_status=payment_status,
                    status=order_status,
                    refund_status=refund_status,
                    is_deleted=False,
                )
                db = FakeDb(ticket, order)
                audit_session = FakeAuditSession()

                with patch.object(ticket_service, "async_session_factory", make_audit_factory(audit_session)):
                    with self.assertRaises(HTTPException) as ctx:
                        await ticket_service.scan_ticket(
                            db,
                            qr_token,
                            staff_id=99,
                            device_info="wx-devtools",
                            staff_site_id=2,
                        )

                self.assertEqual(ctx.exception.status_code, 400)
                self.assertEqual(ticket.verify_status, "pending")
                logs = [obj for obj in audit_session.added if obj.__class__.__name__ == "TicketVerifyLog"]
                self.assertEqual(len(logs), 1)
                self.assertEqual(logs[0].failure_reason, "订单不可核销")
                self.assertEqual(audit_session.commit_count, 1)

    async def test_scan_ticket_rejects_non_pending_ticket_status(self):
        from services import ticket_service

        for verify_status in ["expired", "refunded"]:
            with self.subTest(verify_status=verify_status):
                ticket = SimpleNamespace(
                    id=12,
                    site_id=2,
                    ticket_no="T20260626001",
                    ticket_type="camping",
                    order_id=34,
                    order_item_id=56,
                    qr_token_expires_at=datetime.now(timezone.utc) + timedelta(seconds=30),
                    verify_status=verify_status,
                    verify_date=date.today(),
                    verified_at=None,
                    verified_by=None,
                    current_verify_count=0,
                    is_deleted=False,
                )
                db = FakeDb(ticket)
                audit_session = FakeAuditSession()

                with patch.object(ticket_service, "async_session_factory", make_audit_factory(audit_session)):
                    with self.assertRaises(HTTPException) as ctx:
                        await ticket_service.scan_ticket(
                            db,
                            f"qr-token-{verify_status}",
                            staff_id=99,
                            device_info="wx-devtools",
                            staff_site_id=2,
                        )

                self.assertEqual(ctx.exception.status_code, 400)
                logs = [obj for obj in audit_session.added if obj.__class__.__name__ == "TicketVerifyLog"]
                self.assertEqual(len(logs), 1)
                self.assertEqual(logs[0].failure_reason, "电子票不可核销")

    async def test_scan_ticket_records_invalid_qr_log_without_plain_token(self):
        from services import ticket_service

        db = FakeDb(None)
        audit_session = FakeAuditSession()

        with patch.object(ticket_service, "async_session_factory", make_audit_factory(audit_session)):
            with self.assertRaises(HTTPException) as ctx:
                await ticket_service.scan_ticket(
                    db,
                    "bad-qr-token",
                    staff_id=88,
                    device_info="scanner-01",
                )

        self.assertEqual(ctx.exception.status_code, 400)
        logs = [obj for obj in audit_session.added if obj.__class__.__name__ == "TicketVerifyLog"]
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0].site_id, 1)
        self.assertIsNone(logs[0].ticket_id)
        self.assertIsNone(logs[0].order_id)
        self.assertEqual(logs[0].staff_id, 88)
        self.assertEqual(logs[0].verify_result, "failed")
        self.assertEqual(logs[0].failure_reason, "二维码无效")
        self.assertEqual(logs[0].device_info, "scanner-01")
        self.assertNotEqual(logs[0].qr_token_hash, "bad-qr-token")
        self.assertEqual(len(logs[0].qr_token_hash), 64)
        self.assertEqual(audit_session.commit_count, 1)
        self.assertEqual(db.flush_count, 0)

    async def test_scan_ticket_rejects_cross_site_staff_and_records_log(self):
        from services import ticket_service

        db = FakeDb(None)
        audit_session = FakeAuditSession()

        with patch.object(ticket_service, "async_session_factory", make_audit_factory(audit_session)):
            with self.assertRaises(HTTPException) as ctx:
                await ticket_service.scan_ticket(
                    db,
                    "cross-site-token",
                    staff_id=100,
                    staff_site_id=1,
                )

        self.assertEqual(ctx.exception.status_code, 400)
        logs = [obj for obj in audit_session.added if obj.__class__.__name__ == "TicketVerifyLog"]
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0].site_id, 1)
        self.assertIsNone(logs[0].ticket_id)
        self.assertEqual(logs[0].verify_result, "failed")
        self.assertEqual(logs[0].failure_reason, "二维码无效")

    async def test_verify_code_records_success_log_for_membership_ticket(self):
        from services import ticket_service

        ticket = SimpleNamespace(
            id=13,
            site_id=2,
            user_id=101,
            order_id=35,
            order_item_id=57,
            verify_status="pending",
            verified_at=None,
            verified_by=None,
            current_verify_count=0,
        )
        order = SimpleNamespace(id=35, site_id=2, payment_status="paid", status="paid", is_deleted=False)
        db = FakeDb(ticket, order)
        redis = FakeRedis({"verify_session:session-1": "13:654321:77"})

        with patch.object(ticket_service, "get_redis", return_value=redis):
            result = await ticket_service.verify_code(
                db,
                "session-1",
                "654321",
                user_id=101,
            )

        logs = [obj for obj in db.added if obj.__class__.__name__ == "TicketVerifyLog"]
        self.assertEqual(result["status"], "verified")
        self.assertEqual(ticket.verify_status, "verified")
        self.assertEqual(ticket.verified_by, 77)
        self.assertEqual(ticket.current_verify_count, 1)
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0].site_id, 2)
        self.assertEqual(logs[0].ticket_id, 13)
        self.assertEqual(logs[0].order_id, 35)
        self.assertEqual(logs[0].order_item_id, 57)
        self.assertEqual(logs[0].staff_id, 77)
        self.assertEqual(logs[0].verify_result, "success")

    async def test_verify_code_rechecks_order_status_before_membership_ticket_success(self):
        from services import ticket_service

        cases = [
            ("paid", "paid", "pending"),
            ("unpaid", "paid", "none"),
            ("refunded", "paid", "none"),
        ]
        for payment_status, order_status, refund_status in cases:
            with self.subTest(
                payment_status=payment_status,
                order_status=order_status,
                refund_status=refund_status,
            ):
                ticket = SimpleNamespace(
                    id=13,
                    site_id=2,
                    user_id=101,
                    order_id=35,
                    order_item_id=57,
                    verify_status="pending",
                    verified_at=None,
                    verified_by=None,
                    current_verify_count=0,
                )
                order = SimpleNamespace(
                    id=35,
                    site_id=2,
                    payment_status=payment_status,
                    status=order_status,
                    refund_status=refund_status,
                    is_deleted=False,
                )
                db = FakeDb(ticket, order)
                redis = FakeRedis({"verify_session:session-order-state": "13:654321:77:2:user"})
                audit_session = FakeAuditSession()

                with (
                    patch.object(ticket_service, "get_redis", return_value=redis),
                    patch.object(ticket_service, "async_session_factory", make_audit_factory(audit_session)),
                ):
                    with self.assertRaises(HTTPException) as ctx:
                        await ticket_service.verify_code(
                            db,
                            "session-order-state",
                            "654321",
                            user_id=101,
                            site_id=2,
                        )

                self.assertEqual(ctx.exception.status_code, 400)
                self.assertEqual(ticket.verify_status, "pending")
                logs = [obj for obj in audit_session.added if obj.__class__.__name__ == "TicketVerifyLog"]
                self.assertEqual(len(logs), 1)
                self.assertEqual(logs[0].failure_reason, "订单不可核销")

    async def test_verify_code_rejects_non_pending_ticket_status(self):
        from services import ticket_service

        for verify_status in ["verified", "expired", "refunded"]:
            with self.subTest(verify_status=verify_status):
                ticket = SimpleNamespace(
                    id=13,
                    site_id=2,
                    user_id=101,
                    order_id=35,
                    order_item_id=57,
                    verify_status=verify_status,
                    verified_at=None,
                    verified_by=None,
                    current_verify_count=0,
                )
                db = FakeDb(ticket)
                redis = FakeRedis({"verify_session:session-non-pending": "13:654321:77:2:user"})
                audit_session = FakeAuditSession()

                with (
                    patch.object(ticket_service, "get_redis", return_value=redis),
                    patch.object(ticket_service, "async_session_factory", make_audit_factory(audit_session)),
                ):
                    with self.assertRaises(HTTPException) as ctx:
                        await ticket_service.verify_code(
                            db,
                            "session-non-pending",
                            "654321",
                            user_id=101,
                            site_id=2,
                        )

                self.assertEqual(ctx.exception.status_code, 400)
                logs = [obj for obj in audit_session.added if obj.__class__.__name__ == "TicketVerifyLog"]
                self.assertEqual(len(logs), 1)
                self.assertIn(logs[0].verify_result, {"failed", "duplicate"})

    async def test_verify_code_rejects_cross_site_session(self):
        from services import ticket_service

        ticket = SimpleNamespace(
            id=13,
            site_id=2,
            user_id=101,
            order_id=35,
            order_item_id=57,
            verify_status="pending",
            verified_at=None,
            verified_by=None,
            current_verify_count=0,
        )
        db = FakeDb(ticket)
        redis = FakeRedis({"verify_session:session-cross-site": "13:654321:77:2"})
        audit_session = FakeAuditSession()

        with (
            patch.object(ticket_service, "get_redis", return_value=redis),
            patch.object(ticket_service, "async_session_factory", make_audit_factory(audit_session)),
        ):
            with self.assertRaises(HTTPException) as ctx:
                await ticket_service.verify_code(
                    db,
                    "session-cross-site",
                    "654321",
                    user_id=101,
                    site_id=1,
                )

        self.assertEqual(ctx.exception.status_code, 403)
        self.assertEqual(ticket.verify_status, "pending")
        logs = [obj for obj in audit_session.added if obj.__class__.__name__ == "TicketVerifyLog"]
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0].site_id, 2)
        self.assertEqual(logs[0].verify_result, "failed")
        self.assertEqual(logs[0].failure_reason, "票券不属于当前营地")
        self.assertNotIn("ticket.site_id", query_where_clause(db.queries[0]))

    async def test_verify_code_rejects_other_user_and_logs_failure(self):
        from services import ticket_service

        ticket = SimpleNamespace(
            id=13,
            site_id=2,
            user_id=202,
            order_id=35,
            order_item_id=57,
            verify_status="pending",
            verified_at=None,
            verified_by=None,
            current_verify_count=0,
        )
        db = FakeDb(ticket)
        redis = FakeRedis({"verify_session:session-2": "13:654321:77"})
        audit_session = FakeAuditSession()

        with (
            patch.object(ticket_service, "get_redis", return_value=redis),
            patch.object(ticket_service, "async_session_factory", make_audit_factory(audit_session)),
        ):
            with self.assertRaises(HTTPException) as ctx:
                await ticket_service.verify_code(
                    db,
                    "session-2",
                    "654321",
                    user_id=101,
                )

        self.assertEqual(ctx.exception.status_code, 403)
        logs = [obj for obj in audit_session.added if obj.__class__.__name__ == "TicketVerifyLog"]
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0].site_id, 2)
        self.assertIsNone(logs[0].ticket_id)
        self.assertIsNone(logs[0].order_id)
        self.assertEqual(logs[0].verify_result, "failed")
        self.assertEqual(logs[0].failure_reason, "票券不属于当前用户")
        self.assertEqual(ticket.verify_status, "pending")

    async def test_verify_code_wrong_code_records_failure_log(self):
        from services import ticket_service

        ticket = SimpleNamespace(
            id=13,
            site_id=2,
            user_id=101,
            order_id=35,
            order_item_id=57,
            verify_status="pending",
        )
        db = FakeDb(ticket)
        redis = FakeRedis({"verify_session:session-3": "13:654321:77"})
        audit_session = FakeAuditSession()

        with (
            patch.object(ticket_service, "get_redis", return_value=redis),
            patch.object(ticket_service, "async_session_factory", make_audit_factory(audit_session)),
        ):
            with self.assertRaises(HTTPException):
                await ticket_service.verify_code(
                    db,
                    "session-3",
                    "000000",
                    user_id=101,
                )

        logs = [obj for obj in audit_session.added if obj.__class__.__name__ == "TicketVerifyLog"]
        self.assertEqual(len(logs), 1)
        self.assertIsNone(logs[0].ticket_id)
        self.assertIsNone(logs[0].order_id)
        self.assertEqual(logs[0].verify_result, "failed")
        self.assertEqual(logs[0].failure_reason, "验证码错误")

    async def test_verify_status_requires_session_staff_and_site(self):
        from services import ticket_service

        redis = FakeRedis({
            "verify_session:session-4": "13:654321:77:2:user",
            "verify_status:session-4": "code_sent",
        })

        with patch.object(ticket_service, "get_redis", return_value=redis):
            with self.assertRaises(HTTPException) as ctx:
                await ticket_service.get_verify_status(
                    "session-4",
                    staff_id=88,
                    staff_site_id=2,
                )

        self.assertEqual(ctx.exception.status_code, 403)

        with patch.object(ticket_service, "get_redis", return_value=redis):
            with self.assertRaises(HTTPException) as ctx:
                await ticket_service.get_verify_status(
                    "session-4",
                    staff_id=77,
                    staff_site_id=1,
                )

        self.assertEqual(ctx.exception.status_code, 403)

        with patch.object(ticket_service, "get_redis", return_value=redis):
            result = await ticket_service.get_verify_status(
                "session-4",
                staff_id=77,
                staff_site_id=2,
                staff_source="user",
            )

        self.assertEqual(result["status"], "code_sent")
        self.assertEqual(result["verification_code"], "654321")

    async def test_verify_status_rejects_same_id_different_staff_source(self):
        from services import ticket_service

        redis = FakeRedis({
            "verify_session:session-source": "13:654321:77:2:user",
            "verify_status:session-source": "code_sent",
        })

        with patch.object(ticket_service, "get_redis", return_value=redis):
            with self.assertRaises(HTTPException) as ctx:
                await ticket_service.get_verify_status(
                    "session-source",
                    staff_id=77,
                    staff_site_id=2,
                    staff_source="admin",
                )

        self.assertEqual(ctx.exception.status_code, 403)
        self.assertEqual(ctx.exception.detail["code"], 40303)

    async def test_verify_status_owner_rejects_same_id_different_staff_source(self):
        from services import ticket_service

        redis = FakeRedis({
            "verify_status:session-owner-source": "verified",
            "verify_session_owner:session-owner-source": "13:77:2:user",
        })

        with patch.object(ticket_service, "get_redis", return_value=redis):
            with self.assertRaises(HTTPException) as ctx:
                await ticket_service.get_verify_status(
                    "session-owner-source",
                    staff_id=77,
                    staff_site_id=2,
                    staff_source="admin",
                )

        self.assertEqual(ctx.exception.status_code, 403)
        self.assertEqual(ctx.exception.detail["code"], 40303)

    async def test_verify_status_rejects_missing_owner_metadata(self):
        from services import ticket_service

        redis = FakeRedis({
            "verify_status:session-without-owner": "verified",
        })

        with patch.object(ticket_service, "get_redis", return_value=redis):
            with self.assertRaises(HTTPException) as ctx:
                await ticket_service.get_verify_status(
                    "session-without-owner",
                    staff_id=77,
                    staff_site_id=2,
                )

        self.assertEqual(ctx.exception.status_code, 403)
        self.assertEqual(ctx.exception.detail["code"], 40303)

    async def test_staff_pending_tickets_include_user_phone_remark_and_quantity(self):
        from services import ticket_service

        ticket = SimpleNamespace(
            id=21,
            ticket_no="T20260627001",
            ticket_type="camping",
            verify_date=date(2026, 6, 27),
            verify_status="pending",
            current_verify_count=0,
            total_verify_count=1,
            created_at=datetime(2026, 6, 20, tzinfo=timezone.utc),
        )
        order = SimpleNamespace(
            id=31,
            order_no="O20260627001",
            user_id=41,
            remark="客户会晚到半小时",
            actual_amount=199,
        )
        item = SimpleNamespace(id=51, quantity=2, date=date(2026, 6, 27), time_slot="14:00")
        product = SimpleNamespace(id=61, name="林间营位")
        user = SimpleNamespace(id=41, nickname="露营用户", phone="13800001234")
        db = FakeDb([(ticket, order, item, product, user)])

        result = await ticket_service.list_staff_pending_tickets(db, staff_site_id=2)

        self.assertEqual(result[0]["ticket_id"], 21)
        self.assertEqual(result[0]["order_id"], 31)
        self.assertEqual(result[0]["order_item_id"], 51)
        self.assertEqual(result[0]["product_name"], "林间营位")
        self.assertEqual(result[0]["user_nickname"], "露营用户")
        self.assertEqual(result[0]["user_phone_masked"], "138****1234")
        self.assertEqual(result[0]["remark"], "客户会晚到半小时")
        self.assertEqual(result[0]["quantity"], 2)
        self.assertEqual(result[0]["time_slot"], "14:00")
        self.assertEqual(result[0]["can_verify"], True)
        sql = compile_query(db.queries[0])
        self.assertIn("ticket.site_id", sql)
        self.assertIn("ticket.site_id = 2", sql)
        self.assertIn('"order".payment_status = \'paid\'', sql)
        self.assertIn('"order".refund_status IN (', sql)
        self.assertIn("product.site_id = 2", sql)
        self.assertIn("product.is_deleted IS false", sql)

    async def test_staff_ticket_logs_include_product_and_verify_date(self):
        from services import ticket_service

        created_at = datetime(2026, 6, 27, 12, 30, tzinfo=timezone.utc)
        log = SimpleNamespace(
            id=71,
            ticket_id=21,
            order_id=31,
            order_item_id=51,
            staff_id=9,
            staff_source="admin",
            verify_result="success",
            failure_reason=None,
            device_info="wx-staff",
            created_at=created_at,
        )
        ticket = SimpleNamespace(ticket_no="T20260627001", verify_date=date(2026, 6, 27))
        order = SimpleNamespace(order_no="O20260627001", remark="客户会晚到半小时")
        item = SimpleNamespace(quantity=2, time_slot="14:00")
        product = SimpleNamespace(name="林间营位")
        user = SimpleNamespace(nickname="露营用户", phone="13800001234")
        db = FakeDb([(log, ticket, order, item, product, user)])

        result = await ticket_service.list_staff_ticket_logs(
            db,
            staff_site_id=2,
            staff_id=9,
            staff_source="admin",
        )

        self.assertEqual(result[0]["id"], 71)
        self.assertEqual(result[0]["ticket_no"], "T20260627001")
        self.assertEqual(result[0]["product_name"], "林间营位")
        self.assertEqual(result[0]["verify_date"], date(2026, 6, 27))
        self.assertEqual(result[0]["quantity"], 2)
        self.assertEqual(result[0]["staff_source"], "admin")
        self.assertEqual(result[0]["user_phone_masked"], "138****1234")
        self.assertEqual(result[0]["remark"], "客户会晚到半小时")
        sql = compile_query(db.queries[0])
        self.assertIn("ticket_verify_log.staff_source = 'admin'", sql)
        self.assertIn("product.site_id = 2", sql)
        self.assertIn("product.is_deleted IS false", sql)

    async def test_staff_today_orders_query_is_ticket_site_scoped_and_day_bounded(self):
        from services import ticket_service

        db = FakeDb([])

        await ticket_service.list_staff_today_orders(
            db,
            staff_site_id=2,
            target_date=date(2026, 6, 27),
        )

        sql = compile_query(db.queries[0])
        self.assertIn("ticket.site_id", sql)
        self.assertIn("ticket.site_id = 2", sql)
        self.assertIn('"order".payment_status = \'paid\'', sql)
        self.assertIn("\"order\".created_at >= '2026-06-27 00:00:00+00:00'", sql)
        self.assertIn("\"order\".created_at < '2026-06-28 00:00:00+00:00'", sql)
        self.assertIn('"order".refund_status IN (', sql)
        self.assertIn("product.site_id = 2", sql)
        self.assertIn("product.is_deleted IS false", sql)

    async def test_staff_order_detail_is_site_scoped_and_contains_items_and_tickets(self):
        from services import ticket_service

        created_at = datetime(2026, 6, 27, 9, 0, tzinfo=timezone.utc)
        order = SimpleNamespace(
            id=31,
            site_id=2,
            order_no="O20260627001",
            user_id=41,
            status="paid",
            payment_status="paid",
            payment_method="wechat_pay",
            actual_amount=199,
            total_amount=199,
            discount_amount=0,
            remark="客户会晚到半小时",
            created_at=created_at,
            payment_time=created_at,
        )
        user = SimpleNamespace(id=41, nickname="露营用户", phone="13800001234")
        item = SimpleNamespace(
            id=51,
            product_id=61,
            sku_id=62,
            quantity=2,
            date=date(2026, 6, 27),
            time_slot="14:00",
            unit_price=99,
            actual_price=198,
        )
        product = SimpleNamespace(id=61, name="林间营位", cover_image="/images/camp.jpg")
        ticket = SimpleNamespace(
            id=21,
            order_item_id=51,
            ticket_no="T20260627001",
            ticket_type="camping",
            verify_status="pending",
            verify_date=date(2026, 6, 27),
            verified_at=None,
            verified_by=None,
            current_verify_count=0,
            total_verify_count=1,
        )
        db = FakeDb(order, [(item, product)], [ticket], user)

        result = await ticket_service.get_staff_order_detail(db, order_id=31, staff_site_id=2)

        self.assertEqual(result["order_id"], 31)
        self.assertEqual(result["order_no"], "O20260627001")
        self.assertEqual(result["user_phone_masked"], "138****1234")
        self.assertEqual(result["remark"], "客户会晚到半小时")
        self.assertEqual(result["items"][0]["product_name"], "林间营位")
        self.assertEqual(result["items"][0]["tickets"][0]["ticket_no"], "T20260627001")
        self.assertEqual(result["items"][0]["tickets"][0]["can_verify"], True)
        item_sql = compile_query(db.queries[1])
        self.assertIn("product.site_id = 2", item_sql)
        self.assertIn("product.is_deleted IS false", item_sql)

    async def test_staff_order_detail_rejects_unworkable_order_status(self):
        from services import ticket_service

        order = SimpleNamespace(
            id=31,
            site_id=2,
            order_no="O20260627001",
            user_id=41,
            status="cancelled",
            payment_status="paid",
            refund_status="none",
            is_deleted=False,
        )
        db = FakeDb(order)

        with self.assertRaises(HTTPException) as ctx:
            await ticket_service.get_staff_order_detail(db, order_id=31, staff_site_id=2)

        self.assertEqual(ctx.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()

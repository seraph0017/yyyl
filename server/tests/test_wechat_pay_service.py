import base64
import json
import unittest
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes, serialization


class WechatPayServiceTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        from services import wechat_pay_service

        self.service = wechat_pay_service
        self.merchant_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.platform_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.merchant_key_pem = self.merchant_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode()
        self.platform_public_pem = self.platform_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode()
        self.api_v3_key = "0123456789abcdeffedcba9876543210"

    def test_build_mini_program_pay_params_signs_expected_message(self):
        config = self.service.WechatPayConfig(
            app_id="wx-test",
            mch_id="1619737660",
            mch_serial_no="SERIAL123",
            api_v3_key=self.api_v3_key,
            private_key_pem=self.merchant_key_pem,
            platform_public_key_pem=self.platform_public_pem,
            platform_public_key_id="PUB_KEY_ID_TEST",
            notify_url="https://www.yyylcamp.com/api/v1/payments/wechat/notify",
            refund_notify_url="https://www.yyylcamp.com/api/v1/payments/wechat/refund-notify",
        )

        params = self.service.build_mini_program_pay_params(
            config,
            prepay_id="wx_pre_123",
            timestamp="1710000000",
            nonce_str="nonce-123",
        )

        self.assertEqual(params["appId"], "wx-test")
        self.assertEqual(params["package"], "prepay_id=wx_pre_123")
        message = "wx-test\n1710000000\nnonce-123\nprepay_id=wx_pre_123\n".encode()
        self.merchant_key.public_key().verify(
            base64.b64decode(params["paySign"]),
            message,
            padding.PKCS1v15(),
            hashes.SHA256(),
        )

    async def test_create_jsapi_prepay_posts_wechat_payload_and_returns_pay_params(self):
        config = self.service.WechatPayConfig(
            app_id="wx-test",
            mch_id="1619737660",
            mch_serial_no="SERIAL123",
            api_v3_key=self.api_v3_key,
            private_key_pem=self.merchant_key_pem,
            platform_public_key_pem=self.platform_public_pem,
            platform_public_key_id="PUB_KEY_ID_TEST",
            notify_url="https://www.yyylcamp.com/api/v1/payments/wechat/notify",
            refund_notify_url="https://www.yyylcamp.com/api/v1/payments/wechat/refund-notify",
        )
        order = SimpleNamespace(
            order_no="YY202606140001",
            actual_amount=Decimal("12.34"),
            expire_at=None,
            user=SimpleNamespace(openid="openid-test"),
            id=18,
        )
        response = SimpleNamespace(
            status_code=200,
            json=lambda: {"prepay_id": "wx_pre_123"},
            text='{"prepay_id":"wx_pre_123"}',
        )

        async_client = AsyncMock()
        async_client.__aenter__.return_value.post.return_value = response

        with (
            patch.object(self.service, "get_wechat_pay_config", return_value=config),
            patch.object(self.service.httpx, "AsyncClient", return_value=async_client),
            patch.object(self.service, "_utc_timestamp", return_value="1710000000"),
            patch.object(self.service, "_nonce_str", return_value="nonce-123"),
        ):
            params = await self.service.create_jsapi_prepay(order, site_id=1)

        post_call = async_client.__aenter__.return_value.post.call_args
        self.assertEqual(post_call.args[0], "https://api.mch.weixin.qq.com/v3/pay/transactions/jsapi")
        payload = json.loads(post_call.kwargs["content"].decode())
        self.assertEqual(payload["mchid"], "1619737660")
        self.assertEqual(payload["appid"], "wx-test")
        self.assertEqual(payload["out_trade_no"], "YY202606140001")
        self.assertEqual(payload["amount"]["total"], 1234)
        self.assertEqual(payload["payer"]["openid"], "openid-test")
        self.assertIn("time_expire", payload)
        self.assertNotIn("Wechatpay-Serial", post_call.kwargs["headers"])
        self.assertIn('serial_no="SERIAL123"', post_call.kwargs["headers"]["Authorization"])
        self.assertEqual(params["package"], "prepay_id=wx_pre_123")

    def test_decrypt_notification_resource_returns_plain_payload(self):
        plaintext = {"out_trade_no": "YY202606140001", "transaction_id": "4200001"}
        nonce = b"nonce-123456"
        associated_data = b"transaction"
        ciphertext = AESGCM(self.api_v3_key.encode()).encrypt(
            nonce,
            json.dumps(plaintext).encode(),
            associated_data,
        )
        resource = {
            "nonce": nonce.decode(),
            "associated_data": associated_data.decode(),
            "ciphertext": base64.b64encode(ciphertext).decode(),
        }

        result = self.service.decrypt_notification_resource(self.api_v3_key, resource)

        self.assertEqual(result, plaintext)

    def test_verify_notification_signature_accepts_valid_wechat_signature(self):
        body = '{"id":"notify-id"}'
        timestamp = "1710000000"
        nonce = "nonce-123"
        message = f"{timestamp}\n{nonce}\n{body}\n".encode()
        signature = self.platform_key.sign(message, padding.PKCS1v15(), hashes.SHA256())

        self.assertTrue(
            self.service.verify_notification_signature(
                self.platform_public_pem,
                timestamp,
                nonce,
                body,
                base64.b64encode(signature).decode(),
            )
        )


if __name__ == "__main__":
    unittest.main()

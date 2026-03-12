"""临时测试脚本 — 验证所有新建模块"""

# ---- 测试 schemas 导入 ----
from schemas.common import ResponseModel, PaginatedResponse, PaginationParams, ErrorResponse, SortParams
from schemas.user import (UserInfo, UserIdentityCreate, UserIdentityUpdate, UserIdentityResponse,
                          UserAddressCreate, UserAddressUpdate, UserAddressResponse)
from schemas.auth import (WxLoginRequest, WxLoginResponse, AdminLoginRequest, AdminLoginResponse,
                          TokenRefreshRequest, TokenRefreshResponse, TokenPayload)
from schemas.product import (ProductListItem, ProductDetail, ProductCreate, ProductUpdate,
                             PricingRuleSchema, SKUSchema, InventoryQuery, InventoryResponse, ProductSearchParams)
from schemas.order import (OrderCreateRequest, OrderCreateItem, OrderResponse, OrderItemResponse,
                           OrderListParams, RefundRequest, TicketResponse)
from schemas.member import (AnnualCardInfo, AnnualCardPurchaseRequest, AnnualCardBookingCheck,
                            TimesCardInfo, ActivationCodeActivateRequest, PointsInfo, PointsExchangeRequest)
from schemas.finance import (FinanceAccountInfo, WithdrawRequest, TransactionListParams,
                             TransactionResponse, DepositRefundRequest)
from schemas.admin import (AdminUserCreate, AdminUserUpdate, AdminUserResponse,
                           DashboardOverview, SalesReportParams, SalesReportResponse, OperationLogResponse)
from schemas.notification import NotificationResponse, NotificationListParams

print("✅ 所有 schemas 导入成功！")

# ---- 测试 utils ----
from utils.security import (create_access_token, create_refresh_token, verify_token,
                            hash_password, verify_password, encrypt_sensitive, decrypt_sensitive,
                            hash_sensitive, mask_id_card)
from utils.helpers import (generate_order_no, generate_ticket_code, generate_verification_code,
                           format_price, generate_qr_token, generate_batch_no, generate_activation_code)

# AES-256 加密解密
test_data = "110101199001011234"
encrypted = encrypt_sensitive(test_data)
decrypted = decrypt_sensitive(encrypted)
assert decrypted == test_data
print(f"✅ AES-256 加密解密通过: {test_data} -> {encrypted[:20]}...")

# 密码哈希
hashed = hash_password("test123456")
assert verify_password("test123456", hashed)
assert not verify_password("wrong", hashed)
print("✅ 密码哈希测试通过")

# JWT Token
token = create_access_token({"sub": "123", "role": "user"})
payload = verify_token(token)
assert payload["sub"] == "123" and payload["role"] == "user" and payload["token_type"] == "access"
print("✅ JWT Token 测试通过")

# 刷新 Token
rt = create_refresh_token({"sub": "123", "role": "user"})
rt_payload = verify_token(rt)
assert rt_payload["token_type"] == "refresh"
print("✅ Refresh Token 测试通过")

# 工具函数
print(f"✅ 订单号: {generate_order_no()}")
print(f"✅ 验票码: {generate_ticket_code()}")
print(f"✅ 验证码: {generate_verification_code()}")
print(f"✅ 二维码Token: {generate_qr_token()}")
print(f"✅ 批次号: {generate_batch_no()}")
print(f"✅ 激活码: {generate_activation_code()}")

# 脱敏
assert mask_id_card("110101199001011234") == "1101**********1234"
print(f"✅ 身份证脱敏: {mask_id_card('110101199001011234')}")

# 价格格式化
from decimal import Decimal
assert format_price(Decimal("128.5")) == "¥128.50"
print(f"✅ 价格格式化: {format_price(Decimal('128.5'))}")

# ---- 测试模型序列化 ----
resp = ResponseModel.success(data={"test": True})
d = resp.model_dump()
assert d["code"] == 0 and d["data"]["test"] is True
print(f"✅ ResponseModel: code={d['code']}, message={d['message']}")

paginated = PaginatedResponse.create(items=[{"a": 1}], total=100, page=1, page_size=20)
assert paginated.data.pagination.total_pages == 5
print(f"✅ PaginatedResponse: total_pages={paginated.data.pagination.total_pages}")

# 分页参数校验
params = PaginationParams(page=3, page_size=15)
assert params.offset == 30
print(f"✅ PaginationParams: offset={params.offset}")

# 错误码
err = ErrorResponse(code=40001, message="参数校验失败")
print(f"✅ ErrorResponse: code={err.code}")

# ---- middleware 导入测试 ----
from middleware.auth import (get_current_user, get_current_active_user, require_role,
                             get_optional_user, get_current_admin, require_admin_role, require_permission)
print("✅ 认证中间件导入成功！")

print("\n🎉 全部测试通过！所有模块正常工作。")

"""
数据模型包
导入所有模型以确保 SQLAlchemy 和 Alembic 能发现完整的元数据
"""

from models.base import Base  # noqa: F401

# 用户模块 (4张表)
from models.user import (  # noqa: F401
    IdentityFieldConfig,
    User,
    UserAddress,
    UserIdentity,
)

# 商品模块 (11张表)
from models.product import (  # noqa: F401
    DateTypeConfig,
    DiscountRule,
    Inventory,
    InventoryLog,
    PricingRule,
    Product,
    ProductExtActivity,
    ProductExtCamping,
    ProductExtRental,
    ProductExtShop,
    SKU,
)

# 搭配售卖模块 (3张表) - v1.5新增
from models.bundle import (  # noqa: F401
    BundleConfig,
    BundleItem,
    ProductExtInsurance,
)

# 订单模块 (5张表)
from models.order import (  # noqa: F401
    Cart,
    CartItem,
    Order,
    OrderItem,
    Ticket,
)

# 会员模块 (9张表)
from models.member import (  # noqa: F401
    ActivationCode,
    AnnualCard,
    AnnualCardBookingRecord,
    AnnualCardConfig,
    PointsExchangeConfig,
    PointsRecord,
    TimesCard,
    TimesCardConfig,
    TimesConsumptionRule,
)

# 财务模块 (3张表)
from models.finance import (  # noqa: F401
    DepositRecord,
    FinanceAccount,
    FinanceTransaction,
)

# 管理模块 (7张表)
from models.admin import (  # noqa: F401
    AdminPermission,
    AdminRole,
    AdminUser,
    DailyReport,
    MonthlyReport,
    OperationLog,
    WeeklyReport,
)

# 内容模块 (5张表)
from models.content import (  # noqa: F401
    DisclaimerSignature,
    DisclaimerTemplate,
    FaqCategory,
    FaqItem,
    PageConfig,
)

# 通知模块 (1张表)
from models.notification import Notification  # noqa: F401

# 前端增强模块 (3张表) - v1.5新增
from models.camp_map import (  # noqa: F401
    CampMap,
    CampMapZone,
    MiniGame,
)

# 报销模块 (2张表) - v1.5新增
from models.expense import (  # noqa: F401
    ExpenseRequest,
    ExpenseType,
)

# 绩效模块 (3张表) - v1.5新增
from models.performance import (  # noqa: F401
    PerformanceConfig,
    PerformanceDetail,
    PerformanceRecord,
)

# CMS模块 (4张表) - v1.6新增
from models.cms import (  # noqa: F401
    CmsAsset,
    CmsComponent,
    CmsPage,
    CmsPageVersion,
)

# 所有模型总计: 4 + 11 + 3 + 5 + 9 + 3 + 7 + 5 + 1 + 3 + 2 + 3 + 4 = 60 张表

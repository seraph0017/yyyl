"""
购物车相关 Schemas

- CartAddItemRequest：添加商品到购物车
- CartCheckoutRequest：购物车结算
"""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CartAddItemRequest(BaseModel):
    """添加商品到购物车请求"""

    model_config = ConfigDict(populate_by_name=True)

    product_id: int = Field(description="商品ID")
    sku_id: Optional[int] = Field(default=None, description="SKU ID（多规格商品）")
    quantity: int = Field(default=1, ge=1, description="数量")

    @field_validator("product_id")
    @classmethod
    def validate_product_id(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("product_id 必须为正整数")
        return v


class CartCheckoutRequest(BaseModel):
    """购物车结算请求"""

    model_config = ConfigDict(populate_by_name=True)

    item_ids: List[int] = Field(min_length=1, description="要结算的购物车商品ID列表")
    address_id: Optional[int] = Field(default=None, description="收货地址ID（周边商品/邮寄）")
    remark: Optional[str] = Field(default=None, max_length=200, description="备注")

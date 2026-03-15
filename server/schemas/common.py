"""
通用响应模型 & 分页参数

统一响应格式对齐架构文档 3.1.2 规范：
- ResponseModel[T]：成功响应
- PaginatedResponse[T]：分页响应
- PaginationParams：分页请求参数
- ErrorDetail / ErrorResponse：错误响应
"""


import math
import time
from typing import Any, Generic, List, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


# ---- 成功响应 ----

class ResponseModel(BaseModel, Generic[T]):
    """统一成功响应格式

    ```json
    { "code": 0, "message": "success", "data": { ... }, "timestamp": 1710144000 }
    ```
    """

    model_config = ConfigDict(populate_by_name=True)

    code: int = Field(default=0, description="业务状态码，0=成功")
    message: str = Field(default="success", description="状态消息")
    data: Optional[T] = Field(default=None, description="响应数据")
    timestamp: int = Field(default_factory=lambda: int(time.time()), description="时间戳")

    @classmethod
    def success(cls, data: Any = None, message: str = "success") -> "ResponseModel":
        """快速构建成功响应"""
        return cls(code=0, message=message, data=data)

    @classmethod
    def error(cls, code: int, message: str, data: Any = None) -> "ResponseModel":
        """快速构建错误响应"""
        return cls(code=code, message=message, data=data)


# ---- 分页相关 ----

class PaginationInfo(BaseModel):
    """分页信息"""

    model_config = ConfigDict(populate_by_name=True)

    page: int = Field(description="当前页码")
    page_size: int = Field(description="每页数量")
    total: int = Field(description="总记录数")
    total_pages: int = Field(description="总页数")


class PaginatedData(BaseModel, Generic[T]):
    """分页数据结构（嵌套在 data 字段中）

    对齐架构文档格式：
    ```json
    { "list": [...], "pagination": { "page": 1, "page_size": 20, "total": 150, "total_pages": 8 } }
    ```
    """

    model_config = ConfigDict(populate_by_name=True)

    list: List[T] = Field(default_factory=list, description="数据列表")
    pagination: PaginationInfo = Field(description="分页信息")


class PaginatedResponse(BaseModel, Generic[T]):
    """分页响应格式"""

    model_config = ConfigDict(populate_by_name=True)

    code: int = Field(default=0, description="业务状态码")
    message: str = Field(default="success", description="状态消息")
    data: PaginatedData[T] = Field(description="分页数据")
    timestamp: int = Field(default_factory=lambda: int(time.time()), description="时间戳")

    @classmethod
    def create(
        cls,
        items: List[Any],
        total: int,
        page: int,
        page_size: int,
        message: str = "success",
    ) -> "PaginatedResponse":
        """快速构建分页响应"""
        total_pages = math.ceil(total / page_size) if page_size > 0 else 0
        return cls(
            code=0,
            message=message,
            data=PaginatedData(
                list=items,
                pagination=PaginationInfo(
                    page=page,
                    page_size=page_size,
                    total=total,
                    total_pages=total_pages,
                ),
            ),
        )


class PaginationParams(BaseModel):
    """分页请求参数（Query Parameters）"""

    model_config = ConfigDict(populate_by_name=True)

    page: int = Field(default=1, ge=1, description="页码，从1开始")
    page_size: int = Field(default=20, ge=1, le=100, description="每页数量，最大100")

    @property
    def offset(self) -> int:
        """计算数据库查询偏移量"""
        return (self.page - 1) * self.page_size


class AdminPaginationParams(BaseModel):
    """管理端分页参数（允许更大的 page_size，用于下拉选择等场景）"""

    model_config = ConfigDict(populate_by_name=True)

    page: int = Field(default=1, ge=1, description="页码，从1开始")
    page_size: int = Field(default=20, ge=1, le=500, description="每页数量，最大500")

    @property
    def offset(self) -> int:
        """计算数据库查询偏移量"""
        return (self.page - 1) * self.page_size


# ---- 错误响应 ----

class ErrorDetail(BaseModel):
    """字段级错误详情"""

    field: str = Field(description="错误字段名")
    message: str = Field(description="错误描述")


class ErrorResponse(BaseModel):
    """统一错误响应格式

    ```json
    { "code": 40001, "message": "参数校验失败", "errors": [...], "timestamp": 1710144000 }
    ```
    """

    model_config = ConfigDict(populate_by_name=True)

    code: int = Field(description="错误码")
    message: str = Field(description="错误消息")
    errors: Optional[List[ErrorDetail]] = Field(default=None, description="字段错误详情")
    timestamp: int = Field(default_factory=lambda: int(time.time()), description="时间戳")


# ---- 排序参数 ----

class SortParams(BaseModel):
    """排序参数"""

    model_config = ConfigDict(populate_by_name=True)

    sort_by: Optional[str] = Field(default=None, description="排序字段")
    sort_order: Optional[str] = Field(default="desc", pattern="^(asc|desc)$", description="排序方向: asc/desc")

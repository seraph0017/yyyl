# 一月一露 (yyyl) 后台管理系统 — 代码模式指南

> 完整的 Vue 3 + TypeScript + Element Plus 管理系统代码模式探索
>
> **日期**: 2026-04-01
> **项目**: 一月一露 多营地露营运营平台
> **模块**: admin/ (后台管理仪表板)

---

## 目录

1. [项目结构](#项目结构)
2. [核心技术栈](#核心技术栈)
3. [API 模块模式](#api-模块模式)
4. [Vue 3 组件模式](#vue-3-组件模式)
5. [Pinia 状态管理模式](#pinia-状态管理模式)
6. [路由配置模式](#路由配置模式)
7. [HTTP 请求与认证](#http-请求与认证)
8. [类型系统](#类型系统)
9. [样式与主题系统](#样式与主题系统)
10. [工具函数](#工具函数)
11. [开发规范](#开发规范)

---

## 项目结构

```
admin/
├── src/
│   ├── api/              # API 接口层（15+ 模块）
│   │   ├── auth.ts       # 认证相关
│   │   ├── product.ts    # 商品管理
│   │   ├── order.ts      # 订单管理
│   │   ├── member.ts     # 会员管理
│   │   ├── ...           # 其他业务模块
│   │
│   ├── views/            # 页面组件（24+ 页面）
│   │   ├── products/
│   │   │   ├── index.vue      # 商品列表
│   │   │   └── edit.vue       # 商品编辑
│   │   ├── orders/
│   │   ├── members/
│   │   ├── dashboard/
│   │   └── ...
│   │
│   ├── stores/           # Pinia 状态管理
│   │   ├── app.ts        # 全局应用状态
│   │   └── user.ts       # 用户认证状态
│   │
│   ├── router/
│   │   └── index.ts      # Vue Router 配置
│   │
│   ├── components/       # 共享组件（简单展示组件）
│   │   └── HelloWorld.vue
│   │
│   ├── types/            # TypeScript 类型定义
│   │   ├── index.ts      # 主类型文件（17K+）
│   │   └── campsite.ts   # 营地特定类型
│   │
│   ├── utils/
│   │   ├── request.ts    # HTTP 客户端（Axios 封装）
│   │   └── index.ts      # 通用工具函数
│   │
│   ├── config/
│   │   └── brand.ts      # 品牌配置
│   │
│   ├── styles/
│   │   ├── index.scss    # 全局设计系统
│   │   └── element.scss  # Element Plus 主题定制
│   │
│   ├── layout/
│   │   └── index.vue     # 主布局（侧边栏+头部+主区）
│   │
│   ├── App.vue
│   ├── main.ts
│   └── components.d.ts   # 自动导入生成
│
├── vite.config.ts        # Vite 构建配置
├── tsconfig.json
├── package.json
└── README.md
```

---

## 核心技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| **Vue** | 3.5.25 | 前端框架 |
| **TypeScript** | 5.9.3 | 类型系统 |
| **Vite** | 7.3.1 | 构建工具 |
| **Vue Router** | 4.6.4 | 路由管理 |
| **Pinia** | 3.0.4 | 状态管理 |
| **Element Plus** | 2.13.5 | UI 组件库 |
| **Axios** | 1.13.6 | HTTP 客户端 |
| **ECharts** | 6.0.0 | 数据可视化 |
| **dayjs** | 1.11.19 | 日期处理 |
| **SCSS** | 1.98.0 | 样式预处理 |

---

## API 模块模式

### 文件: `src/api/product.ts`

**设计原则:**
- 每个业务域一个 API 模块
- 导出具名函数，每个函数对应一个 API 端点
- 使用泛型定义响应数据类型
- 分组相关接口（CRUD、规则、库存等）

```typescript
import { get, post, put, del } from '@/utils/request'
import type {
  Product, ProductCreateRequest, ProductSearchParams,
  PricingRule, DiscountRule, Inventory, InventoryUpdateRequest, InventoryBatchRequest,
  PaginatedResponse, CalendarQuery, CalendarItem
} from '@/types'

// ==================== 商品 CRUD ====================

export function getProducts(params: ProductSearchParams) {
  return get<{ data: PaginatedResponse<Product> }>('/admin/products', params)
}

export function getProductDetail(id: number) {
  return get<{ data: Product }>(`/products/${id}`)
}

export function createProduct(data: ProductCreateRequest) {
  return post<{ data: Product }>('/admin/products', data)
}

export function updateProduct(id: number, data: Partial<ProductCreateRequest>) {
  return put<{ data: Product }>(`/admin/products/${id}`, data)
}

export function deleteProduct(id: number) {
  return del(`/admin/products/${id}`)
}

export function updateProductStatus(id: number, status: string) {
  return put(`/admin/products/${id}/status`, { status })
}

// ==================== 定价规则 ====================

export function getPricingRules(productId: number) {
  return get<{ data: PricingRule[] }>(`/admin/products/${productId}/pricing-rules`)
}

export function createPricingRule(productId: number, data: Partial<PricingRule>) {
  return post(`/admin/products/${productId}/pricing-rules`, data)
}

// ... 更多接口
```

**关键特性:**
- ✅ 使用 `import type` 仅导入类型（编译后消失，减小 bundle）
- ✅ 泛型参数清晰：`get<{ data: PaginatedResponse<T> }>(url, params)`
- ✅ 按业务逻辑分组相关接口
- ✅ 使用模板字符串处理动态路由参数

---

## Vue 3 组件模式

### 列表页面: `src/views/products/index.vue`

**结构:**
1. **Template** - 搜索栏 + 表格 + 分页
2. **Script Setup** - 状态、事件处理、数据加载
3. **Scoped Styles** - 使用 CSS 变量

```vue
<template>
  <div class="page-container">
    <div class="card-box">
      <!-- 搜索栏 -->
      <div class="flex-between mb-16">
        <div class="search-bar">
          <el-input v-model="searchParams.keyword" placeholder="搜索商品名称" clearable style="width: 240px" @clear="handleSearch">
            <template #prefix><el-icon><Search /></el-icon></template>
          </el-input>
          <el-select v-model="searchParams.category" placeholder="品类筛选" clearable style="width: 140px" @change="handleSearch">
            <el-option v-for="(label, key) in categoryMap" :key="key" :label="label" :value="key" />
          </el-select>
          <el-select v-model="searchParams.status" placeholder="状态" clearable style="width: 120px" @change="handleSearch">
            <el-option label="上架" value="active" />
            <el-option label="下架" value="inactive" />
            <el-option label="草稿" value="draft" />
          </el-select>
          <el-button type="primary" @click="handleSearch">
            <el-icon><Search /></el-icon>搜索
          </el-button>
        </div>
        <el-button type="primary" @click="router.push('/products/create')">
          <el-icon><Plus /></el-icon>新增商品
        </el-button>
      </div>

      <!-- 表格 -->
      <el-table :data="tableData" v-loading="loading" stripe>
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column label="商品信息" min-width="280">
          <template #default="{ row }">
            <div class="product-info">
              <el-image :src="row.cover_image" class="product-cover" fit="cover">
                <template #error><div class="image-placeholder"><el-icon><Picture /></el-icon></div></template>
              </el-image>
              <div>
                <div class="product-name">{{ row.name }}</div>
                <el-tag size="small" type="info">{{ getCategoryName(row.category) }}</el-tag>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="基础价" width="120" align="right">
          <template #default="{ row }">
            <span class="price">¥{{ formatPrice(row.base_price) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : row.status === 'draft' ? 'info' : 'danger'" size="small">
              {{ row.status === 'active' ? '上架' : row.status === 'draft' ? '草稿' : '下架' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="sort_order" label="排序" width="80" align="center" />
        <el-table-column label="更新时间" width="170">
          <template #default="{ row }">{{ formatDateTime(row.updated_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right" align="center">
          <template #default="{ row }">
            <div class="action-buttons">
              <el-tooltip content="编辑" placement="top" :show-after="400">
                <el-button class="action-btn action-btn--edit" circle size="small" @click="router.push(`/products/${row.id}/edit`)">
                  <el-icon><Edit /></el-icon>
                </el-button>
              </el-tooltip>
              <el-tooltip :content="row.status === 'active' ? '下架' : '上架'" placement="top" :show-after="400">
                <el-button
                  class="action-btn"
                  :class="row.status === 'active' ? 'action-btn--offline' : 'action-btn--online'"
                  circle size="small"
                  @click="handleToggleStatus(row)"
                >
                  <el-icon>
                    <Bottom v-if="row.status === 'active'" />
                    <Top v-else />
                  </el-icon>
                </el-button>
              </el-tooltip>
              <el-popconfirm title="确定删除该商品？" @confirm="handleDelete(row.id)" width="200">
                <template #reference>
                  <el-tooltip content="删除" placement="top" :show-after="400">
                    <el-button class="action-btn action-btn--delete" circle size="small">
                      <el-icon><Delete /></el-icon>
                    </el-button>
                  </el-tooltip>
                </template>
              </el-popconfirm>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="searchParams.page"
          v-model:page-size="searchParams.page_size"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="fetchData"
          @current-change="fetchData"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Search, Plus, Picture, Edit, Delete, Top, Bottom } from '@element-plus/icons-vue'
import { getProducts, updateProductStatus, deleteProduct } from '@/api/product'
import { formatPrice, formatDateTime, getCategoryName, categoryMap } from '@/utils'
import type { Product, ProductSearchParams } from '@/types'

// ==================== 状态管理 ====================
const router = useRouter()
const loading = ref(false)
const tableData = ref<Product[]>([])
const total = ref(0)

const searchParams = reactive<ProductSearchParams>({
  page: 1,
  page_size: 20,
  keyword: '',
  category: undefined,
  status: undefined,
})

// ==================== 数据加载 ====================
async function fetchData() {
  loading.value = true
  try {
    const res = await getProducts(searchParams)
    tableData.value = res.data.list
    total.value = res.data.pagination.total
  } catch {
    // 错误由 request 拦截器处理
    tableData.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

// ==================== 事件处理 ====================
function handleSearch() {
  searchParams.page = 1  // 搜索时重置到第 1 页
  fetchData()
}

async function handleToggleStatus(row: Product) {
  const newStatus = row.status === 'active' ? 'inactive' : 'active'
  try {
    await updateProductStatus(row.id, newStatus)
    ElMessage.success(`已${newStatus === 'active' ? '上架' : '下架'}`)
    row.status = newStatus  // 本地更新表格
  } catch {
    // 错误由 request 拦截器处理
  }
}

async function handleDelete(id: number) {
  try {
    await deleteProduct(id)
    ElMessage.success('删除成功')
    fetchData()  // 重新加载列表
  } catch {
    // 错误由 request 拦截器处理
  }
}

// ==================== 生命周期 ====================
onMounted(fetchData)
</script>

<style lang="scss" scoped>
.search-bar {
  display: flex;
  gap: 12px;
  align-items: center;
}

.product-info {
  display: flex;
  align-items: center;
  gap: 14px;

  .product-cover {
    width: 52px;
    height: 52px;
    border-radius: var(--radius-small);
    flex-shrink: 0;
    box-shadow: var(--shadow-light);
  }

  .image-placeholder {
    width: 52px;
    height: 52px;
    background: linear-gradient(135deg, var(--color-bg), var(--color-bg-warm));
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--color-text-placeholder);
    border-radius: var(--radius-small);
    border: 1px solid var(--color-border-light);
  }

  .product-name {
    font-size: 14px;
    font-weight: 600;
    margin-bottom: 6px;
    color: var(--color-text);
    letter-spacing: 0.3px;
  }
}

.price {
  font-weight: 700;
  color: var(--color-accent);
  letter-spacing: 0.5px;
}

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid var(--color-border-light);
}
</style>
```

**关键特性:**
- ✅ `<script setup>` 语法（Vue 3 推荐）
- ✅ 分离关注点：状态、数据加载、事件处理、生命周期
- ✅ `reactive` 用于搜索参数对象，`ref` 用于原始类型和数组
- ✅ 使用导入的工具函数格式化数据
- ✅ 错误处理委托给 HTTP 拦截器
- ✅ 表格操作按钮使用统一的 `action-btn--*` 样式类

### 编辑页面: `src/views/products/edit.vue`

```vue
<template>
  <div class="page-container">
    <div class="card-box">
      <div class="flex-between mb-20">
        <h3>{{ isEdit ? '编辑商品' : '新增商品' }}</h3>
        <el-button @click="router.back()">返回</el-button>
      </div>

      <el-form ref="formRef" :model="form" :rules="rules" label-width="120px" style="max-width: 800px;">
        <el-form-item label="商品名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入商品名称" maxlength="50" show-word-limit />
        </el-form-item>

        <el-form-item label="商品品类" prop="category">
          <el-select v-model="form.category" placeholder="请选择品类" style="width: 100%;">
            <el-option v-for="(label, key) in categoryMap" :key="key" :label="label" :value="key" />
          </el-select>
        </el-form-item>

        <el-form-item label="基础价格（分）" prop="base_price">
          <el-input-number v-model="form.base_price" :min="0" :step="100" style="width: 100%;" />
        </el-form-item>

        <el-form-item label="市场价（分）">
          <el-input-number v-model="form.market_price" :min="0" :step="100" style="width: 100%;" />
        </el-form-item>

        <el-form-item label="单位">
          <el-input v-model="form.unit" placeholder="如：晚、人次、份" />
        </el-form-item>

        <el-form-item label="封面图" prop="cover_image">
          <el-input v-model="form.cover_image" placeholder="请输入图片URL" />
        </el-form-item>

        <el-form-item label="商品描述">
          <el-input v-model="form.description" type="textarea" :rows="4" placeholder="请输入商品描述" />
        </el-form-item>

        <el-form-item label="排序权重">
          <el-input-number v-model="form.sort_order" :min="0" :max="9999" />
        </el-form-item>

        <el-form-item label="标签">
          <el-select v-model="form.tags" multiple filterable allow-create placeholder="添加标签" style="width: 100%;">
            <el-option label="热门" value="热门" />
            <el-option label="推荐" value="推荐" />
            <el-option label="新品" value="新品" />
            <el-option label="限时" value="限时" />
          </el-select>
        </el-form-item>

        <el-form-item label="需要身份登记">
          <el-switch v-model="form.require_identity" />
        </el-form-item>

        <el-form-item label="需要免责声明">
          <el-switch v-model="form.require_disclaimer" />
        </el-form-item>

        <el-form-item label="状态">
          <el-radio-group v-model="form.status">
            <el-radio value="draft">草稿</el-radio>
            <el-radio value="active">上架</el-radio>
            <el-radio value="inactive">下架</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" :loading="saving" @click="handleSubmit">保存</el-button>
          <el-button @click="router.back()">取消</el-button>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { getProductDetail, createProduct, updateProduct } from '@/api/product'
import { categoryMap } from '@/utils'
import type { ProductCreateRequest } from '@/types'

// ==================== 路由相关 ====================
const router = useRouter()
const route = useRoute()

// ==================== 状态管理 ====================
const formRef = ref<FormInstance>()
const saving = ref(false)

const isEdit = computed(() => !!route.params.id)
const productId = computed(() => Number(route.params.id))

// ==================== 表单数据 ====================
const form = reactive<ProductCreateRequest>({
  name: '',
  category: 'activity',
  base_price: 0,
  market_price: undefined,
  unit: '',
  cover_image: '',
  images: [],
  description: '',
  sort_order: 0,
  tags: [],
  require_identity: false,
  require_disclaimer: false,
  status: 'draft',
})

// ==================== 表单验证规则 ====================
const rules: FormRules = {
  name: [{ required: true, message: '请输入商品名称', trigger: 'blur' }],
  category: [{ required: true, message: '请选择品类', trigger: 'change' }],
  base_price: [{ required: true, message: '请输入价格', trigger: 'blur' }],
  cover_image: [{ required: true, message: '请设置封面图', trigger: 'blur' }],
}

// ==================== 数据加载 ====================
async function fetchDetail() {
  if (!isEdit.value) return
  try {
    const res = await getProductDetail(productId.value)
    Object.assign(form, res.data)  // 使用 Object.assign 而不是 = 保持响应式
  } catch {}
}

// ==================== 表单提交 ====================
async function handleSubmit() {
  if (!formRef.value) return

  // 先验证表单
  await formRef.value.validate()

  saving.value = true
  try {
    if (isEdit.value) {
      await updateProduct(productId.value, form)
      ElMessage.success('更新成功')
    } else {
      await createProduct(form)
      ElMessage.success('创建成功')
    }
    router.push('/products')
  } catch {} finally {
    saving.value = false
  }
}

// ==================== 生命周期 ====================
onMounted(fetchDetail)
</script>
```

**关键特性:**
- ✅ 使用 `computed` 判断编辑 vs 创建模式
- ✅ 使用 `FormRules` 类型定义表单验证规则
- ✅ 表单验证后再提交：`await formRef.value.validate()`
- ✅ 使用 `Object.assign()` 保持响应式而不是直接赋值

---

## Pinia 状态管理模式

### 应用全局状态: `src/stores/app.ts`

```typescript
// 某露营地 — 应用全局状态
import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAppStore = defineStore('app', () => {
  // ==================== 状态 ====================
  const sidebarCollapsed = ref(false)
  const loading = ref(false)

  // ==================== 操作 ====================
  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  function setLoading(val: boolean) {
    loading.value = val
  }

  // ==================== 导出 ====================
  return {
    sidebarCollapsed,
    loading,
    toggleSidebar,
    setLoading,
  }
})
```

### 用户认证状态: `src/stores/user.ts`

```typescript
// 某露营地 — 用户状态管理
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { AdminUserInfo } from '@/types'
import { login as loginApi, logout as logoutApi, getMe } from '@/api/auth'
import { setToken, clearToken, getToken } from '@/utils/request'
import router from '@/router'

export const useUserStore = defineStore('user', () => {
  // ==================== 状态 ====================
  const userInfo = ref<AdminUserInfo | null>(null)
  const isVerified = ref(false)  // 是否已通过服务端验证

  // ==================== 计算属性 ====================
  const isLoggedIn = computed(() => !!getToken())
  const roleName = computed(() => userInfo.value?.role?.role_name || '')
  const roleCode = computed(() => userInfo.value?.role?.role_code || '')
  const isAdmin = computed(() => ['admin', 'super_admin'].includes(roleCode.value))
  const isSuperAdmin = computed(() => roleCode.value === 'super_admin')

  // ==================== 初始化 ====================
  function initUser() {
    const cached = localStorage.getItem('user_info')
    if (cached) {
      try {
        userInfo.value = JSON.parse(cached)
      } catch {
        localStorage.removeItem('user_info')
      }
    }
  }

  // ==================== Token 验证 ====================
  async function verifyAndRefreshUser(): Promise<boolean> {
    if (isVerified.value) return true
    if (!getToken()) return false
    try {
      const res = await getMe()
      userInfo.value = res.data
      localStorage.setItem('user_info', JSON.stringify(res.data))
      isVerified.value = true
      return true
    } catch {
      userInfo.value = null
      clearToken()
      isVerified.value = false
      return false
    }
  }

  // ==================== 角色检查 ====================
  function hasRole(roles: string[]): boolean {
    return !!roleCode.value && roles.includes(roleCode.value)
  }

  // ==================== 登录 ====================
  async function login(username: string, password: string) {
    const res = await loginApi({ username, password })
    const data = res.data
    setToken(data.access_token, data.refresh_token)
    userInfo.value = data.user
    localStorage.setItem('user_info', JSON.stringify(data.user))
    isVerified.value = true
    return data
  }

  // ==================== 获取最新用户信息 ====================
  async function fetchUserInfo() {
    try {
      const res = await getMe()
      userInfo.value = res.data
      localStorage.setItem('user_info', JSON.stringify(res.data))
      isVerified.value = true
    } catch {
      logout()
    }
  }

  // ==================== 登出 ====================
  async function logout() {
    try {
      await logoutApi()
    } catch {
      // 忽略登出接口失败
    } finally {
      userInfo.value = null
      isVerified.value = false
      clearToken()
      router.push('/login')
    }
  }

  // ==================== 导出 ====================
  return {
    userInfo,
    isLoggedIn,
    isVerified,
    roleName,
    roleCode,
    isAdmin,
    isSuperAdmin,
    initUser,
    verifyAndRefreshUser,
    hasRole,
    login,
    fetchUserInfo,
    logout,
  }
})
```

**关键特性:**
- ✅ 使用 Composition API 风格的 `defineStore`
- ✅ 计算属性用于派生状态（`isLoggedIn`, `roleName` 等）
- ✅ 异步操作（`login`, `verifyAndRefreshUser` 等）与数据同步
- ✅ LocalStorage 持久化用户信息
- ✅ Token 有效性验证（特别是页面刷新后）
- ✅ 角色权限检查方法 `hasRole()`

---

## 路由配置模式

### 文件: `src/router/index.ts`

```typescript
// 某露营地 — 路由配置
import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import NProgress from 'nprogress'
import 'nprogress/nprogress.css'
import { getToken } from '@/utils/request'
import { brandConfig } from '@/config/brand'
import { useUserStore } from '@/stores/user'

NProgress.configure({ showSpinner: false })

// ==================== 公共路由 ====================
const publicRoutes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/login/index.vue'),
    meta: { title: '登录', public: true },
  },
]

// ==================== 管理后台路由 ====================
const adminRoutes: RouteRecordRaw[] = [
  {
    path: '/',
    component: () => import('@/layout/index.vue'),
    redirect: '/dashboard',
    children: [
      // Dashboard
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/dashboard/index.vue'),
        meta: { title: 'Dashboard', icon: 'DataAnalysis' },
      },
      // 营地日历
      {
        path: 'calendar',
        name: 'Calendar',
        component: () => import('@/views/calendar/index.vue'),
        meta: { title: '营地日历', icon: 'Calendar' },
      },
      // 营位管理
      {
        path: 'campsites',
        name: 'Campsites',
        component: () => import('@/views/campsites/index.vue'),
        meta: { title: '营位管理', icon: 'Place' },
      },
      {
        path: 'campsites/create',
        name: 'CampsiteCreate',
        component: () => import('@/views/campsites/edit.vue'),
        meta: { title: '新增营位', hidden: true, activeMenu: '/campsites' },
      },
      {
        path: 'campsites/:id/edit',
        name: 'CampsiteEdit',
        component: () => import('@/views/campsites/edit.vue'),
        meta: { title: '编辑营位', hidden: true, activeMenu: '/campsites' },
      },
      // 商品管理
      {
        path: 'products',
        name: 'Products',
        component: () => import('@/views/products/index.vue'),
        meta: { title: '商品管理', icon: 'Goods' },
      },
      {
        path: 'products/create',
        name: 'ProductCreate',
        component: () => import('@/views/products/edit.vue'),
        meta: { title: '新增商品', hidden: true, activeMenu: '/products' },
      },
      {
        path: 'products/:id/edit',
        name: 'ProductEdit',
        component: () => import('@/views/products/edit.vue'),
        meta: { title: '编辑商品', hidden: true, activeMenu: '/products' },
      },
      // 订单管理
      {
        path: 'orders',
        name: 'Orders',
        component: () => import('@/views/orders/index.vue'),
        meta: { title: '订单管理', icon: 'List' },
      },
      {
        path: 'orders/:id',
        name: 'OrderDetail',
        component: () => import('@/views/orders/detail.vue'),
        meta: { title: '订单详情', hidden: true, activeMenu: '/orders' },
      },
      // 会员管理
      {
        path: 'members',
        name: 'Members',
        component: () => import('@/views/members/index.vue'),
        meta: { title: '会员管理', icon: 'User' },
      },
      {
        path: 'members/:id',
        name: 'MemberDetail',
        component: () => import('@/views/members/detail.vue'),
        meta: { title: '会员详情', hidden: true, activeMenu: '/members' },
      },
      // 财务管理（需要管理员权限）
      {
        path: 'finance',
        name: 'Finance',
        component: () => import('@/views/finance/index.vue'),
        meta: { title: '财务管理', icon: 'Money', roles: ['admin', 'super_admin'] },
      },
      // 系统设置
      {
        path: 'staff',
        name: 'Staff',
        component: () => import('@/views/system/staff.vue'),
        meta: { title: '员工管理', icon: 'UserFilled', roles: ['admin', 'super_admin'] },
      },
      {
        path: 'settings',
        name: 'Settings',
        component: () => import('@/views/system/settings.vue'),
        meta: { title: '系统设置', icon: 'Setting', roles: ['admin', 'super_admin'] },
      },
      // ... 更多路由
    ],
  },
]

// ==================== 创建路由器 ====================
const router = createRouter({
  history: createWebHistory(),
  routes: [...publicRoutes, ...adminRoutes],
})

// ==================== 路由守卫 ====================
router.beforeEach(async (to, _from, next) => {
  // 进度条
  NProgress.start()

  // 设置页面标题
  document.title = `${to.meta.title || '管理后台'} - ${brandConfig.name}`

  const token = getToken()

  // 公共页面逻辑
  if (to.meta.public) {
    if (token && to.path === '/login') {
      next('/dashboard')
    } else {
      next()
    }
  }
  // 受保护页面逻辑
  else {
    if (!token) {
      // 重定向到登录，记录目标路由用于登录后跳转
      next(`/login?redirect=${to.path}`)
    } else {
      const userStore = useUserStore()

      // 页面刷新后，store 为空时需要验证 token
      if (!userStore.isVerified) {
        const isValid = await userStore.verifyAndRefreshUser()
        if (!isValid) {
          next(`/login?redirect=${to.path}`)
          return
        }
      }

      // 角色权限检查
      const requiredRoles = to.meta.roles as string[] | undefined
      if (requiredRoles) {
        if (userStore.hasRole(requiredRoles)) {
          next()
        } else {
          next('/dashboard')  // 无权限则跳转到 dashboard
        }
      } else {
        next()
      }
    }
  }
})

router.afterEach(() => {
  NProgress.done()
})

export default router

// ==================== 类型扩展 ====================
declare module 'vue-router' {
  interface RouteMeta {
    title?: string
    icon?: string
    hidden?: boolean
    public?: boolean
    roles?: string[]
    activeMenu?: string
  }
}
```

**关键特性:**
- ✅ 动态导入组件实现代码分割
- ✅ `beforeEach` 守卫处理认证、权限、验证
- ✅ 基于 `roles` 元数据的权限检查
- ✅ 页面刷新后的 token 有效性验证
- ✅ NProgress 进度条在导航时显示
- ✅ 使用 `meta` 扩展自定义字段（`icon`, `hidden`, `roles` 等）
- ✅ 嵌套路由用于 create/edit 子页面

---

## HTTP 请求与认证

### 文件: `src/utils/request.ts`

```typescript
// 某露营地 — HTTP 请求封装
import axios, { type AxiosRequestConfig, type AxiosResponse, type InternalAxiosRequestConfig } from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'
import router from '@/router'

const BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1'

// ==================== Axios 实例 ====================
const service = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// ==================== Token 管理 ====================
const getToken = () => localStorage.getItem('access_token')
const getRefreshToken = () => localStorage.getItem('refresh_token')
const setToken = (access: string, refresh: string) => {
  localStorage.setItem('access_token', access)
  localStorage.setItem('refresh_token', refresh)
}
const clearToken = () => {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
  localStorage.removeItem('user_info')
}

// ==================== Token 刷新控制 ====================
let isRefreshing = false
let refreshSubscribers: Array<(token: string) => void> = []

function subscribeTokenRefresh(cb: (token: string) => void) {
  refreshSubscribers.push(cb)
}

function onTokenRefreshed(newToken: string) {
  refreshSubscribers.forEach(cb => cb(newToken))
  refreshSubscribers = []
}

// ==================== 请求拦截器 ====================
service.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // 添加 Authorization 头
    const token = getToken()
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }

    // 添加 CSRF Token
    const csrfToken = localStorage.getItem('csrf_token')
    if (csrfToken && config.method !== 'get') {
      config.headers['X-Request-Token'] = csrfToken
    }

    return config
  },
  (error) => Promise.reject(error)
)

// ==================== 响应拦截器 ====================
service.interceptors.response.use(
  (response: AxiosResponse) => {
    const { data } = response

    // 文件下载等二进制响应不做处理
    if (response.config.responseType === 'blob') {
      return response
    }

    // 业务 code 检查
    if (data.code !== undefined && data.code !== 0 && data.code !== 200) {
      ElMessage.error(data.message || '操作失败')
      return Promise.reject(new Error(data.message || '操作失败'))
    }

    return data
  },
  async (error) => {
    const { response, config } = error

    if (!response) {
      ElMessage.error('网络异常，请检查网络连接')
      return Promise.reject(error)
    }

    // ==================== 401: Token 过期处理 ====================
    if (response.status === 401 && !config._isRetry) {
      if (!isRefreshing) {
        isRefreshing = true
        try {
          const refreshToken = getRefreshToken()
          if (!refreshToken) throw new Error('no refresh token')

          // 调用刷新 token 接口
          const { data } = await axios.post(`${BASE_URL}/auth/refresh`, {
            refresh_token: refreshToken,
          })

          const newToken = data.data?.access_token || data.access_token
          const newRefresh = data.data?.refresh_token || data.refresh_token
          setToken(newToken, newRefresh)
          onTokenRefreshed(newToken)
          isRefreshing = false

          // 重试原请求
          config._isRetry = true
          config.headers.Authorization = `Bearer ${newToken}`
          return service(config)
        } catch {
          // Token 刷新失败，清除登录状态
          isRefreshing = false
          refreshSubscribers = []
          clearToken()
          ElMessageBox.confirm('登录已过期，请重新登录', '提示', {
            confirmButtonText: '重新登录',
            cancelButtonText: '取消',
            type: 'warning',
          }).then(() => {
            router.push('/login')
          })
          return Promise.reject(error)
        }
      } else {
        // 等待其他请求完成 token 刷新
        return new Promise((resolve) => {
          subscribeTokenRefresh((newToken: string) => {
            config._isRetry = true
            config.headers.Authorization = `Bearer ${newToken}`
            resolve(service(config))
          })
        })
      }
    }

    // ==================== 403: 权限不足 ====================
    if (response.status === 403) {
      ElMessage.error('权限不足，无法执行此操作')
      return Promise.reject(error)
    }

    // ==================== 其他错误 ====================
    const message = response.data?.message || response.data?.detail || `请求失败 (${response.status})`
    ElMessage.error(message)
    return Promise.reject(error)
  }
)

// ==================== HTTP 方法 ====================
export function get<T = any>(url: string, params?: any, config?: AxiosRequestConfig): Promise<T> {
  return service.get(url, { params, ...config }) as Promise<T>
}

export function post<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
  return service.post(url, data, config) as Promise<T>
}

export function put<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
  return service.put(url, data, config) as Promise<T>
}

export function patch<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
  return service.patch(url, data, config) as Promise<T>
}

export function del<T = any>(url: string, config?: AxiosRequestConfig): Promise<T> {
  return service.delete(url, config) as Promise<T>
}

// ==================== 导出 ====================
export { setToken, clearToken, getToken }
export default service
```

**关键特性:**
- ✅ Bearer Token 认证
- ✅ Token 自动刷新机制（避免多个同时发起刷新请求）
- ✅ 业务 code 检查（code !== 0 视为错误）
- ✅ 统一错误提示（`ElMessage`）
- ✅ CSRF Token 支持
- ✅ 泛型 `<T>` 支持强类型返回值
- ✅ 二进制响应处理（文件下载）

---

## 类型系统

### 文件: `src/types/index.ts`（部分）

```typescript
// 某露营地 — Web 管理后台 TypeScript 类型定义

// ==================== 通用类型 ====================

export interface ApiResponse<T = any> {
  code: number
  message: string
  data: T
}

export interface PaginatedResponse<T> {
  list: T[]
  pagination: {
    page: number
    page_size: number
    total: number
    total_pages: number
  }
}

export interface PaginationParams {
  page?: number
  page_size?: number
}

export interface SortParams {
  sort_by?: string
  sort_order?: 'asc' | 'desc'
}

// ==================== 认证类型 ====================

export interface AdminLoginRequest {
  username: string
  password: string
}

export interface LoginResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
  user: AdminUserInfo
}

export interface AdminUserInfo {
  id: number
  username: string
  real_name: string
  phone: string
  role: RoleInfo
  status: 'active' | 'disabled'
  last_login_at: string | null
  avatar?: string
}

export interface RoleInfo {
  id: number
  role_name: string
  role_code: 'super_admin' | 'admin' | 'staff'
  description: string
}

export interface TokenPayload {
  sub: string
  role: string
  exp: number
  jti: string
}

// ==================== 商品类型 ====================

export type ProductCategory = 'campsite' | 'activity' | 'meal' | 'equipment_rental' | 'addon' | 'shop_item' | 'peripheral'

export type ProductStatus = 'active' | 'inactive' | 'draft'

export interface Product {
  id: number
  name: string
  category: ProductCategory
  sub_category: string
  status: ProductStatus
  cover_image: string
  images: string[]
  description: string
  base_price: number
  market_price: number | null
  unit: string
  sort_order: number
  tags: string[]
  require_identity: boolean
  require_disclaimer: boolean
  created_at: string
  updated_at: string
  extension?: ProductExtension
  skus?: ProductSKU[]
  pricing_rules?: PricingRule[]
  discount_rules?: DiscountRule[]
}

export interface ProductCreateRequest {
  name: string
  category: ProductCategory
  base_price: number
  market_price?: number
  unit: string
  cover_image: string
  images: string[]
  description: string
  sort_order: number
  tags: string[]
  require_identity: boolean
  require_disclaimer: boolean
  status: ProductStatus
}

export interface ProductSearchParams extends PaginationParams {
  keyword?: string
  category?: ProductCategory
  status?: ProductStatus
}
```

**关键特性:**
- ✅ 使用 `interface` 定义数据结构
- ✅ 使用 `type` 定义字面量联合类型（`'active' | 'inactive' | 'draft'`）
- ✅ 继承 Mixin 类型（`ProductSearchParams extends PaginationParams`）
- ✅ 可选字段用 `?`（`market_price?: number`）
- ✅ 嵌套对象类型

---

## 样式与主题系统

### 全局设计系统: `src/styles/index.scss`

```scss
// 一月一露 — 「深邃极光」管理后台设计系统
// Northern Lights Dashboard · 暗色科技 + 自然光韵

// ==================== 变量系统 ====================
:root {
  // 主色系 — 深邃森林
  --color-primary: #3d8b5e;
  --color-primary-light: #52b67a;
  --color-primary-lighter: #7ed4a0;
  --color-primary-lightest: #d0f0dc;
  --color-primary-glow: rgba(61, 139, 94, 0.25);

  // 点缀色 — 极光
  --color-accent: #c8a872;
  --color-accent-glow: rgba(200, 168, 114, 0.2);

  // 背景色 — 深邃层次
  --color-bg: #f0ede8;
  --color-bg-warm: #faf6f0;
  --color-bg-card: #ffffff;
  --color-sidebar: #141e1a;
  --color-sidebar-hover: rgba(61, 139, 94, 0.08);
  --color-sidebar-active: rgba(61, 139, 94, 0.15);

  // 文字色
  --color-text: #2a2520;
  --color-text-secondary: #6b6560;
  --color-text-placeholder: #a09890;
  --color-text-sidebar: #8a9a90;
  --color-text-sidebar-active: #7ed4a0;

  // 边框与分割线
  --color-border: #e8e2dc;
  --color-border-light: #f0ece6;

  // 阴影 — 柔和自然
  --shadow-base: 0 4px 20px rgba(42, 37, 32, 0.06);
  --shadow-light: 0 2px 12px rgba(42, 37, 32, 0.04);
  --shadow-elevated: 0 8px 40px rgba(42, 37, 32, 0.08);
  --shadow-glow: 0 4px 24px var(--color-primary-glow);

  // 圆角
  --radius-base: 12px;
  --radius-small: 6px;
  --radius-large: 16px;
  --radius-xl: 20px;

  // 过渡
  --ease-out-expo: cubic-bezier(0.19, 1, 0.22, 1);
  --transition-base: all 0.35s var(--ease-out-expo);
}

// ==================== Reset ====================
*,
*::before,
*::after {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

html, body, #app {
  width: 100%;
  height: 100%;
  font-family: 'PingFang SC', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif;
  font-size: 14px;
  color: var(--color-text);
  background-color: var(--color-bg);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  letter-spacing: 0.3px;
}

// ==================== 工具类 ====================
.page-container {
  padding: 24px;
  min-height: calc(100vh - 60px);
}

.card-box {
  background: var(--color-bg-card);
  border-radius: var(--radius-base);
  box-shadow: var(--shadow-light);
  padding: 24px;
  margin-bottom: 20px;
  border: 1px solid var(--color-border-light);
  transition: var(--transition-base);

  &:hover {
    box-shadow: var(--shadow-base);
  }
}

.flex-between {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.text-primary { color: var(--color-primary); }
.text-success { color: #52b67a; }
.text-warning { color: #d4a535; }
.text-danger { color: #c45c4a; }
.text-accent { color: var(--color-accent); }

.mt-8 { margin-top: 8px; }
.mt-16 { margin-top: 16px; }
.mb-8 { margin-bottom: 8px; }
.mb-16 { margin-bottom: 16px; }

// ==================== 表格操作按钮 — 全局统一 ====================
.action-buttons {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.action-btn {
  width: 32px !important;
  height: 32px !important;
  border: 1.5px solid transparent !important;
  transition: all 0.3s var(--ease-out-expo) !important;
  font-size: 15px !important;

  .el-icon { font-size: 15px; }

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
  }

  &:active {
    transform: translateY(0) scale(0.95);
  }

  // 编辑 — 主色调
  &--edit {
    color: var(--color-primary) !important;
    background: rgba(61, 139, 94, 0.08) !important;
    border-color: rgba(61, 139, 94, 0.2) !important;
    &:hover {
      color: #fff !important;
      background: var(--color-primary) !important;
      border-color: var(--color-primary) !important;
      box-shadow: 0 4px 14px var(--color-primary-glow);
    }
  }

  // 删除 — 柔和红
  &--delete {
    color: #e06060 !important;
    background: rgba(224, 96, 96, 0.06) !important;
    border-color: rgba(224, 96, 96, 0.15) !important;
    &:hover {
      color: #fff !important;
      background: #e06060 !important;
      border-color: #e06060 !important;
      box-shadow: 0 4px 14px rgba(224, 96, 96, 0.3);
    }
  }

  // 上架 — 绿色
  &--online {
    color: #52b67a !important;
    background: rgba(82, 182, 122, 0.08) !important;
    border-color: rgba(82, 182, 122, 0.2) !important;
    &:hover {
      color: #fff !important;
      background: #52b67a !important;
      border-color: #52b67a !important;
      box-shadow: 0 4px 14px rgba(82, 182, 122, 0.3);
    }
  }

  // 下架 — 琥珀色
  &--offline {
    color: var(--color-accent) !important;
    background: var(--color-accent-glow) !important;
    border-color: rgba(200, 168, 114, 0.25) !important;
    &:hover {
      color: #fff !important;
      background: var(--color-accent) !important;
      border-color: var(--color-accent) !important;
      box-shadow: 0 4px 14px var(--color-accent-glow);
    }
  }

  // ... 更多按钮变体
}
```

### Element Plus 主题定制: `src/styles/element.scss`

```scss
// 一月一露 — Element Plus 深邃极光主题定制
// 户外露营自然风 × 科技管理感

@forward 'element-plus/theme-chalk/src/common/var.scss' with (
  $colors: (
    'primary': (
      'base': #3d8b5e,
    ),
    'success': (
      'base': #52b67a,
    ),
    'warning': (
      'base': #d4a535,
    ),
    'danger': (
      'base': #c45c4a,
    ),
    'info': (
      'base': #6b8a9a,
    ),
  ),
);
```

**关键特性:**
- ✅ CSS 变量系统（`--color-primary`, `--color-bg` 等）便于主题切换
- ✅ 工具类（`.flex-between`, `.card-box`, `.action-btn--*` 等）
- ✅ 阴影和渐变与品牌设计一致
- ✅ 统一的操作按钮变体（11+ 种）
- ✅ 使用 Element Plus `@forward` 定制主题颜色

---

## 工具函数

### 文件: `src/utils/index.ts`

```typescript
// 某露营地 — 通用工具函数
import dayjs from 'dayjs'

// ==================== 价格格式化 ====================
// 注: 后端存储为分（cent），前端展示为元（yuan）
export function formatPrice(price: number): string {
  return (price / 100).toFixed(2)
}

// ==================== 日期格式化 ====================
export function formatDate(date: string | Date, format = 'YYYY-MM-DD'): string {
  return dayjs(date).format(format)
}

export function formatDateTime(date: string | Date): string {
  return dayjs(date).format('YYYY-MM-DD HH:mm:ss')
}

// ==================== 相对时间 ====================
export function formatRelativeTime(date: string | Date): string {
  const d = dayjs(date)
  const now = dayjs()
  const diff = now.diff(d, 'minute')
  if (diff < 1) return '刚刚'
  if (diff < 60) return `${diff}分钟前`
  if (diff < 1440) return `${Math.floor(diff / 60)}小时前`
  if (diff < 43200) return `${Math.floor(diff / 1440)}天前`
  return d.format('YYYY-MM-DD')
}

// ==================== 品类映射 ====================
export const categoryMap: Record<string, string> = {
  activity: '活动',
  meal: '餐饮',
  equipment_rental: '装备租赁',
  addon: '加人票',
  shop_item: '小商店',
  peripheral: '周边商品',
}

export function getCategoryName(category: string): string {
  return categoryMap[category] || category
}

// ==================== 订单状态映射 ====================
export const orderStatusMap: Record<string, { label: string; type: string }> = {
  pending_payment: { label: '待支付', type: 'warning' },
  paid: { label: '已支付', type: 'primary' },
  confirmed: { label: '已确认', type: 'success' },
  in_use: { label: '使用中', type: 'primary' },
  completed: { label: '已完成', type: 'info' },
  cancelled: { label: '已取消', type: 'info' },
  refunding: { label: '退款中', type: 'warning' },
  refunded: { label: '已退款', type: 'danger' },
}

// ==================== 防抖 ====================
export function debounce<T extends (...args: any[]) => any>(fn: T, delay = 300): T {
  let timer: ReturnType<typeof setTimeout>
  return ((...args: any[]) => {
    clearTimeout(timer)
    timer = setTimeout(() => fn(...args), delay)
  }) as T
}

// ==================== 文件大小格式化 ====================
export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / 1024 / 1024).toFixed(1) + ' MB'
}

// ==================== 文件下载 ====================
export function downloadFile(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}
```

**关键特性:**
- ✅ 强类型泛型函数（`debounce<T>`）
- ✅ 映射对象用于枚举值查询（`categoryMap`, `orderStatusMap`）
- ✅ 日期/时间格式化
- ✅ 防抖和文件操作工具

---

## 开发规范

### 命名规范

| 对象 | 规范 | 示例 |
|------|------|------|
| **文件** | kebab-case | `product.ts`, `user-list.vue` |
| **目录** | kebab-case | `api/`, `views/products/` |
| **变量/函数** | camelCase | `getProducts`, `userInfo` |
| **常量** | UPPER_SNAKE_CASE | `API_TIMEOUT`, `ROLE_ADMIN` |
| **类型/接口** | PascalCase | `Product`, `UserInfo` |
| **CSS 类名** | kebab-case | `.action-btn--edit`, `.product-cover` |

### 文件组织

```
feature/
├── index.vue          # 列表页面
├── edit.vue           # 编辑页面
├── detail.vue         # 详情页面（可选）
└── components/        # 特定功能组件（可选）
    ├── editor.vue
    └── filter.vue
```

### 组件模板结构

```vue
<template>
  <!-- 容器 -->
  <div class="page-container">
    <!-- 卡片 -->
    <div class="card-box">
      <!-- 搜索/筛选区 -->
      <div class="flex-between mb-16">
        <!-- 左: 搜索 -->
        <div class="search-bar">
          <!-- 搜索框 -->
        </div>
        <!-- 右: 新增按钮 -->
        <el-button type="primary">新增</el-button>
      </div>

      <!-- 表格区 -->
      <el-table :data="tableData" v-loading="loading" stripe>
        <!-- 列定义 -->
      </el-table>

      <!-- 分页区 -->
      <div class="pagination-wrapper">
        <el-pagination />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
// 导入
// 状态
// 方法
// 生命周期
</script>

<style lang="scss" scoped>
// 样式
</style>
```

### 状态管理最佳实践

- ✅ **响应式数据**: 使用 `ref()` 用于原始类型，`reactive()` 用于对象
- ✅ **派生状态**: 使用 `computed()` 而不是在模板中计算
- ✅ **异步操作**: 返回 Promise，让调用方处理错误
- ✅ **Pinia Store**: 用于全局状态（认证、应用状态）

### API 调用模式

```typescript
// 组件中
async function fetchData() {
  loading.value = true
  try {
    const res = await getProducts(params)
    tableData.value = res.data.list
    total.value = res.data.pagination.total
  } catch {
    // 错误已由 request 拦截器显示
  } finally {
    loading.value = false
  }
}
```

### 表单处理模式

```typescript
// 验证 + 提交
async function handleSubmit() {
  if (!formRef.value) return

  // 1. 验证
  await formRef.value.validate()

  // 2. 设置加载状态
  saving.value = true
  try {
    // 3. 调用 API
    if (isEdit.value) {
      await updateProduct(id, form)
      ElMessage.success('更新成功')
    } else {
      await createProduct(form)
      ElMessage.success('创建成功')
    }
    // 4. 跳转
    router.push('/products')
  } catch {
    // 错误已显示
  } finally {
    saving.value = false
  }
}
```

---

## Vite 构建配置

### 文件: `vite.config.ts`

```typescript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'
import path from 'path'

export default defineConfig({
  plugins: [
    // Vue 支持
    vue(),

    // 自动导入 Vue 3 API（ref, computed 等）+ Element Plus
    AutoImport({
      resolvers: [ElementPlusResolver()],
      imports: ['vue', 'vue-router', 'pinia'],
      dts: 'src/auto-imports.d.ts',
    }),

    // 自动导入 Element Plus 组件
    Components({
      resolvers: [ElementPlusResolver({ importStyle: 'sass' })],
      dts: 'src/components.d.ts',
    }),
  ],

  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
  },

  css: {
    preprocessorOptions: {
      scss: {
        // 全局导入 Element Plus 主题
        additionalData: `@use "@/styles/element.scss" as *;`,
      },
    },
  },

  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
```

**关键特性:**
- ✅ 路径别名 `@` 映射到 `src/`
- ✅ 自动导入 Vue 3 Composition API（无需手动 `import`）
- ✅ 自动导入 Element Plus 组件（无需手动 `import`）
- ✅ API 代理（开发时 `/api` 转发到 `http://localhost:8000`）
- ✅ Element Plus SCSS 主题全局注入

---

## 总结

### 核心设计原则

1. **类型安全**: 完整的 TypeScript 类型定义，避免运行时错误
2. **关注点分离**: API 层、业务层、UI 层分开
3. **可复用性**: 通用工具函数、样式类、API 模块
4. **一致性**: 统一的命名规范、组件结构、错误处理
5. **响应式**: 利用 Vue 3 的响应式系统管理状态
6. **易维护**: 小文件、清晰的目录结构、模块化

### 快速开始新页面

1. **创建 API 模块** (`src/api/xxx.ts`)
   - 导出具名函数，每个对应一个端点
   - 使用泛型定义响应类型

2. **创建类型定义** (`src/types/index.ts`)
   - 定义 `SearchParams`, `Item`, `CreateRequest` 等类型

3. **创建列表页面** (`src/views/xxx/index.vue`)
   - 响应式状态管理
   - 表格渲染
   - 分页、搜索、排序

4. **创建编辑页面** (`src/views/xxx/edit.vue`)
   - 表单验证
   - 创建/更新逻辑

5. **添加路由** (`src/router/index.ts`)
   - 列表、创建、编辑路由
   - 权限检查（`roles` 元数据）

---

**文档版本**: 1.0
**最后更新**: 2026-04-01
**作者**: Claude Opus

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
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" @click="router.push(`/products/${row.id}/edit`)">编辑</el-button>
            <el-button text :type="row.status === 'active' ? 'warning' : 'success'" @click="handleToggleStatus(row)">
              {{ row.status === 'active' ? '下架' : '上架' }}
            </el-button>
            <el-popconfirm title="确定删除该商品？" @confirm="handleDelete(row.id)">
              <template #reference>
                <el-button text type="danger">删除</el-button>
              </template>
            </el-popconfirm>
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
import { Search, Plus, Picture } from '@element-plus/icons-vue'
import { getProducts, updateProductStatus, deleteProduct } from '@/api/product'
import { formatPrice, formatDateTime, getCategoryName, categoryMap } from '@/utils'
import type { Product, ProductSearchParams } from '@/types'

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

async function fetchData() {
  loading.value = true
  try {
    const res = await getProducts(searchParams)
    tableData.value = res.data.list
    total.value = res.data.pagination.total
  } catch {
    // 模拟数据
    tableData.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  searchParams.page = 1
  fetchData()
}

async function handleToggleStatus(row: Product) {
  const newStatus = row.status === 'active' ? 'inactive' : 'active'
  try {
    await updateProductStatus(row.id, newStatus)
    ElMessage.success(`已${newStatus === 'active' ? '上架' : '下架'}`)
    row.status = newStatus
  } catch {}
}

async function handleDelete(id: number) {
  try {
    await deleteProduct(id)
    ElMessage.success('删除成功')
    fetchData()
  } catch {}
}

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
  gap: 12px;

  .product-cover {
    width: 48px;
    height: 48px;
    border-radius: 6px;
    flex-shrink: 0;
  }

  .image-placeholder {
    width: 48px;
    height: 48px;
    background: #f5f7fa;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #c0c4cc;
    border-radius: 6px;
  }

  .product-name {
    font-size: 14px;
    font-weight: 500;
    margin-bottom: 4px;
    color: #303133;
  }
}

.price {
  font-weight: 600;
  color: #F44336;
}

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>

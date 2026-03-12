<template>
  <div class="page-container">
    <el-row :gutter="16">
      <!-- 分类管理 -->
      <el-col :span="8">
        <div class="card-box">
          <div class="flex-between mb-16">
            <h3>FAQ分类</h3>
            <el-button type="primary" size="small" @click="showCategoryDialog = true"><el-icon><Plus /></el-icon>新建</el-button>
          </div>
          <el-table :data="categories" v-loading="loading" border size="small">
            <el-table-column prop="name" label="分类名称" />
            <el-table-column prop="item_count" label="条目数" width="70" align="center" />
            <el-table-column prop="sort_order" label="排序" width="60" align="center" />
            <el-table-column label="操作" width="120">
              <template #default="{ row }">
                <el-button text type="primary" size="small" @click="editCategory(row)">编辑</el-button>
                <el-popconfirm title="确定删除？" @confirm="handleDeleteCategory(row.id)">
                  <template #reference><el-button text type="danger" size="small">删除</el-button></template>
                </el-popconfirm>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-col>

      <!-- FAQ条目 -->
      <el-col :span="16">
        <div class="card-box">
          <div class="flex-between mb-16">
            <h3>FAQ条目</h3>
            <el-button type="primary" size="small" @click="showItemDialog = true"><el-icon><Plus /></el-icon>新建</el-button>
          </div>
          <el-table :data="items" v-loading="loadingItems" stripe>
            <el-table-column prop="question" label="问题" min-width="200" show-overflow-tooltip />
            <el-table-column prop="category_name" label="分类" width="100" />
            <el-table-column prop="view_count" label="查看次数" width="90" align="center" />
            <el-table-column label="状态" width="80" align="center">
              <template #default="{ row }">
                <el-tag size="small" :type="row.status === 'active' ? 'success' : 'info'">{{ row.status === 'active' ? '启用' : '停用' }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="120">
              <template #default="{ row }">
                <el-button text type="primary" size="small" @click="editItem(row)">编辑</el-button>
                <el-popconfirm title="确定删除？" @confirm="handleDeleteItem(row.id)">
                  <template #reference><el-button text type="danger" size="small">删除</el-button></template>
                </el-popconfirm>
              </template>
            </el-table-column>
          </el-table>
          <div class="pagination-wrapper">
            <el-pagination v-model:current-page="itemParams.page" :total="itemTotal" :page-size="20" layout="total, prev, pager, next" @current-change="fetchItems" />
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- 分类弹窗 -->
    <el-dialog v-model="showCategoryDialog" title="FAQ分类" width="400px">
      <el-form :model="categoryForm" label-width="80px">
        <el-form-item label="名称" required><el-input v-model="categoryForm.name" /></el-form-item>
        <el-form-item label="排序"><el-input-number v-model="categoryForm.sort_order" :min="0" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCategoryDialog = false">取消</el-button>
        <el-button type="primary" @click="handleSaveCategory">保存</el-button>
      </template>
    </el-dialog>

    <!-- 条目弹窗 -->
    <el-dialog v-model="showItemDialog" title="FAQ条目" width="600px">
      <el-form :model="itemForm" label-width="80px">
        <el-form-item label="分类" required>
          <el-select v-model="itemForm.category_id" style="width: 100%;">
            <el-option v-for="c in categories" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="问题" required><el-input v-model="itemForm.question" /></el-form-item>
        <el-form-item label="回答" required><el-input v-model="itemForm.answer" type="textarea" :rows="5" /></el-form-item>
        <el-form-item label="关键词"><el-select v-model="itemForm.keywords" multiple filterable allow-create style="width: 100%;" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showItemDialog = false">取消</el-button>
        <el-button type="primary" @click="handleSaveItem">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { getFaqCategories, createFaqCategory, updateFaqCategory, deleteFaqCategory, getFaqItems, createFaqItem, updateFaqItem, deleteFaqItem } from '@/api/system'
import type { FaqCategory, FaqItem } from '@/types'

const loading = ref(false)
const loadingItems = ref(false)
const categories = ref<FaqCategory[]>([])
const items = ref<FaqItem[]>([])
const itemTotal = ref(0)
const showCategoryDialog = ref(false)
const showItemDialog = ref(false)
const editingCategory = ref<FaqCategory | null>(null)
const editingItem = ref<FaqItem | null>(null)
const categoryForm = reactive({ name: '', sort_order: 0 })
const itemForm = reactive({ category_id: 0, question: '', answer: '', keywords: [] as string[] })
const itemParams = reactive({ page: 1, page_size: 20 })

async function fetchCategories() {
  loading.value = true
  try { const res = await getFaqCategories(); categories.value = res.data } catch {} finally { loading.value = false }
}

async function fetchItems() {
  loadingItems.value = true
  try { const res = await getFaqItems(itemParams); items.value = res.data.items; itemTotal.value = res.data.total } catch {} finally { loadingItems.value = false }
}

function editCategory(row: FaqCategory) { editingCategory.value = row; Object.assign(categoryForm, row); showCategoryDialog.value = true }
function editItem(row: FaqItem) { editingItem.value = row; Object.assign(itemForm, row); showItemDialog.value = true }

async function handleSaveCategory() {
  try {
    if (editingCategory.value) await updateFaqCategory(editingCategory.value.id, categoryForm)
    else await createFaqCategory(categoryForm)
    ElMessage.success('保存成功'); showCategoryDialog.value = false; fetchCategories()
  } catch {}
}

async function handleSaveItem() {
  try {
    if (editingItem.value) await updateFaqItem(editingItem.value.id, itemForm)
    else await createFaqItem(itemForm)
    ElMessage.success('保存成功'); showItemDialog.value = false; fetchItems()
  } catch {}
}

async function handleDeleteCategory(id: number) { try { await deleteFaqCategory(id); ElMessage.success('已删除'); fetchCategories() } catch {} }
async function handleDeleteItem(id: number) { try { await deleteFaqItem(id); ElMessage.success('已删除'); fetchItems() } catch {} }

onMounted(() => { fetchCategories(); fetchItems() })
</script>

<style lang="scss" scoped>
.pagination-wrapper { display: flex; justify-content: flex-end; margin-top: 16px; }
</style>

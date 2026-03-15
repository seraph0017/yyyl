<template>
  <div class="page-container">
    <div class="card-box">
      <div class="flex-between mb-16">
        <h3>游戏管理</h3>
        <el-button type="primary" @click="handleCreate">
          <el-icon><Plus /></el-icon>新建游戏
        </el-button>
      </div>

      <!-- 搜索 -->
      <el-form :inline="true" class="mb-16">
        <el-form-item>
          <el-input v-model="searchParams.keyword" placeholder="搜索游戏名称" clearable style="width: 200px" @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item>
          <el-select v-model="searchParams.status" placeholder="状态" clearable @change="handleSearch">
            <el-option label="启用" value="active" />
            <el-option label="停用" value="inactive" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch"><el-icon><Search /></el-icon>搜索</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>

      <!-- 数据表格 -->
      <el-table :data="tableData" v-loading="loading" stripe>
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="name" label="游戏名称" min-width="150" show-overflow-tooltip />
        <el-table-column label="封面" width="100">
          <template #default="{ row }">
            <el-image
              v-if="row.cover_image"
              :src="row.cover_image"
              :preview-src-list="[row.cover_image]"
              fit="cover"
              style="width: 60px; height: 40px; border-radius: 4px"
            />
            <span v-else class="text-secondary">无</span>
          </template>
        </el-table-column>
        <el-table-column label="游戏URL" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            <el-link type="primary" :href="row.game_url" target="_blank">{{ row.game_url }}</el-link>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : 'info'" size="small">
              {{ row.status === 'active' ? '启用' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="积分奖励" width="100" align="center">
          <template #default="{ row }">
            <span class="points">+{{ row.points_reward }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="sort_order" label="排序" width="70" align="center" />
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" @click="handleEdit(row)">编辑</el-button>
            <el-button text type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

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

    <!-- 新建/编辑弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      :title="editingId ? '编辑游戏' : '新建游戏'"
      width="560px"
      destroy-on-close
    >
      <el-form ref="formRef" :model="formData" :rules="formRules" label-width="90px">
        <el-form-item label="游戏名称" prop="name">
          <el-input v-model="formData.name" placeholder="请输入游戏名称" />
        </el-form-item>
        <el-form-item label="游戏URL" prop="game_url">
          <el-input v-model="formData.game_url" placeholder="请输入游戏链接（H5 URL）" />
        </el-form-item>
        <el-form-item label="封面图片">
          <el-input v-model="formData.cover_image" placeholder="封面图片URL（选填）" />
        </el-form-item>
        <el-form-item label="游戏描述">
          <el-input v-model="formData.description" type="textarea" :rows="3" placeholder="游戏描述（选填）" />
        </el-form-item>
        <el-form-item label="积分奖励">
          <el-input-number v-model="formData.points_reward" :min="0" :max="9999" />
        </el-form-item>
        <el-form-item label="排序" prop="sort_order">
          <el-input-number v-model="formData.sort_order" :min="0" :max="999" />
        </el-form-item>
        <el-form-item label="状态">
          <el-radio-group v-model="formData.status">
            <el-radio value="active">启用</el-radio>
            <el-radio value="inactive">停用</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { Search, Plus } from '@element-plus/icons-vue'
import { getGames, createGame, updateGame, deleteGame } from '@/api/game'
import type { MiniGame, MiniGameCreate } from '@/types'

const loading = ref(false)
const submitting = ref(false)
const tableData = ref<MiniGame[]>([])
const total = ref(0)
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const formRef = ref<FormInstance>()

const searchParams = reactive({
  page: 1,
  page_size: 20,
  keyword: '',
  status: undefined as string | undefined,
})

const formData = reactive<MiniGameCreate & { status: string; points_reward: number }>({
  name: '',
  game_url: '',
  cover_image: '',
  description: '',
  sort_order: 0,
  status: 'active',
  points_reward: 0,
})

const formRules: FormRules = {
  name: [{ required: true, message: '请输入游戏名称', trigger: 'blur' }],
  game_url: [
    { required: true, message: '请输入游戏URL', trigger: 'blur' },
    { type: 'url', message: '请输入有效的URL', trigger: 'blur' },
  ],
  sort_order: [{ required: true, message: '请输入排序值', trigger: 'blur' }],
}

async function fetchData() {
  loading.value = true
  try {
    const res = await getGames(searchParams)
    tableData.value = res.data.list
    total.value = res.data.pagination.total
  } catch {
    tableData.value = []
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  searchParams.page = 1
  fetchData()
}

function handleReset() {
  searchParams.keyword = ''
  searchParams.status = undefined
  handleSearch()
}

function resetForm() {
  formData.name = ''
  formData.game_url = ''
  formData.cover_image = ''
  formData.description = ''
  formData.sort_order = 0
  formData.status = 'active'
  formData.points_reward = 0
  editingId.value = null
}

function handleCreate() {
  resetForm()
  dialogVisible.value = true
}

function handleEdit(row: MiniGame) {
  editingId.value = row.id
  formData.name = row.name
  formData.game_url = row.game_url
  formData.cover_image = row.cover_image
  formData.description = row.description
  formData.sort_order = row.sort_order
  formData.status = row.status
  formData.points_reward = row.points_reward
  dialogVisible.value = true
}

async function handleDelete(row: MiniGame) {
  await ElMessageBox.confirm(`确认删除游戏「${row.name}」？`, '删除确认', { type: 'warning' })
  await deleteGame(row.id)
  ElMessage.success('删除成功')
  fetchData()
}

async function handleSubmit() {
  await formRef.value?.validate()
  submitting.value = true
  try {
    if (editingId.value) {
      await updateGame(editingId.value, { ...formData })
      ElMessage.success('更新成功')
    } else {
      await createGame({ ...formData })
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    fetchData()
  } finally {
    submitting.value = false
  }
}

onMounted(fetchData)
</script>

<style lang="scss" scoped>
.text-secondary { font-size: 12px; color: #909399; }
.points { font-weight: 600; color: #E6A23C; }
.pagination-wrapper { display: flex; justify-content: flex-end; margin-top: 16px; }
</style>

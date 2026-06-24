<template>
  <div class="page-container">
    <div class="card-box">
      <div class="flex-between mb-16">
        <h3>管理员/员工管理</h3>
        <el-button v-if="userStore.isSuperAdmin" type="primary" @click="openCreateDialog">
          <el-icon><Plus /></el-icon>添加账号
        </el-button>
      </div>

      <el-table :data="staffList" v-loading="loading" stripe>
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="real_name" label="姓名" width="120" />
        <el-table-column prop="phone" label="手机号" width="140" />
        <el-table-column prop="username" label="用户名" width="120" />
        <el-table-column label="角色" width="120" align="center">
          <template #default="{ row }">
            <el-tag :type="row.role?.role_code === 'super_admin' ? 'danger' : row.role?.role_code === 'admin' ? 'warning' : 'info'" size="small">
              {{ row.role?.role_name || '--' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : 'danger'" size="small">{{ row.status === 'active' ? '正常' : '禁用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="最后登录" width="170">
          <template #default="{ row }">{{ row.last_login_at ? formatDateTime(row.last_login_at) : '从未登录' }}</template>
        </el-table-column>
        <el-table-column v-if="userStore.isSuperAdmin" label="操作" width="120" fixed="right" align="center">
          <template #default="{ row }">
            <div class="action-buttons">
              <el-tooltip content="编辑" placement="top" :show-after="400">
                <el-button class="action-btn action-btn--edit" circle size="small" @click="editStaff(row)">
                  <el-icon><Edit /></el-icon>
                </el-button>
              </el-tooltip>
              <el-popconfirm title="确定移除该账号？" @confirm="handleDelete(row.id)" width="200">
                <template #reference>
                  <el-tooltip content="移除" placement="top" :show-after="400">
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
    </div>

    <el-alert
      v-if="!userStore.isSuperAdmin"
      class="readonly-alert"
      type="info"
      :closable="false"
      title="当前账号可查看成员列表，新增、编辑和移除账号需由超级管理员操作。"
    />

    <el-dialog v-model="showDialog" :title="editingStaff ? '编辑账号' : '添加账号'" width="520px" @closed="resetForm">
      <el-form ref="staffFormRef" :model="staffForm" :rules="staffRules" label-width="90px">
        <el-form-item v-if="!editingStaff" label="用户名" prop="username">
          <el-input v-model.trim="staffForm.username" maxlength="50" placeholder="用于登录后台，如 ops_admin" />
        </el-form-item>
        <el-form-item label="姓名" prop="real_name">
          <el-input v-model.trim="staffForm.real_name" maxlength="50" placeholder="成员真实姓名" />
        </el-form-item>
        <el-form-item label="手机号" prop="phone">
          <el-input v-model.trim="staffForm.phone" maxlength="20" placeholder="可选，用于联系和识别" />
        </el-form-item>
        <el-form-item label="角色" prop="role_id">
          <el-select v-model="staffForm.role_id" style="width: 100%;">
            <el-option v-for="r in assignableRoles" :key="r.id" :label="r.role_name" :value="r.id" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="!editingStaff" label="初始密码" prop="password">
          <el-input v-model="staffForm.password" type="password" show-password placeholder="留空则使用默认密码 123456" />
        </el-form-item>
        <el-form-item v-if="editingStaff" label="状态" prop="status">
          <el-switch
            v-model="staffForm.status"
            active-value="active"
            inactive-value="disabled"
            active-text="正常"
            inactive-text="禁用"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, reactive, onMounted } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { Plus, Edit, Delete } from '@element-plus/icons-vue'
import { getStaffList, createStaff, updateStaff, deleteStaff, getRoles } from '@/api/system'
import { formatDateTime } from '@/utils'
import { useUserStore } from '@/stores/user'
import type { RoleInfo, StaffMember } from '@/types'

const loading = ref(false)
const saving = ref(false)
const staffList = ref<StaffMember[]>([])
const roles = ref<RoleInfo[]>([])
const showDialog = ref(false)
const editingStaff = ref<StaffMember | null>(null)
const staffFormRef = ref<FormInstance>()
const userStore = useUserStore()
const staffForm = reactive({
  username: '',
  real_name: '',
  phone: '',
  role_id: 0,
  password: '',
  status: 'active' as 'active' | 'disabled',
})
const staffRules: FormRules = {
  username: [
    { required: true, message: '请输入后台登录用户名', trigger: 'blur' },
    { pattern: /^[A-Za-z0-9_]{3,50}$/, message: '用户名需为 3-50 位英文、数字或下划线', trigger: 'blur' },
  ],
  real_name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  role_id: [{ required: true, message: '请选择角色', trigger: 'change' }],
  password: [{ min: 6, max: 128, message: '密码至少 6 位', trigger: 'blur' }],
}

const assignableRoles = computed(() => roles.value.filter(role => role.role_code !== 'super_admin'))

async function fetchData() {
  loading.value = true
  try { const res = await getStaffList(); staffList.value = res.data.list } catch {} finally { loading.value = false }
}

async function fetchRoles() {
  try {
    const res = await getRoles()
    roles.value = res.data
  } catch {}
}

function resetForm() {
  editingStaff.value = null
  Object.assign(staffForm, {
    username: '',
    real_name: '',
    phone: '',
    role_id: assignableRoles.value[0]?.id || 0,
    password: '',
    status: 'active',
  })
  staffFormRef.value?.clearValidate()
}

function openCreateDialog() {
  resetForm()
  showDialog.value = true
}

function editStaff(row: StaffMember) {
  editingStaff.value = row
  Object.assign(staffForm, {
    username: row.username,
    real_name: row.real_name,
    phone: row.phone,
    role_id: row.role?.id || 0,
    password: '',
    status: row.status,
  })
  showDialog.value = true
}

async function handleSave() {
  const valid = await staffFormRef.value?.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    if (editingStaff.value) {
      await updateStaff(editingStaff.value.id, {
        real_name: staffForm.real_name,
        phone: staffForm.phone || undefined,
        role_id: staffForm.role_id,
        status: staffForm.status,
      })
    } else {
      await createStaff({
        username: staffForm.username,
        real_name: staffForm.real_name,
        phone: staffForm.phone || undefined,
        role_id: staffForm.role_id,
        password: staffForm.password || undefined,
      })
    }
    ElMessage.success('保存成功'); showDialog.value = false; fetchData()
  } catch {
  } finally {
    saving.value = false
  }
}

async function handleDelete(id: number) {
  try { await deleteStaff(id); ElMessage.success('已移除'); fetchData() } catch {}
}

onMounted(async () => {
  await fetchRoles()
  resetForm()
  fetchData()
})
</script>

<style lang="scss" scoped>
.readonly-alert {
  margin-top: 16px;
}
</style>

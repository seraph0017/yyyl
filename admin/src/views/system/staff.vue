<template>
  <div class="page-container">
    <div class="card-box">
      <div class="flex-between mb-16">
        <h3>员工管理</h3>
        <el-button type="primary" @click="showDialog = true"><el-icon><Plus /></el-icon>添加员工</el-button>
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
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" size="small" @click="editStaff(row)">编辑</el-button>
            <el-popconfirm title="确定移除该员工？" @confirm="handleDelete(row.id)">
              <template #reference><el-button text type="danger" size="small">移除</el-button></template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="showDialog" :title="editingStaff ? '编辑员工' : '添加员工'" width="500px">
      <el-form :model="staffForm" label-width="80px">
        <el-form-item label="姓名" required><el-input v-model="staffForm.real_name" /></el-form-item>
        <el-form-item label="手机号" required><el-input v-model="staffForm.phone" /></el-form-item>
        <el-form-item label="角色" required>
          <el-select v-model="staffForm.role_id" style="width: 100%;">
            <el-option v-for="r in roles" :key="r.id" :label="r.role_name" :value="r.id" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="!editingStaff" label="初始密码"><el-input v-model="staffForm.password" type="password" placeholder="留空则使用默认密码" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button type="primary" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { getStaffList, createStaff, updateStaff, deleteStaff, getRoles } from '@/api/system'
import { formatDateTime } from '@/utils'
import type { StaffMember } from '@/types'

const loading = ref(false)
const staffList = ref<StaffMember[]>([])
const roles = ref<any[]>([])
const showDialog = ref(false)
const editingStaff = ref<StaffMember | null>(null)
const staffForm = reactive({ real_name: '', phone: '', role_id: 0, password: '' })

async function fetchData() {
  loading.value = true
  try { const res = await getStaffList(); staffList.value = res.data.items } catch {} finally { loading.value = false }
}

async function fetchRoles() {
  try { const res = await getRoles(); roles.value = res.data } catch {}
}

function editStaff(row: StaffMember) {
  editingStaff.value = row
  Object.assign(staffForm, { real_name: row.real_name, phone: row.phone, role_id: row.role?.id || 0 })
  showDialog.value = true
}

async function handleSave() {
  try {
    if (editingStaff.value) await updateStaff(editingStaff.value.id, staffForm)
    else await createStaff(staffForm)
    ElMessage.success('保存成功'); showDialog.value = false; fetchData()
  } catch {}
}

async function handleDelete(id: number) {
  try { await deleteStaff(id); ElMessage.success('已移除'); fetchData() } catch {}
}

onMounted(() => { fetchData(); fetchRoles() })
</script>

<template>
  <el-dialog
    :model-value="visible"
    title="管理员登录"
    width="400px"
    :close-on-click-modal="false"
    aria-label="管理员登录"
    @update:model-value="emit('update:visible', $event)"
    @close="emit('update:visible', false)"
    @opened="onDialogOpened"
  >
    <el-form
      ref="formRef"
      :model="loginForm"
      :rules="loginRules"
      label-width="0"
      size="large"
      @submit.prevent="handleLogin"
    >
      <el-form-item prop="username">
        <el-input
          ref="usernameInputRef"
          v-model="loginForm.username"
          placeholder="用户名"
          prefix-icon="User"
          clearable
        />
      </el-form-item>
      <el-form-item prop="password">
        <el-input
          v-model="loginForm.password"
          type="password"
          placeholder="密码"
          prefix-icon="Lock"
          show-password
          @keyup.enter="handleLogin"
        />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="loading" style="width: 100%" @click="handleLogin">
          登录
        </el-button>
      </el-form-item>
    </el-form>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, nextTick } from 'vue'
import type { FormInstance, FormRules } from 'element-plus'
import { useUserStore } from '@/stores/user'

const props = defineProps<{
  visible: boolean
}>()

const emit = defineEmits<{
  (e: 'update:visible', value: boolean): void
  (e: 'success'): void
}>()

const userStore = useUserStore()
const formRef = ref<FormInstance>()
const usernameInputRef = ref()
const loading = ref(false)

const loginForm = reactive({
  username: '',
  password: '',
})

const loginRules: FormRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

// 弹窗打开后自动聚焦用户名输入框
function onDialogOpened() {
  nextTick(() => {
    usernameInputRef.value?.focus()
  })
}

async function handleLogin() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    await userStore.login(loginForm.username, loginForm.password)
    ElMessage.success('登录成功')
    emit('update:visible', false)
    emit('success')
  } catch {
    // 错误由拦截器处理
  } finally {
    loading.value = false
  }
}
</script>

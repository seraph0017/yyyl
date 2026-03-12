<template>
  <div class="login-container">
    <div class="login-bg">
      <div class="bg-overlay" />
    </div>
    <div class="login-card">
      <div class="login-header">
        <img src="@/assets/logo.svg" alt="logo" class="login-logo" />
        <h1 class="login-title">{{ brand.name }}</h1>
        <p class="login-subtitle">露营地管理后台</p>
      </div>

      <el-form
        ref="formRef"
        :model="loginForm"
        :rules="rules"
        class="login-form"
        @keyup.enter="handleLogin"
      >
        <el-form-item prop="username">
          <el-input
            v-model="loginForm.username"
            placeholder="请输入用户名或手机号"
            size="large"
            :prefix-icon="User"
          />
        </el-form-item>
        <el-form-item prop="password">
          <el-input
            v-model="loginForm.password"
            type="password"
            placeholder="请输入密码"
            size="large"
            :prefix-icon="Lock"
            show-password
          />
        </el-form-item>
        <el-form-item>
          <el-button
            type="primary"
            size="large"
            class="login-btn"
            :loading="loading"
            @click="handleLogin"
          >
            登录
          </el-button>
        </el-form-item>
      </el-form>

      <el-divider>其他登录方式</el-divider>
      <div class="other-login">
        <el-button text @click="handleWechatLogin">
          <el-icon :size="24"><ChatDotRound /></el-icon>
          <span>微信扫码登录</span>
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { User, Lock, ChatDotRound } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'
import { brandConfig as brand } from '@/config/brand'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const formRef = ref<FormInstance>()
const loading = ref(false)

const loginForm = reactive({
  username: '',
  password: '',
})

const rules: FormRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码不少于6位', trigger: 'blur' },
  ],
}

async function handleLogin() {
  if (!formRef.value) return
  await formRef.value.validate()

  loading.value = true
  try {
    await userStore.login(loginForm.username, loginForm.password)
    ElMessage.success('登录成功')
    const redirect = (route.query.redirect as string) || '/dashboard'
    router.push(redirect)
  } catch (error: any) {
    ElMessage.error(error?.message || '登录失败，请检查用户名和密码')
  } finally {
    loading.value = false
  }
}

function handleWechatLogin() {
  ElMessage.info('微信扫码登录功能开发中')
}
</script>

<style lang="scss" scoped>
.login-container {
  width: 100%;
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
}

.login-bg {
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, #1a3a1a 0%, #2E7D32 40%, #4CAF50 70%, #81C784 100%);
  z-index: 0;

  .bg-overlay {
    position: absolute;
    inset: 0;
    background:
      radial-gradient(circle at 20% 80%, rgba(255,248,240,0.08) 0%, transparent 50%),
      radial-gradient(circle at 80% 20%, rgba(255,255,255,0.05) 0%, transparent 50%);
  }
}

.login-card {
  position: relative;
  z-index: 1;
  width: 420px;
  padding: 48px 40px;
  background: rgba(255, 255, 255, 0.95);
  border-radius: 16px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
  backdrop-filter: blur(20px);
}

.login-header {
  text-align: center;
  margin-bottom: 36px;

  .login-logo {
    width: 64px;
    height: 64px;
    margin-bottom: 12px;
  }

  .login-title {
    font-size: 28px;
    font-weight: 700;
    color: #2E7D32;
    margin: 0 0 4px;
    letter-spacing: 2px;
  }

  .login-subtitle {
    font-size: 14px;
    color: #909399;
    margin: 0;
  }
}

.login-form {
  .login-btn {
    width: 100%;
    height: 44px;
    font-size: 16px;
    border-radius: 8px;
    background: linear-gradient(135deg, #2E7D32, #4CAF50);
    border: none;

    &:hover {
      background: linear-gradient(135deg, #388E3C, #66BB6A);
    }
  }
}

.other-login {
  text-align: center;

  .el-button {
    display: flex;
    align-items: center;
    gap: 6px;
    margin: 0 auto;
    color: #4CAF50;
  }
}
</style>

<template>
  <div class="login-page">
    <!-- 多层背景 -->
    <div class="login-bg">
      <div class="login-bg__base" />
      <div class="login-bg__aurora" />
      <div class="login-bg__grain" />
    </div>

    <!-- 登录卡片 -->
    <div class="login-card">
      <div class="login-card__glow" />
      <div class="login-card__inner">
        <div class="login-header">
          <img src="@/assets/logo.svg" alt="logo" class="login-header__logo" />
          <h1 class="login-header__title">{{ brand.name }}</h1>
          <p class="login-header__subtitle">营地管理后台</p>
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
              class="login-input"
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
              class="login-input"
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
              登 录
            </el-button>
          </el-form-item>
        </el-form>

        <el-divider class="login-divider">其他方式</el-divider>
        <div class="other-login">
          <el-button text class="wechat-btn" @click="handleWechatLogin">
            <el-icon :size="20"><ChatDotRound /></el-icon>
            <span>微信扫码登录</span>
          </el-button>
        </div>
      </div>
    </div>

    <!-- 底部版权 -->
    <div class="login-footer">
      <span>© 2026 {{ brand.name }} · 露营地管理系统</span>
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
.login-page {
  width: 100%;
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
}

// ==================== 多层背景 ====================
.login-bg {
  position: absolute;
  inset: 0;
  z-index: 0;

  &__base {
    position: absolute;
    inset: 0;
    background: linear-gradient(
      165deg,
      #0c1a14 0%,
      #141e1a 20%,
      #1a2e24 45%,
      #2d4a3e 70%,
      #3d6b5a 100%
    );
  }

  &__aurora {
    position: absolute;
    inset: 0;
    background:
      radial-gradient(ellipse 80% 50% at 65% 20%, rgba(61, 139, 94, 0.15) 0%, transparent 60%),
      radial-gradient(ellipse 60% 40% at 30% 70%, rgba(200, 168, 114, 0.08) 0%, transparent 50%),
      radial-gradient(circle at 80% 80%, rgba(74, 139, 168, 0.06) 0%, transparent 40%);
    animation: aurora-shift 12s ease-in-out infinite alternate;
  }

  &__grain {
    position: absolute;
    inset: 0;
    opacity: 0.03;
    background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
  }
}

@keyframes aurora-shift {
  0% {
    transform: scale(1) translateX(0);
  }
  100% {
    transform: scale(1.05) translateX(20px);
  }
}

// ==================== 登录卡片 ====================
.login-card {
  position: relative;
  z-index: 1;
  width: 440px;

  &__glow {
    position: absolute;
    inset: -1px;
    border-radius: 22px;
    background: linear-gradient(
      135deg,
      rgba(61, 139, 94, 0.3) 0%,
      rgba(200, 168, 114, 0.2) 50%,
      rgba(61, 139, 94, 0.15) 100%
    );
    opacity: 0.6;
    filter: blur(1px);
  }

  &__inner {
    position: relative;
    padding: 48px 44px;
    background: rgba(255, 255, 255, 0.92);
    border-radius: 20px;
    backdrop-filter: blur(40px);
    box-shadow:
      0 24px 80px rgba(0, 0, 0, 0.2),
      0 8px 32px rgba(0, 0, 0, 0.1),
      inset 0 1px 0 rgba(255, 255, 255, 0.5);
  }
}

// ==================== 登录头部 ====================
.login-header {
  text-align: center;
  margin-bottom: 40px;

  &__logo {
    width: 60px;
    height: 60px;
    margin-bottom: 16px;
    filter: drop-shadow(0 4px 12px rgba(61, 139, 94, 0.2));
  }

  &__title {
    font-size: 28px;
    font-weight: 800;
    color: #2a2520;
    margin: 0 0 6px;
    letter-spacing: 4px;
  }

  &__subtitle {
    font-size: 13px;
    color: #a09890;
    margin: 0;
    letter-spacing: 2px;
    font-weight: 400;
  }
}

// ==================== 表单 ====================
.login-form {
  .login-input {
    :deep(.el-input__wrapper) {
      border-radius: 10px;
      box-shadow: 0 0 0 1px var(--color-border-light) inset;
      transition: all 0.3s ease;
      padding: 4px 12px;

      &:hover {
        box-shadow: 0 0 0 1px var(--color-border) inset;
      }

      &.is-focus {
        box-shadow: 0 0 0 1px var(--color-primary) inset, 0 0 0 3px var(--color-primary-glow);
      }
    }
  }

  .login-btn {
    width: 100%;
    height: 46px;
    font-size: 15px;
    font-weight: 600;
    letter-spacing: 6px;
    border-radius: 10px;
    background: linear-gradient(135deg, #2d4a3e, #3d8b5e);
    border: none;
    box-shadow: 0 6px 20px rgba(61, 139, 94, 0.3);
    transition: all 0.35s var(--ease-out-expo);

    &:hover {
      background: linear-gradient(135deg, #3d6b5a, #52b67a);
      box-shadow: 0 8px 28px rgba(61, 139, 94, 0.35);
      transform: translateY(-1px);
    }

    &:active {
      transform: translateY(0);
    }
  }
}

// ==================== 分割线 ====================
.login-divider {
  :deep(.el-divider__text) {
    font-size: 12px;
    color: var(--color-text-placeholder);
    letter-spacing: 1px;
    background: rgba(255, 255, 255, 0.92);
  }
}

// ==================== 其他登录 ====================
.other-login {
  text-align: center;

  .wechat-btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    color: var(--color-primary);
    font-size: 13px;
    letter-spacing: 0.5px;
    padding: 8px 20px;
    border-radius: 8px;
    transition: var(--transition-base);

    &:hover {
      background: var(--color-bg-warm);
    }
  }
}

// ==================== 底部版权 ====================
.login-footer {
  position: absolute;
  bottom: 24px;
  left: 0;
  right: 0;
  text-align: center;
  z-index: 1;

  span {
    font-size: 12px;
    color: rgba(200, 200, 200, 0.3);
    letter-spacing: 1px;
  }
}
</style>

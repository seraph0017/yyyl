<template>
  <div class="landing-page">
    <!-- 顶部导航栏 -->
    <header class="landing-header">
      <div class="header-brand">
        <img src="@/assets/logo.svg" :alt="brandConfig.name + ' logo'" class="brand-logo" />
        <span class="brand-name">{{ brandConfig.name }}</span>
      </div>
      <button class="login-btn" @click="loginVisible = true">管理员登录</button>
    </header>

    <!-- CMS 渲染区域 -->
    <main class="landing-content">
      <template v-if="pageConfig">
        <LandingRenderer :config="pageConfig" />
      </template>

      <!-- 默认内容（无CMS配置时显示） -->
      <template v-else-if="!loading">
        <section class="default-hero fade-in-up" ref="heroRef">
          <div class="hero-inner">
            <h1 class="hero-title">{{ brandConfig.name }}</h1>
            <p class="hero-subtitle">在自然中寻找生活的诗意</p>
            <p class="hero-desc">
              我们精心打造多个特色营地，为您提供远离城市喧嚣的户外露营体验。
              从西郊林场的静谧森林到大聋谷的壮美峡谷，每一处都是大自然的馈赠。
            </p>
          </div>
        </section>

        <section class="default-features fade-in-up">
          <div class="features-grid">
            <div class="feature-card">
              <div class="feature-icon">
                <el-icon :size="40" color="#2d4a3e"><HomeFilled /></el-icon>
              </div>
              <h3>精选营位</h3>
              <p>多种风格营位可选，满足不同露营需求</p>
            </div>
            <div class="feature-card">
              <div class="feature-icon">
                <el-icon :size="40" color="#2d4a3e"><Sunny /></el-icon>
              </div>
              <h3>自然环境</h3>
              <p>远离城市喧嚣，沉浸于山水之间</p>
            </div>
            <div class="feature-card">
              <div class="feature-icon">
                <el-icon :size="40" color="#2d4a3e"><SetUp /></el-icon>
              </div>
              <h3>完善设施</h3>
              <p>配套设施齐全，享受便捷野奢体验</p>
            </div>
            <div class="feature-card">
              <div class="feature-icon">
                <el-icon :size="40" color="#2d4a3e"><MagicStick /></el-icon>
              </div>
              <h3>星空露营</h3>
              <p>仰望漫天繁星，感受宇宙浩瀚</p>
            </div>
          </div>
        </section>
      </template>

      <!-- 加载状态 -->
      <div v-if="loading" class="loading-state">
        <el-icon class="is-loading" :size="32"><Loading /></el-icon>
      </div>
    </main>

    <!-- 底部版权栏 -->
    <footer class="landing-footer">
      <p>© {{ currentYear }} {{ brandConfig.name }} 版权所有</p>
    </footer>

    <!-- 登录弹窗 -->
    <LoginDialog v-model:visible="loginVisible" @success="onLoginSuccess" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Loading, Sunny, SetUp, HomeFilled, MagicStick } from '@element-plus/icons-vue'
import { brandConfig } from '@/config/brand'
import { getLandingPage } from '@/api/cms'
import type { CmsConfig } from '@/types/cms'
import LandingRenderer from '@/components/landing/LandingRenderer.vue'
import LoginDialog from '@/components/landing/LoginDialog.vue'

const route = useRoute()
const router = useRouter()

const loading = ref(true)
const loginVisible = ref(false)
const pageConfig = ref<CmsConfig | null>(null)
const currentYear = new Date().getFullYear()

// 加载宣传页配置
async function loadLandingPage() {
  loading.value = true
  try {
    const res = await getLandingPage()
    if (res.data) {
      pageConfig.value = res.data.config
    }
  } catch {
    // 配置未创建或API失败，展示内置默认内容
    pageConfig.value = null
  } finally {
    loading.value = false
  }
}

// 登录成功
function onLoginSuccess() {
  const redirect = route.query.redirect as string
  if (redirect) {
    router.push(decodeURIComponent(redirect))
  } else {
    router.push('/dashboard')
  }
}

// ---- 滚动动画 ----
let observer: IntersectionObserver | null = null

function setupScrollAnimation() {
  observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible')
        }
      })
    },
    { threshold: 0.1 }
  )

  document.querySelectorAll('.fade-in-up').forEach((el) => {
    observer!.observe(el)
  })
}

onMounted(async () => {
  await loadLandingPage()
  // 等待DOM更新后设置滚动动画
  setTimeout(setupScrollAnimation, 100)
})

onUnmounted(() => {
  if (observer) {
    observer.disconnect()
    observer = null
  }
})
</script>

<style lang="scss" scoped>
.landing-page {
  min-height: 100vh;
  background: var(--color-warm-sand, #faf6f0);
  display: flex;
  flex-direction: column;
}

// ==================== 顶部导航 ====================
.landing-header {
  position: fixed;
  top: 0;
  width: 100%;
  z-index: 100;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 40px;
  background: rgba(45, 74, 62, 0.85);
  backdrop-filter: blur(12px);
}

.header-brand {
  display: flex;
  align-items: center;
  gap: 10px;
}

.brand-logo {
  width: 28px;
  height: 28px;
  filter: brightness(2);
}

.brand-name {
  color: #c8a872;
  font-size: 20px;
  font-weight: 600;
  letter-spacing: 2px;
}

.login-btn {
  color: #fff;
  background: rgba(255, 255, 255, 0.15);
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 20px;
  padding: 8px 24px;
  cursor: pointer;
  transition: all 0.3s;
  font-size: 14px;

  &:hover {
    background: rgba(200, 168, 114, 0.3);
    border-color: #c8a872;
  }
}

// ==================== 内容区域 ====================
.landing-content {
  flex: 1;
  padding-top: 64px; // 顶部导航高度
}

.loading-state {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 400px;
  color: #2d4a3e;
}

// ==================== 默认内容 ====================
.default-hero {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 500px;
  background: linear-gradient(135deg, #2d4a3e 0%, #1a3028 100%);
  color: #fff;
  text-align: center;
  padding: 80px 40px;
}

.hero-inner {
  max-width: 700px;
}

.hero-title {
  font-size: 48px;
  font-weight: 700;
  letter-spacing: 6px;
  color: #c8a872;
  margin: 0 0 16px;
}

.hero-subtitle {
  font-size: 20px;
  color: rgba(255, 255, 255, 0.85);
  margin: 0 0 24px;
  letter-spacing: 3px;
}

.hero-desc {
  font-size: 15px;
  color: rgba(255, 255, 255, 0.75);
  line-height: 1.8;
  margin: 0;
}

.default-features {
  padding: 80px 40px;
  max-width: 1200px;
  margin: 0 auto;
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 24px;
}

.feature-card {
  text-align: center;
  padding: 40px 20px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
  transition: transform 0.3s ease, box-shadow 0.3s ease;

  &:hover {
    transform: translateY(-4px);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
  }

  .feature-icon {
    font-size: 40px;
    margin-bottom: 16px;
  }

  h3 {
    font-size: 18px;
    color: #2d4a3e;
    margin: 0 0 8px;
  }

  p {
    font-size: 14px;
    color: #909399;
    margin: 0;
    line-height: 1.5;
  }
}

// ==================== 底部版权栏 ====================
.landing-footer {
  padding: 24px 40px;
  text-align: center;
  background: rgba(45, 74, 62, 0.05);
  border-top: 1px solid rgba(45, 74, 62, 0.1);

  p {
    font-size: 13px;
    color: #909399;
    margin: 0;
  }
}

// ==================== 滚动动画 ====================
.fade-in-up {
  opacity: 0;
  transform: translateY(30px);
  transition: opacity 0.6s ease, transform 0.6s ease;

  &.is-visible {
    opacity: 1;
    transform: translateY(0);
  }
}

// ==================== 响应式 ====================
@media (max-width: 768px) {
  .landing-header {
    padding: 12px 20px;
  }

  .features-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .hero-title {
    font-size: 32px;
  }
}

// ==================== 减少动画 ====================
@media (prefers-reduced-motion: reduce) {
  .fade-in-up {
    opacity: 1;
    transform: none;
    transition: none;
  }

  .feature-card {
    transition: none;

    &:hover {
      transform: none;
    }
  }

  .login-btn {
    transition: none;
  }
}
</style>

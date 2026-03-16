<script setup lang="ts">
import { onLaunch, onError } from '@dcloudio/uni-app'
import { currentSite } from '@/config/sites'
import { useUserStore } from '@/store/user'
import { checkLoginStatus, wxLogin } from '@/utils/auth'

onLaunch(() => {
  console.log(`[${currentSite.name}] 小程序启动 site_id=${currentSite.id}`)

  const userStore = useUserStore()

  // 恢复登录状态
  if (checkLoginStatus()) {
    userStore.restoreFromStorage()
  } else {
    // 尝试静默登录
    wxLogin().catch(() => {
      console.log('静默登录失败，等待用户手动登录')
    })
  }
})

onError((err) => {
  console.error('App Error:', err)
})
</script>

<style lang="scss">
@import './uni.scss';

/* ========== 一月一露 · 野奢设计系统 ========== */
page {
  font-family: var(--font-family);
  font-size: var(--font-size-base);
  color: var(--color-text);
  background-color: var(--color-bg);
  line-height: 1.6;
  letter-spacing: 0.5rpx;
  -webkit-font-smoothing: antialiased;
}

/* --- 通用工具类 --- */
.text-ellipsis {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.text-ellipsis-2 {
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.flex-row {
  display: flex;
  flex-direction: row;
  align-items: center;
}

.flex-col {
  display: flex;
  flex-direction: column;
}

.flex-center {
  display: flex;
  justify-content: center;
  align-items: center;
}

.flex-between {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.flex-1 {
  flex: 1;
  min-width: 0;
}

.safe-bottom {
  padding-bottom: env(safe-area-inset-bottom);
}

.page-container {
  min-height: 100vh;
  background-color: var(--color-bg);
  box-sizing: border-box;
}

/* --- 卡片 — 柔和浮层 --- */
.card {
  background-color: var(--color-bg-card);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-md);
  overflow: hidden;
  border: 1rpx solid rgba(42, 37, 32, 0.04);
}

.divider {
  height: 1rpx;
  background: linear-gradient(90deg, transparent, rgba(42, 37, 32, 0.08), transparent);
  margin: var(--spacing-md) 0;
}

/* --- 按钮 — 野奢质感 --- */
.btn-primary {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 96rpx;
  background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-light) 100%);
  color: var(--color-text-white);
  font-size: var(--font-size-md);
  font-weight: 600;
  border-radius: var(--radius-xl);
  border: none;
  letter-spacing: 4rpx;
  box-shadow: 0 6rpx 20rpx rgba(45, 74, 62, 0.25);
  transition: var(--transition-base);

  &::after {
    border: none;
  }

  &:active {
    opacity: 0.9;
    transform: scale(0.97);
    box-shadow: 0 2rpx 8rpx rgba(45, 74, 62, 0.2);
  }
}

.btn-secondary {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 96rpx;
  background-color: transparent;
  color: var(--color-primary);
  font-size: var(--font-size-md);
  font-weight: 600;
  border: 2rpx solid var(--color-primary-lighter);
  border-radius: var(--radius-xl);
  letter-spacing: 2rpx;
  transition: var(--transition-base);

  &::after {
    border: none;
  }

  &:active {
    opacity: 0.85;
    background-color: var(--color-primary-bg);
  }
}

.btn-accent {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 96rpx;
  background: linear-gradient(135deg, var(--color-accent) 0%, #b8944e 100%);
  color: #fff;
  font-size: var(--font-size-md);
  font-weight: 600;
  border-radius: var(--radius-xl);
  border: none;
  letter-spacing: 4rpx;
  box-shadow: 0 6rpx 20rpx rgba(200, 168, 114, 0.3);
  transition: var(--transition-base);

  &::after {
    border: none;
  }

  &:active {
    opacity: 0.9;
    transform: scale(0.97);
  }
}

.btn-orange {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 96rpx;
  background: linear-gradient(135deg, #d4804a 0%, #c46e3a 100%);
  color: var(--color-text-white);
  font-size: var(--font-size-md);
  font-weight: 600;
  border-radius: var(--radius-xl);
  border: none;
  letter-spacing: 2rpx;
  box-shadow: 0 6rpx 20rpx rgba(212, 128, 74, 0.25);

  &::after {
    border: none;
  }

  &:active {
    opacity: 0.9;
    transform: scale(0.97);
  }
}

.btn-disabled {
  opacity: 0.4;
  pointer-events: none;
}

/* --- 标签 — 精致小标 --- */
.tag {
  display: inline-flex;
  align-items: center;
  padding: 6rpx 16rpx;
  font-size: var(--font-size-xs);
  border-radius: var(--radius-sm);
  white-space: nowrap;
  letter-spacing: 1rpx;

  &--primary {
    background-color: var(--color-primary-bg);
    color: var(--color-primary);
  }

  &--accent {
    background-color: var(--color-accent-bg);
    color: var(--color-accent);
  }

  &--orange {
    background-color: rgba(212, 128, 74, 0.1);
    color: var(--color-orange);
  }

  &--red {
    background-color: rgba(196, 92, 74, 0.08);
    color: var(--color-red);
  }
}

/* --- 价格 — 醒目金色 --- */
.price {
  color: var(--color-accent);
  font-weight: 700;

  &__symbol {
    font-size: var(--font-size-sm);
    font-weight: 500;
  }

  &__value {
    font-size: var(--font-size-xl);
    letter-spacing: 1rpx;
  }

  &--small .price__value {
    font-size: var(--font-size-base);
  }

  &--large .price__value {
    font-size: var(--font-size-title);
  }

  &__original {
    color: var(--color-text-placeholder);
    font-size: var(--font-size-sm);
    font-weight: 400;
    text-decoration: line-through;
    margin-left: 8rpx;
  }
}

.icon-placeholder {
  display: flex;
  justify-content: center;
  align-items: center;
  font-size: 48rpx;
  width: 88rpx;
  height: 88rpx;
  background: linear-gradient(135deg, var(--color-bg-light), var(--color-bg-warm));
  border-radius: var(--radius-lg);
}

/* --- 段落标题 — 优雅 --- */
.section-heading {
  font-size: var(--font-size-lg);
  font-weight: 700;
  color: var(--color-text);
  letter-spacing: 2rpx;
  position: relative;
  padding-left: 20rpx;

  &::before {
    content: '';
    position: absolute;
    left: 0;
    top: 50%;
    transform: translateY(-50%);
    width: 6rpx;
    height: 28rpx;
    background: linear-gradient(180deg, var(--color-accent), var(--color-primary-light));
    border-radius: 3rpx;
  }
}
</style>

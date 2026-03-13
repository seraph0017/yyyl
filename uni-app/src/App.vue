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

/* ========== 全局样式 ========== */
page {
  font-family: var(--font-family);
  font-size: var(--font-size-base);
  color: var(--color-text);
  background-color: var(--color-bg);
  line-height: 1.5;
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

.card {
  background-color: var(--color-bg-card);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  overflow: hidden;
}

.divider {
  height: 1rpx;
  background-color: #eaeaea;
  margin: var(--spacing-md) 0;
}

/* 按钮 */
.btn-primary {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 88rpx;
  background: linear-gradient(135deg, var(--color-primary-light), var(--color-primary));
  color: var(--color-text-white);
  font-size: var(--font-size-lg);
  font-weight: 600;
  border-radius: var(--radius-xl);
  border: none;
  letter-spacing: 2rpx;

  &::after {
    border: none;
  }

  &:active {
    opacity: 0.85;
    transform: scale(0.98);
  }
}

.btn-secondary {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 88rpx;
  background-color: var(--color-bg-white);
  color: var(--color-primary);
  font-size: var(--font-size-lg);
  font-weight: 600;
  border: 2rpx solid var(--color-primary);
  border-radius: var(--radius-xl);

  &::after {
    border: none;
  }

  &:active {
    opacity: 0.85;
  }
}

.btn-orange {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 88rpx;
  background: linear-gradient(135deg, #ff8a50, var(--color-orange));
  color: var(--color-text-white);
  font-size: var(--font-size-lg);
  font-weight: 600;
  border-radius: var(--radius-xl);
  border: none;

  &::after {
    border: none;
  }

  &:active {
    opacity: 0.85;
  }
}

.btn-disabled {
  opacity: 0.5;
  pointer-events: none;
}

/* 标签 */
.tag {
  display: inline-flex;
  align-items: center;
  padding: 4rpx 12rpx;
  font-size: var(--font-size-xs);
  border-radius: var(--radius-sm);
  white-space: nowrap;

  &--primary {
    background-color: var(--color-primary-bg);
    color: var(--color-primary);
  }

  &--orange {
    background-color: rgba(255, 107, 53, 0.1);
    color: var(--color-orange);
  }

  &--red {
    background-color: rgba(229, 57, 53, 0.1);
    color: var(--color-red);
  }
}

/* 价格 */
.price {
  color: var(--color-orange);
  font-weight: 700;

  &__symbol {
    font-size: var(--font-size-sm);
  }

  &__value {
    font-size: var(--font-size-xl);
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
  width: 80rpx;
  height: 80rpx;
  background-color: var(--color-bg-light);
  border-radius: var(--radius-md);
}
</style>

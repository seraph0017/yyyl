<template>
  <view class="qr-landing">
    <view class="qr-landing__panel">
      <view class="qr-landing__mark">
        <text>{{ failed ? '!' : '...' }}</text>
      </view>
      <text class="qr-landing__title">{{ failed ? '二维码不可用' : '正在打开' }}</text>
      <text class="qr-landing__desc">{{ message }}</text>
      <view v-if="failed" class="qr-landing__actions">
        <view class="qr-landing__btn" @tap="goHome">
          <text>返回首页</text>
        </view>
        <view class="qr-landing__btn qr-landing__btn--ghost" @tap="retry">
          <text>重试</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { resolveQrcode } from '@/api/qrcode'
import { savePendingCategoryKey, saveQrcodeAttribution } from '@/utils/attribution'

const scene = ref('')
const message = ref('请稍候')
const failed = ref(false)

onLoad((options) => {
  scene.value = decodeURIComponent(String(options?.scene || ''))
  if (!scene.value) {
    failed.value = true
    message.value = '缺少二维码参数'
    return
  }
  resolveAndRedirect()
})

async function resolveAndRedirect() {
  failed.value = false
  message.value = '正在解析二维码'
  try {
    const data = await resolveQrcode(scene.value)
    saveQrcodeAttribution(data)
    message.value = '正在跳转'
    redirectByPath(data.path, data.target_type, data.target_key)
  } catch {
    failed.value = true
    message.value = '二维码已失效或网络异常'
  }
}

function redirectByPath(path: string, targetType: string, targetKey: string) {
  if (targetType === 'category') {
    savePendingCategoryKey(targetKey)
    uni.switchTab({ url: '/pages/category/index' })
    return
  }

  if (path.startsWith('/pages/index/index')) {
    uni.switchTab({ url: '/pages/index/index' })
    return
  }

  uni.redirectTo({
    url: path,
    fail: () => {
      uni.navigateTo({
        url: path,
        fail: () => {
          uni.switchTab({ url: '/pages/index/index' })
        },
      })
    },
  })
}

function retry() {
  resolveAndRedirect()
}

function goHome() {
  uni.switchTab({ url: '/pages/index/index' })
}
</script>

<style lang="scss" scoped>
.qr-landing {
  min-height: 100vh;
  background: var(--color-bg);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 48rpx;

  &__panel {
    width: 100%;
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
  }

  &__mark {
    width: 88rpx;
    height: 88rpx;
    border-radius: 50%;
    background: var(--color-primary-bg);
    color: var(--color-primary);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 32rpx;
    font-weight: 700;
    margin-bottom: 28rpx;
  }

  &__title {
    font-size: 34rpx;
    font-weight: 700;
    color: var(--color-text);
    margin-bottom: 12rpx;
  }

  &__desc {
    font-size: 26rpx;
    color: var(--color-text-secondary);
  }

  &__actions {
    display: flex;
    gap: 16rpx;
    margin-top: 36rpx;
  }

  &__btn {
    min-width: 180rpx;
    height: 72rpx;
    padding: 0 28rpx;
    border-radius: var(--radius-round);
    background: var(--color-primary);
    color: var(--color-text-white);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 26rpx;
    font-weight: 600;

    &--ghost {
      background: var(--color-bg-light);
      color: var(--color-primary);
      border: 1rpx solid rgba(45, 74, 62, 0.18);
    }
  }
}
</style>

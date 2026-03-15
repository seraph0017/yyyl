<template>
  <view class="page-webview">
    <web-view :src="gameUrl" v-if="gameUrl" @message="onMessage" />
    <view class="webview-empty" v-else>
      <text class="webview-empty__icon">🎮</text>
      <text class="webview-empty__text">游戏加载失败</text>
      <view class="webview-empty__btn" @tap="goBack">
        <text>返回</text>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'

const gameUrl = ref('')

onLoad((query) => {
  if (query?.url) {
    gameUrl.value = decodeURIComponent(query.url)
  }
  if (query?.title) {
    uni.setNavigationBarTitle({ title: decodeURIComponent(query.title) })
  }
})

function onMessage(e: { detail: { data: unknown[] } }) {
  // 处理 H5 游戏回传的消息
  const messages = e.detail?.data || []
  const lastMsg = messages[messages.length - 1] as Record<string, unknown> | undefined
  if (lastMsg?.action === 'close') {
    goBack()
  }
  if (lastMsg?.action === 'reward') {
    uni.showToast({
      title: `恭喜获得 ${lastMsg.points || 0} 积分！`,
      icon: 'success',
    })
  }
}

function goBack() {
  uni.navigateBack()
}
</script>

<style lang="scss" scoped>
.page-webview {
  width: 100%;
  height: 100vh;
}

.webview-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100vh;
  gap: 24rpx;

  &__icon {
    font-size: 120rpx;
  }

  &__text {
    font-size: var(--font-size-lg);
    color: var(--color-text-secondary);
  }

  &__btn {
    padding: 16rpx 48rpx;
    background-color: var(--color-primary);
    border-radius: var(--radius-round);
    margin-top: 20rpx;

    text {
      font-size: var(--font-size-base);
      color: #fff;
      font-weight: 600;
    }

    &:active { opacity: 0.85; }
  }
}
</style>

<template>
  <view class="page-games">
    <!-- 头部 -->
    <view class="games-header">
      <text class="games-header__icon">🎮</text>
      <view class="games-header__info">
        <text class="games-header__title">趣味游戏</text>
        <text class="games-header__desc">玩游戏赢积分，更多福利等你来</text>
      </view>
    </view>

    <!-- 游戏列表 -->
    <view class="games-list" v-if="!loading && games.length > 0">
      <view
        class="game-card"
        v-for="item in games"
        :key="item.id"
        @tap="onGameTap(item)"
      >
        <!-- 封面图 -->
        <view class="game-card__cover-wrap">
          <image
            class="game-card__cover"
            :src="resolveImageUrl(item.cover_image)"
            mode="aspectFill"
            v-if="item.cover_image"
            lazy-load
          />
          <view class="game-card__cover game-card__cover--placeholder" v-else>
            <text>🕹️</text>
          </view>
          <!-- 积分奖励 -->
          <view class="game-card__reward" v-if="item.points_reward > 0">
            <text>🏆 +{{ item.points_reward }}积分</text>
          </view>
        </view>

        <!-- 游戏信息 -->
        <view class="game-card__info">
          <text class="game-card__name">{{ item.name }}</text>
          <text class="game-card__desc text-ellipsis-2">{{ item.description }}</text>
          <view class="game-card__action">
            <view class="game-card__btn">
              <text>开始游戏</text>
            </view>
          </view>
        </view>
      </view>
    </view>

    <!-- 加载骨架 -->
    <view class="games-list" v-else-if="loading">
      <view class="game-card game-card--skeleton" v-for="i in 3" :key="i">
        <view class="skeleton-cover" />
        <view class="skeleton-info">
          <view class="skeleton-bar" style="width: 60%; height: 32rpx;" />
          <view class="skeleton-bar" style="width: 100%; height: 24rpx; margin-top: 12rpx;" />
          <view class="skeleton-bar" style="width: 30%; height: 56rpx; margin-top: 20rpx; border-radius: 28rpx;" />
        </view>
      </view>
    </view>

    <!-- 空状态 -->
    <empty-state
      v-else
      icon="🎮"
      title="暂无游戏"
      description="更多趣味游戏正在开发中"
    />

    <!-- webview 页面（通过跳转打开） -->
    <!-- 加载弹窗 -->
    <view class="game-loading-mask" v-if="gameLoading">
      <view class="game-loading">
        <view class="loading-spinner" />
        <text class="game-loading__text">正在启动游戏...</text>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { get, resolveImageUrl } from '@/utils/request'
import type { IMiniGame } from '@/types'
import EmptyState from '@/components/empty-state/index.vue'

const loading = ref(true)
const games = ref<IMiniGame[]>([])
const gameLoading = ref(false)

/** 加载游戏列表 */
async function loadGames() {
  loading.value = true
  try {
    const data = await get<IMiniGame[]>('/games', undefined, { needAuth: false })
    if (data && Array.isArray(data)) {
      games.value = data
    }
  } catch {
    games.value = []
  } finally {
    loading.value = false
  }
}

/** 点击游戏 */
async function onGameTap(game: IMiniGame) {
  gameLoading.value = true

  try {
    // 获取签名 token
    const tokenData = await get<{ token: string; expires_at: string }>(
      `/games/${game.id}/token`,
    )

    if (!tokenData || !tokenData.token) {
      uni.showToast({ title: '获取游戏凭证失败', icon: 'none' })
      return
    }

    // 拼接带 token 的游戏 URL
    const separator = game.game_url.includes('?') ? '&' : '?'
    const gameUrl = `${game.game_url}${separator}token=${encodeURIComponent(tokenData.token)}`

    // #ifdef MP-WEIXIN
    // 微信小程序：跳转到 webview 页面
    uni.navigateTo({
      url: `/pages-sub/product/game-webview/index?url=${encodeURIComponent(gameUrl)}&title=${encodeURIComponent(game.name)}`,
      fail() {
        // webview 页面不存在时，复制链接
        uni.setClipboardData({
          data: gameUrl,
          success() {
            uni.showToast({ title: '链接已复制，请在浏览器打开', icon: 'none' })
          },
        })
      },
    })
    // #endif

    // #ifdef H5
    window.location.href = gameUrl
    // #endif

    // #ifndef MP-WEIXIN || H5
    uni.setClipboardData({
      data: gameUrl,
      success() {
        uni.showToast({ title: '链接已复制，请在浏览器打开', icon: 'none' })
      },
    })
    // #endif
  } catch {
    uni.showToast({ title: '启动游戏失败，请重试', icon: 'none' })
  } finally {
    gameLoading.value = false
  }
}

onMounted(() => {
  loadGames()
})
</script>

<style lang="scss" scoped>
.page-games {
  min-height: 100vh;
  background-color: var(--color-bg);
  padding-bottom: env(safe-area-inset-bottom);
}

.games-header {
  display: flex;
  align-items: center;
  gap: 20rpx;
  padding: 32rpx;
  background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-light) 100%);

  &__icon {
    font-size: 72rpx;
  }

  &__info {
    display: flex;
    flex-direction: column;
  }

  &__title {
    font-size: var(--font-size-xl);
    font-weight: 700;
    color: #fff;
  }

  &__desc {
    font-size: var(--font-size-sm);
    color: rgba(255, 255, 255, 0.8);
    margin-top: 4rpx;
  }
}

.games-list {
  padding: 24rpx 32rpx;
}

.game-card {
  display: flex;
  background-color: var(--color-bg-card);
  border-radius: var(--radius-xl);
  overflow: hidden;
  box-shadow: var(--shadow-sm);
  margin-bottom: 24rpx;

  &:active {
    opacity: 0.85;
    transform: scale(0.99);
  }

  &--skeleton {
    &:active { opacity: 1; transform: none; }
  }

  &__cover-wrap {
    position: relative;
    width: 240rpx;
    flex-shrink: 0;
  }

  &__cover {
    width: 100%;
    height: 100%;
    min-height: 240rpx;

    &--placeholder {
      background-color: var(--color-bg-light);
      display: flex;
      justify-content: center;
      align-items: center;
      text { font-size: 64rpx; }
    }
  }

  &__reward {
    position: absolute;
    bottom: 12rpx;
    left: 12rpx;
    background-color: rgba(0, 0, 0, 0.6);
    padding: 6rpx 16rpx;
    border-radius: var(--radius-round);

    text {
      font-size: 20rpx;
      color: #ffc107;
      font-weight: 600;
    }
  }

  &__info {
    flex: 1;
    min-width: 0;
    padding: 24rpx;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
  }

  &__name {
    font-size: var(--font-size-lg);
    font-weight: 700;
    color: var(--color-text);
    display: block;
  }

  &__desc {
    font-size: var(--font-size-sm);
    color: var(--color-text-secondary);
    line-height: 1.5;
    margin-top: 8rpx;
    display: -webkit-box;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 2;
    overflow: hidden;
  }

  &__action {
    display: flex;
    justify-content: flex-start;
    margin-top: 16rpx;
  }

  &__btn {
    display: inline-flex;
    align-items: center;
    padding: 12rpx 32rpx;
    background-color: var(--color-primary);
    border-radius: var(--radius-round);

    text {
      font-size: var(--font-size-sm);
      color: #fff;
      font-weight: 600;
    }
  }
}

.skeleton-cover {
  width: 240rpx;
  height: 240rpx;
  flex-shrink: 0;
  background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}

.skeleton-info {
  flex: 1;
  padding: 24rpx;
}

.skeleton-bar {
  border-radius: var(--radius-sm);
  background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* 加载弹窗 */
.game-loading-mask {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  z-index: 100;
  display: flex;
  justify-content: center;
  align-items: center;
}

.game-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20rpx;
  background-color: var(--color-bg-white);
  padding: 48rpx 64rpx;
  border-radius: var(--radius-xl);

  &__text {
    font-size: var(--font-size-sm);
    color: var(--color-text-secondary);
  }
}

.loading-spinner {
  width: 56rpx;
  height: 56rpx;
  border: 4rpx solid var(--color-bg-grey);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>

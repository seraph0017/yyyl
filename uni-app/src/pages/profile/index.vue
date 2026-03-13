<template>
  <view class="page-profile">
    <view class="profile-item card" @tap="onChooseAvatar">
      <text class="profile-item__label">头像</text>
      <view class="profile-item__avatar">
        <text>🏕️</text>
      </view>
    </view>
    <view class="profile-item card">
      <text class="profile-item__label">昵称</text>
      <text class="profile-item__value">{{ userInfo?.nickname || '露营爱好者' }}</text>
    </view>
    <view class="profile-item card">
      <text class="profile-item__label">手机号</text>
      <text class="profile-item__value">{{ userInfo?.phone || '未绑定' }}</text>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { put } from '@/utils/request'
import { useUserStore } from '@/store/user'
import type { IUserInfo } from '@/types'

const userStore = useUserStore()
const userInfo = computed<IUserInfo | null>(() => userStore.userInfo)

function onChooseAvatar() {
  uni.chooseMedia({
    count: 1,
    mediaType: ['image'],
    success: async (res) => {
      const tempPath = res.tempFiles[0].tempFilePath
      try {
        // TODO: 上传头像文件到服务器，获取 URL 后调用 put
        await put('/users/me', { avatar_url: tempPath })
        uni.showToast({ title: '头像更新成功', icon: 'success' })
      } catch {
        uni.showToast({ title: '头像更新失败', icon: 'error' })
      }
    },
  })
}
</script>

<style lang="scss" scoped>
.page-profile { min-height: 100vh; background-color: var(--color-bg); padding: 16rpx 24rpx; }
.profile-item {
  display: flex; justify-content: space-between; align-items: center; padding: 28rpx 24rpx; margin-bottom: 2rpx;
  &__label { font-size: var(--font-size-base); color: var(--color-text); }
  &__value { font-size: var(--font-size-base); color: var(--color-text-secondary); }
  &__avatar { width: 80rpx; height: 80rpx; border-radius: 50%; background-color: var(--color-bg-light); display: flex; justify-content: center; align-items: center; text { font-size: 40rpx; } }
}
</style>

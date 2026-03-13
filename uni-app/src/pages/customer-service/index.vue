<template>
  <!-- 客服中心 -->
  <view class="page-service">
    <!-- 搜索 -->
    <view class="service-search">
      <view class="service-search__wrap">
        <text>🔍</text>
        <input placeholder="搜索您的问题..." :value="searchKeyword" @input="onSearchInput" @confirm="onSearchConfirm" confirm-type="search" />
      </view>
    </view>
    <!-- 分类导航 -->
    <view class="service-categories card">
      <view class="service-category" v-for="item in categories" :key="item.id" @tap="onCategoryTap(item.name)">
        <text class="service-category__icon">{{ item.icon }}</text>
        <text class="service-category__name">{{ item.name }}</text>
      </view>
    </view>
    <!-- 热门问题 -->
    <view class="faq-section">
      <text class="faq-title">🔥 热门问题</text>
      <view class="faq-list">
        <view class="faq-item card" v-for="item in hotQuestions" :key="item.id" @tap="onFaqTap(item.id)">
          <text class="faq-item__q">{{ item.question }}</text>
          <text class="faq-item__arrow">›</text>
        </view>
      </view>
    </view>
    <!-- 人工客服 -->
    <view class="human-service card">
      <text class="human-service__title">📞 联系人工客服</text>
      <text class="human-service__hours">客服时间：{{ serviceHours }}</text>
      <view class="human-service__actions">
        <view class="human-service__btn" @tap="onCallPhone">
          <text class="human-service__btn-icon">📞</text>
          <text>拨打电话</text>
          <text class="human-service__btn-info">{{ servicePhone }}</text>
        </view>
        <view class="human-service__btn" @tap="onCopyWechat">
          <text class="human-service__btn-icon">💬</text>
          <text>微信客服</text>
          <text class="human-service__btn-info">复制微信号</text>
        </view>
      </view>
    </view>
    <!-- FAQ答案弹窗 -->
    <view class="faq-mask" v-if="selectedFaq" @tap="onCloseFaq">
      <view class="faq-popup card" @tap.stop>
        <text class="faq-popup__q">{{ selectedFaq.question }}</text>
        <view class="faq-popup__divider"></view>
        <text class="faq-popup__a">{{ selectedFaq.answer }}</text>
        <view class="faq-popup__close" @tap="onCloseFaq"><text>知道了</text></view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { get } from '@/utils/request'
import type { IFaqCategory, IFaqItem } from '@/types'

interface FaqItem { id: number; question: string; answer: string }

const searchKeyword = ref('')
const categories = ref<{ id: number; name: string; icon: string }[]>([])
const hotQuestions = ref<FaqItem[]>([])
const selectedFaq = ref<FaqItem | null>(null)
const servicePhone = ref('400-888-1234')
const serviceWechat = ref('yyyl_service')
const serviceHours = ref('09:00 - 21:00')

onLoad(() => { loadFaqData() })

async function loadFaqData() {
  try {
    const data = await get<IFaqCategory[]>('/faq/categories', undefined, { needAuth: false })
    if (data && data.length > 0) {
      categories.value = data.map(c => ({ id: c.id, name: c.name, icon: c.icon }))
      // 从所有分类中提取热门问题（前5个）
      const allItems: FaqItem[] = []
      data.forEach(cat => {
        cat.items?.forEach(item => {
          allItems.push({ id: item.id, question: item.question, answer: item.answer })
        })
      })
      hotQuestions.value = allItems.slice(0, 5)
    }
  } catch {
    // 回退到默认分类
    categories.value = [
      { id: 1, name: '预定问题', icon: '🏕️' }, { id: 2, name: '退票退款', icon: '↩️' },
      { id: 3, name: '营位介绍', icon: '⛺' }, { id: 4, name: '交通路线', icon: '🚗' },
      { id: 5, name: '装备租赁', icon: '🎒' }, { id: 6, name: '活动咨询', icon: '🎪' },
      { id: 7, name: '会员与次数卡', icon: '💳' }, { id: 8, name: '其他问题', icon: '❓' },
    ]
  }
}

function onSearchInput(e: any) { searchKeyword.value = e.detail.value }
async function onSearchConfirm() {
  const kw = searchKeyword.value.trim()
  if (!kw) return
  try {
    const items = await get<IFaqItem[]>('/faq/items', { keyword: kw }, { needAuth: false })
    if (items && items.length > 0) {
      selectedFaq.value = { id: items[0].id, question: items[0].question, answer: items[0].answer }
    } else {
      uni.showToast({ title: '未找到相关问题，请联系人工客服', icon: 'none' })
    }
  } catch {
    // 本地搜索回退
    const found = hotQuestions.value.find(q => q.question.includes(kw) || q.answer.includes(kw))
    if (found) { selectedFaq.value = found } else { uni.showToast({ title: '未找到相关问题，请联系人工客服', icon: 'none' }) }
  }
}
function onFaqTap(id: number) { const faq = hotQuestions.value.find(q => q.id === id); if (faq) selectedFaq.value = faq }
function onCategoryTap(name: string) { uni.showToast({ title: `${name}分类开发中`, icon: 'none' }) }
function onCloseFaq() { selectedFaq.value = null }
function onCallPhone() { uni.makePhoneCall({ phoneNumber: servicePhone.value }) }
function onCopyWechat() { uni.setClipboardData({ data: serviceWechat.value, success: () => uni.showToast({ title: '微信号已复制', icon: 'success' }) }) }
</script>

<style lang="scss" scoped>
.page-service { min-height: 100vh; background-color: var(--color-bg); }
.service-search {
  padding: 16rpx 24rpx; background-color: var(--color-bg-white);
  &__wrap { display: flex; align-items: center; height: 72rpx; background-color: var(--color-bg-grey); border-radius: var(--radius-round); padding: 0 20rpx; gap: 12rpx;
    text { font-size: 28rpx; } input { flex: 1; font-size: var(--font-size-base); }
  }
}
.service-categories { margin: 16rpx 24rpx; padding: 20rpx; display: grid; grid-template-columns: repeat(4, 1fr); gap: 20rpx; }
.service-category {
  display: flex; flex-direction: column; align-items: center; padding: 12rpx 0;
  &:active { opacity: 0.7; }
  &__icon { font-size: 40rpx; margin-bottom: 8rpx; }
  &__name { font-size: var(--font-size-xs); color: var(--color-text-secondary); text-align: center; }
}
.faq-section { padding: 0 24rpx; margin-bottom: 16rpx; }
.faq-title { font-size: var(--font-size-lg); font-weight: 700; display: block; margin-bottom: 16rpx; }
.faq-item {
  display: flex; justify-content: space-between; align-items: center; padding: 24rpx; margin-bottom: 8rpx;
  &:active { opacity: 0.85; }
  &__q { font-size: var(--font-size-base); color: var(--color-text); flex: 1; }
  &__arrow { font-size: var(--font-size-xl); color: var(--color-text-placeholder); margin-left: 16rpx; }
}
.human-service {
  margin: 16rpx 24rpx; padding: 28rpx;
  &__title { font-size: var(--font-size-md); font-weight: 600; display: block; margin-bottom: 8rpx; }
  &__hours { font-size: var(--font-size-sm); color: var(--color-text-placeholder); display: block; margin-bottom: 20rpx; }
  &__actions { display: flex; gap: 16rpx; }
  &__btn { flex: 1; display: flex; flex-direction: column; align-items: center; gap: 6rpx; padding: 24rpx; background-color: var(--color-bg-light); border-radius: var(--radius-lg);
    &:active { opacity: 0.85; } text { font-size: var(--font-size-sm); color: var(--color-text); }
  }
  &__btn-icon { font-size: 40rpx !important; }
  &__btn-info { font-size: var(--font-size-xs) !important; color: var(--color-text-placeholder) !important; }
}
.faq-mask { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background-color: rgba(0,0,0,0.5); z-index: 1000; display: flex; align-items: center; justify-content: center; }
.faq-popup {
  width: 85%; padding: 32rpx;
  &__q { font-size: var(--font-size-lg); font-weight: 700; color: var(--color-text); display: block; }
  &__divider { height: 1rpx; background-color: #F0F0F0; margin: 20rpx 0; }
  &__a { font-size: var(--font-size-base); color: var(--color-text-secondary); line-height: 1.8; display: block; }
  &__close { text-align: center; margin-top: 28rpx;
    text { font-size: var(--font-size-base); color: var(--color-primary); font-weight: 600; padding: 12rpx 48rpx; }
    &:active { opacity: 0.7; }
  }
}
</style>

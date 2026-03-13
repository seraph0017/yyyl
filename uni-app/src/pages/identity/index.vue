<template>
  <view class="page-identity">
    <view class="identity-card card" v-for="item in identities" :key="item.id">
      <view class="identity-card__header">
        <text class="identity-card__name">{{ item.name }}</text>
        <text class="identity-card__default tag tag--primary" v-if="item.is_default">默认</text>
      </view>
      <text class="identity-card__info">身份证：{{ item.id_card }}</text>
      <text class="identity-card__info">手机号：{{ item.phone }}</text>
      <view class="identity-card__actions">
        <text class="identity-card__btn" @tap="onEditIdentity(item.id)">编辑</text>
        <text class="identity-card__btn identity-card__btn--del" @tap="onDeleteIdentity(item.id)">删除</text>
      </view>
    </view>
    <view class="add-btn" @tap="onAddIdentity"><text>+ 添加出行人</text></view>
    <EmptyState v-if="identities.length === 0 && !showForm" icon="👤" title="暂无出行人信息" buttonText="添加出行人" @action="onAddIdentity" />
    <!-- 表单弹窗 -->
    <view class="form-mask" v-if="showForm" @tap="onCancelForm">
      <view class="form-popup card" @tap.stop>
        <text class="form-popup__title">{{ editingId ? '编辑' : '添加' }}出行人</text>
        <view class="form-group">
          <text class="form-label">姓名</text>
          <input class="form-input" placeholder="请输入姓名" :value="formData.name" @input="(e: any) => formData.name = e.detail.value" />
        </view>
        <view class="form-group">
          <text class="form-label">身份证号</text>
          <input class="form-input" placeholder="请输入身份证号" :value="formData.id_card" @input="(e: any) => formData.id_card = e.detail.value" :maxlength="18" />
        </view>
        <view class="form-group">
          <text class="form-label">手机号</text>
          <input class="form-input" placeholder="请输入手机号" :value="formData.phone" @input="(e: any) => formData.phone = e.detail.value" type="number" :maxlength="11" />
        </view>
        <view class="form-actions">
          <view class="form-btn form-btn--cancel" @tap="onCancelForm"><text>取消</text></view>
          <view class="form-btn form-btn--save" @tap="onSaveIdentity"><text>保存</text></view>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { get, post, put, del } from '@/utils/request'
import { ensureLogin } from '@/utils/auth'
import { isValidPhone, isValidIdCard } from '@/utils/util'
import EmptyState from '@/components/empty-state/index.vue'
import type { IIdentity } from '@/types'

const identities = ref<IIdentity[]>([])
const showForm = ref(false)
const editingId = ref(0)
const formData = reactive({ name: '', id_card: '', phone: '' })

onLoad(() => { loadIdentities() })

async function loadIdentities() {
  try {
    await ensureLogin()
    const data = await get<IIdentity[]>('/users/identities')
    identities.value = data || []
  } catch {
    identities.value = []
    uni.showToast({ title: '加载出行人信息失败', icon: 'error' })
  }
}
function onAddIdentity() { showForm.value = true; editingId.value = 0; formData.name = ''; formData.id_card = ''; formData.phone = '' }
function onEditIdentity(id: number) {
  const i = identities.value.find(x => x.id === id)
  if (i) { showForm.value = true; editingId.value = id; formData.name = i.name; formData.id_card = i.id_card; formData.phone = i.phone }
}
function onDeleteIdentity(id: number) {
  uni.showModal({
    title: '提示',
    content: '确定删除该出行人信息吗？',
    success: async (res) => {
      if (res.confirm) {
        try {
          await del(`/users/identities/${id}`)
          identities.value = identities.value.filter(x => x.id !== id)
          uni.showToast({ title: '已删除', icon: 'success' })
        } catch {
          uni.showToast({ title: '删除失败', icon: 'error' })
        }
      }
    },
  })
}
async function onSaveIdentity() {
  if (!formData.name.trim()) { uni.showToast({ title: '请输入姓名', icon: 'none' }); return }
  if (!isValidIdCard(formData.id_card)) { uni.showToast({ title: '请输入正确的身份证号', icon: 'none' }); return }
  if (!isValidPhone(formData.phone)) { uni.showToast({ title: '请输入正确的手机号', icon: 'none' }); return }
  try {
    if (editingId.value) {
      await put(`/users/identities/${editingId.value}`, { name: formData.name, id_card: formData.id_card, phone: formData.phone })
    } else {
      await post('/users/identities', { name: formData.name, id_card: formData.id_card, phone: formData.phone })
    }
    uni.showToast({ title: '保存成功', icon: 'success' })
    showForm.value = false
    loadIdentities()
  } catch {
    uni.showToast({ title: '保存失败', icon: 'error' })
  }
}
function onCancelForm() { showForm.value = false }
</script>

<style lang="scss" scoped>
.page-identity { min-height: 100vh; background-color: var(--color-bg); padding: 16rpx 24rpx; }
.identity-card {
  padding: 24rpx; margin-bottom: 16rpx;
  &__header { display: flex; align-items: center; gap: 12rpx; margin-bottom: 12rpx; }
  &__name { font-size: var(--font-size-lg); font-weight: 600; color: var(--color-text); }
  &__info { display: block; font-size: var(--font-size-sm); color: var(--color-text-secondary); margin-top: 6rpx; }
  &__actions { display: flex; gap: 24rpx; margin-top: 16rpx; padding-top: 16rpx; border-top: 1rpx solid #F0F0F0; }
  &__btn { font-size: var(--font-size-sm); color: var(--color-primary); padding: 8rpx; &--del { color: var(--color-red); } }
}
.add-btn { text-align: center; padding: 28rpx; text { font-size: var(--font-size-base); color: var(--color-primary); font-weight: 500; } &:active { opacity: 0.7; } }
.form-mask { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background-color: rgba(0,0,0,0.5); z-index: 1000; display: flex; align-items: center; justify-content: center; }
.form-popup { width: 85%; padding: 32rpx; &__title { font-size: var(--font-size-lg); font-weight: 700; display: block; margin-bottom: 24rpx; text-align: center; } }
.form-group { margin-bottom: 20rpx; }
.form-label { font-size: var(--font-size-sm); color: var(--color-text-secondary); display: block; margin-bottom: 8rpx; }
.form-input { height: 80rpx; background-color: var(--color-bg-grey); border-radius: var(--radius-md); padding: 0 20rpx; font-size: var(--font-size-base); }
.form-actions { display: flex; gap: 16rpx; margin-top: 28rpx; }
.form-btn {
  flex: 1; height: 80rpx; display: flex; justify-content: center; align-items: center; border-radius: var(--radius-xl); font-size: var(--font-size-base); font-weight: 600;
  &--cancel { background-color: var(--color-bg-grey); text { color: var(--color-text-secondary); } }
  &--save { background-color: var(--color-primary); text { color: #fff; } }
  &:active { opacity: 0.85; }
}
</style>

<template>
  <view class="seckill-prefill" v-if="isWarmup || hasPrefillData">
    <!-- 秒杀状态 -->
    <view class="seckill-status" v-if="seckillStatus">
      <view class="seckill-status__header">
        <text class="seckill-status__icon">⚡</text>
        <text class="seckill-status__label">{{ statusLabel }}</text>
        <view class="seckill-status__badge" :class="[`seckill-status__badge--${seckillStatus.status}`]">
          <text>{{ statusText }}</text>
        </view>
      </view>
      <view class="seckill-status__info">
        <view class="seckill-status__item">
          <text class="seckill-status__value">{{ seckillStatus.remaining_stock }}</text>
          <text class="seckill-status__desc">剩余库存</text>
        </view>
        <view class="seckill-status__divider" />
        <view class="seckill-status__item">
          <text class="seckill-status__value">{{ seckillStatus.online_count }}</text>
          <text class="seckill-status__desc">在线等待</text>
        </view>
      </view>
    </view>

    <!-- 预填面板 -->
    <view class="prefill-panel" v-if="isWarmup">
      <view class="prefill-panel__header">
        <text class="prefill-panel__title">📋 提前填写信息</text>
        <text class="prefill-panel__tip">秒杀开始后可一键下单</text>
      </view>

      <!-- 已预填成功 -->
      <view class="prefill-success" v-if="isSaved">
        <text class="prefill-success__icon">✅</text>
        <view class="prefill-success__info">
          <text class="prefill-success__title">预填信息已保存</text>
          <text class="prefill-success__desc">
            {{ savedIdentityNames }} · {{ form.phone }}
          </text>
        </view>
        <view class="prefill-success__btn" @tap="isSaved = false">
          <text>修改</text>
        </view>
      </view>

      <!-- 预填表单 -->
      <view class="prefill-form" v-else>
        <!-- 选择出行人 -->
        <view class="form-group">
          <view class="form-group__label">
            <text>出行人</text>
            <text class="form-group__required">*</text>
          </view>
          <view class="identity-list" v-if="identities.length > 0">
            <view
              class="identity-tag"
              :class="{ 'identity-tag--selected': form.identity_ids.includes(item.id) }"
              v-for="item in identities"
              :key="item.id"
              @tap="toggleIdentity(item.id)"
            >
              <text>{{ item.name }}</text>
            </view>
          </view>
          <view class="form-group__empty" v-else>
            <text class="form-group__empty-text">暂无出行人</text>
            <view class="form-group__link" @tap="goAddIdentity">
              <text>去添加</text>
            </view>
          </view>
        </view>

        <!-- 手机号 -->
        <view class="form-group">
          <view class="form-group__label">
            <text>联系电话</text>
            <text class="form-group__required">*</text>
          </view>
          <input
            class="form-input"
            type="number"
            maxlength="11"
            placeholder="请输入手机号"
            v-model="form.phone"
          />
        </view>

        <!-- 免责声明 -->
        <view class="form-group" v-if="showDisclaimer">
          <view class="disclaimer-row" @tap="form.disclaimer_signed = !form.disclaimer_signed">
            <view
              class="disclaimer-checkbox"
              :class="{ 'disclaimer-checkbox--checked': form.disclaimer_signed }"
            >
              <text v-if="form.disclaimer_signed">✓</text>
            </view>
            <text class="disclaimer-text">我已阅读并同意《安全免责声明》</text>
          </view>
        </view>

        <!-- 保存按钮 -->
        <view
          class="prefill-btn btn-primary"
          :class="{ 'prefill-btn--disabled': !canSave }"
          @tap="savePrefill"
        >
          <text v-if="saving">保存中...</text>
          <text v-else>保存预填信息</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { get, put } from '@/utils/request'
import type { ISeckillPrefill, ISeckillStatus, IIdentity } from '@/types'

const props = defineProps<{
  productId: number
  isWarmup: boolean
  showDisclaimer?: boolean
}>()

const loading = ref(false)
const saving = ref(false)
const isSaved = ref(false)
const identities = ref<IIdentity[]>([])
const seckillStatus = ref<ISeckillStatus | null>(null)
const hasPrefillData = ref(false)

let statusTimer: ReturnType<typeof setInterval> | null = null

const form = reactive({
  identity_ids: [] as number[],
  phone: '',
  disclaimer_signed: false,
  bundle_items: [] as { product_id: number; quantity: number }[],
})

const canSave = computed(() => {
  if (form.identity_ids.length === 0) return false
  if (!form.phone || form.phone.length !== 11) return false
  if (props.showDisclaimer && !form.disclaimer_signed) return false
  return !saving.value
})

const savedIdentityNames = computed(() => {
  return identities.value
    .filter((i) => form.identity_ids.includes(i.id))
    .map((i) => i.name)
    .join('、')
})

const statusLabel = computed(() => {
  if (!seckillStatus.value) return '秒杀'
  const map: Record<string, string> = {
    warmup: '即将开抢',
    active: '秒杀进行中',
    ended: '秒杀已结束',
    sold_out: '已售罄',
  }
  return map[seckillStatus.value.status] || '秒杀'
})

const statusText = computed(() => {
  if (!seckillStatus.value) return ''
  const map: Record<string, string> = {
    warmup: '预热中',
    active: '抢购中',
    ended: '已结束',
    sold_out: '已抢光',
  }
  return map[seckillStatus.value.status] || ''
})

/** 切换出行人 */
function toggleIdentity(id: number) {
  const idx = form.identity_ids.indexOf(id)
  if (idx > -1) {
    form.identity_ids.splice(idx, 1)
  } else {
    form.identity_ids.push(id)
  }
}

/** 前往添加出行人 */
function goAddIdentity() {
  uni.navigateTo({ url: '/pages/identity/index' })
}

/** 保存预填信息 */
async function savePrefill() {
  if (!canSave.value) return

  // 手机号格式校验
  const phoneReg = /^1[3-9]\d{9}$/
  if (!phoneReg.test(form.phone)) {
    uni.showToast({ title: '请输入正确的手机号', icon: 'none' })
    return
  }

  saving.value = true
  try {
    await put('/orders/seckill/prefill', {
      product_id: props.productId,
      identity_ids: form.identity_ids,
      phone: form.phone,
      disclaimer_signed: form.disclaimer_signed,
      bundle_items: form.bundle_items,
    })

    isSaved.value = true
    hasPrefillData.value = true
    uni.showToast({ title: '预填信息已保存', icon: 'success' })
  } catch {
    uni.showToast({ title: '保存失败，请重试', icon: 'none' })
  } finally {
    saving.value = false
  }
}

/** 加载已保存的预填数据 */
async function loadPrefill() {
  try {
    const data = await get<ISeckillPrefill>(
      `/orders/seckill/prefill/${props.productId}`,
      undefined,
      { showError: false },
    )

    if (data && data.product_id) {
      form.identity_ids = data.identity_ids || []
      form.phone = data.phone || ''
      form.disclaimer_signed = data.disclaimer_signed || false
      form.bundle_items = data.bundle_items || []
      isSaved.value = true
      hasPrefillData.value = true
    }
  } catch {
    // 无预填数据
  }
}

/** 加载出行人列表 */
async function loadIdentities() {
  try {
    const data = await get<IIdentity[]>('/identities', undefined, { showError: false })
    if (data && Array.isArray(data)) {
      identities.value = data
    }
  } catch {
    // 静默处理
  }
}

/** 加载秒杀状态 */
async function loadSeckillStatus() {
  try {
    const data = await get<ISeckillStatus>(
      `/products/${props.productId}/seckill-status`,
      undefined,
      { needAuth: false, showError: false },
    )
    if (data) {
      seckillStatus.value = data
    }
  } catch {
    // 静默处理
  }
}

onMounted(async () => {
  loading.value = true

  await Promise.all([
    loadIdentities(),
    loadPrefill(),
    loadSeckillStatus(),
  ])

  loading.value = false

  // 定时刷新秒杀状态（每10秒）
  statusTimer = setInterval(() => {
    loadSeckillStatus()
  }, 10000)
})

onUnmounted(() => {
  if (statusTimer) {
    clearInterval(statusTimer)
    statusTimer = null
  }
})
</script>

<style lang="scss" scoped>
.seckill-prefill {
  margin: 24rpx 0;
}

.seckill-status {
  background: linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%);
  border-radius: var(--radius-xl);
  padding: 24rpx 28rpx;
  margin-bottom: 20rpx;

  &__header {
    display: flex;
    align-items: center;
    gap: 10rpx;
    margin-bottom: 20rpx;
  }

  &__icon {
    font-size: 36rpx;
  }

  &__label {
    font-size: var(--font-size-lg);
    font-weight: 700;
    color: var(--color-text);
    flex: 1;
  }

  &__badge {
    padding: 6rpx 16rpx;
    border-radius: var(--radius-round);
    text {
      font-size: var(--font-size-xs);
      font-weight: 600;
      color: #fff;
    }

    &--warmup { background-color: var(--color-orange); }
    &--active { background-color: var(--color-red); }
    &--ended { background-color: var(--color-text-placeholder); }
    &--sold_out { background-color: var(--color-text-placeholder); }
  }

  &__info {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0;
  }

  &__item {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
  }

  &__divider {
    width: 1rpx;
    height: 48rpx;
    background-color: rgba(0, 0, 0, 0.1);
  }

  &__value {
    font-size: var(--font-size-xxl);
    font-weight: 700;
    color: var(--color-orange);
  }

  &__desc {
    font-size: var(--font-size-xs);
    color: var(--color-text-secondary);
    margin-top: 4rpx;
  }
}

.prefill-panel {
  background-color: var(--color-bg-card);
  border-radius: var(--radius-xl);
  overflow: hidden;
  box-shadow: var(--shadow-sm);

  &__header {
    padding: 28rpx 28rpx 16rpx;
  }

  &__title {
    font-size: var(--font-size-lg);
    font-weight: 700;
    color: var(--color-text);
    display: block;
  }

  &__tip {
    font-size: var(--font-size-xs);
    color: var(--color-text-placeholder);
    margin-top: 4rpx;
    display: block;
  }
}

.prefill-success {
  display: flex;
  align-items: center;
  padding: 24rpx 28rpx 28rpx;
  gap: 16rpx;

  &__icon {
    font-size: 48rpx;
  }

  &__info {
    flex: 1;
    min-width: 0;
  }

  &__title {
    font-size: var(--font-size-base);
    font-weight: 600;
    color: var(--color-green);
    display: block;
  }

  &__desc {
    font-size: var(--font-size-sm);
    color: var(--color-text-secondary);
    margin-top: 4rpx;
    display: block;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  &__btn {
    padding: 10rpx 24rpx;
    background-color: var(--color-bg-grey);
    border-radius: var(--radius-round);
    flex-shrink: 0;

    text {
      font-size: var(--font-size-sm);
      color: var(--color-primary);
      font-weight: 500;
    }

    &:active { opacity: 0.7; }
  }
}

.prefill-form {
  padding: 0 28rpx 28rpx;
}

.form-group {
  margin-bottom: 24rpx;

  &__label {
    display: flex;
    align-items: center;
    gap: 4rpx;
    margin-bottom: 16rpx;
    font-size: var(--font-size-sm);
    font-weight: 600;
    color: var(--color-text);
  }

  &__required {
    color: var(--color-red);
    font-size: var(--font-size-sm);
  }

  &__empty {
    display: flex;
    align-items: center;
    gap: 12rpx;
  }

  &__empty-text {
    font-size: var(--font-size-sm);
    color: var(--color-text-placeholder);
  }

  &__link {
    text {
      font-size: var(--font-size-sm);
      color: var(--color-primary);
      font-weight: 500;
    }
    &:active { opacity: 0.7; }
  }
}

.identity-list {
  display: flex;
  flex-wrap: wrap;
  gap: 12rpx;
}

.identity-tag {
  padding: 12rpx 24rpx;
  border: 2rpx solid #e0e0e0;
  border-radius: var(--radius-round);
  transition: all 0.2s;

  text {
    font-size: var(--font-size-sm);
    color: var(--color-text-secondary);
  }

  &:active { opacity: 0.7; }

  &--selected {
    border-color: var(--color-primary);
    background-color: var(--color-primary-bg);

    text { color: var(--color-primary); font-weight: 500; }
  }
}

.form-input {
  width: 100%;
  height: 80rpx;
  padding: 0 24rpx;
  background-color: var(--color-bg-grey);
  border-radius: var(--radius-md);
  font-size: var(--font-size-base);
  color: var(--color-text);
  box-sizing: border-box;
}

.disclaimer-row {
  display: flex;
  align-items: center;
  gap: 12rpx;

  &:active { opacity: 0.8; }
}

.disclaimer-checkbox {
  width: 40rpx;
  height: 40rpx;
  border: 2rpx solid #d9d9d9;
  border-radius: var(--radius-sm);
  display: flex;
  justify-content: center;
  align-items: center;
  flex-shrink: 0;
  transition: all 0.2s;

  text { font-size: 22rpx; color: #fff; }

  &--checked {
    background-color: var(--color-primary);
    border-color: var(--color-primary);
  }
}

.disclaimer-text {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.prefill-btn {
  width: 100%;
  height: 88rpx;
  display: flex;
  justify-content: center;
  align-items: center;
  background-color: var(--color-primary);
  border-radius: var(--radius-lg);
  margin-top: 32rpx;

  text {
    font-size: var(--font-size-base);
    font-weight: 600;
    color: #fff;
  }

  &:active { opacity: 0.85; }

  &--disabled {
    opacity: 0.5;
    &:active { opacity: 0.5; }
  }
}
</style>

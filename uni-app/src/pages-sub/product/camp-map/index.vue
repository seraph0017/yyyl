<template>
  <view class="page-camp-map">
    <!-- 日期选择 -->
    <view class="date-bar">
      <scroll-view class="date-bar__scroll" scroll-x enable-flex>
        <view
          class="date-tab"
          :class="{ 'date-tab--active': selectedDate === item.value }"
          v-for="item in dateOptions"
          :key="item.value"
          @tap="onDateChange(item.value)"
        >
          <text class="date-tab__label">{{ item.label }}</text>
          <text class="date-tab__date">{{ item.short }}</text>
        </view>
      </scroll-view>
    </view>

    <!-- 图例 -->
    <view class="legend-bar">
      <view class="legend-item">
        <view class="legend-dot legend-dot--available" />
        <text class="legend-text">可预约</text>
      </view>
      <view class="legend-item">
        <view class="legend-dot legend-dot--tight" />
        <text class="legend-text">紧张</text>
      </view>
      <view class="legend-item">
        <view class="legend-dot legend-dot--full" />
        <text class="legend-text">已满</text>
      </view>
    </view>

    <!-- 地图区域 -->
    <view class="map-container" v-if="campMap">
      <movable-area class="map-area">
        <movable-view
          class="map-movable"
          direction="all"
          :scale="true"
          :scale-min="0.5"
          :scale-max="3"
          :scale-value="mapScale"
          @scale="onMapScale"
        >
          <!-- 地图底图 -->
          <image
            class="map-image"
            :src="resolveImageUrl(campMap.map_image)"
            mode="widthFix"
            @load="onMapImageLoad"
          />

          <!-- 区域热点 -->
          <view
            class="zone-hotspot"
            :class="[`zone-hotspot--${getZoneStatus(zone)}`]"
            v-for="zone in campMap.zones"
            :key="zone.id"
            :style="getZoneStyle(zone)"
            @tap="onZoneTap(zone)"
          >
            <text class="zone-hotspot__label">{{ zone.zone_code }}</text>
            <text class="zone-hotspot__count" v-if="zone.available_count !== undefined">
              {{ zone.available_count }}/{{ zone.total_count }}
            </text>
          </view>
        </movable-view>
      </movable-area>

      <!-- 缩放提示 -->
      <view class="zoom-tip" v-if="showZoomTip">
        <text>👆 双指缩放可查看详情</text>
      </view>
    </view>

    <!-- 加载状态 -->
    <view class="loading-state" v-else-if="loading">
      <view class="loading-spinner" />
      <text class="loading-text">加载地图中...</text>
    </view>

    <!-- 空状态 -->
    <empty-state
      v-else
      icon="🗺️"
      title="暂无地图数据"
      description="营地地图正在制作中，敬请期待"
    />

    <!-- 区域详情弹层 -->
    <view class="zone-popup-mask" v-if="showZonePopup" @tap="showZonePopup = false">
      <view class="zone-popup" @tap.stop>
        <view class="zone-popup__header">
          <text class="zone-popup__name">{{ selectedZone?.zone_name }}</text>
          <view class="zone-popup__close" @tap="showZonePopup = false">
            <text>✕</text>
          </view>
        </view>

        <view class="zone-popup__body" v-if="selectedZone">
          <text class="zone-popup__desc">{{ selectedZone.description || '暂无描述' }}</text>

          <view class="zone-popup__stats">
            <view class="zone-stat">
              <text class="zone-stat__value" :class="[`zone-stat__value--${getZoneStatus(selectedZone)}`]">
                {{ selectedZone.available_count ?? '-' }}
              </text>
              <text class="zone-stat__label">可用营位</text>
            </view>
            <view class="zone-stat">
              <text class="zone-stat__value">{{ selectedZone.total_count ?? '-' }}</text>
              <text class="zone-stat__label">总营位数</text>
            </view>
          </view>

          <view
            class="zone-popup__btn btn-primary"
            @tap="onViewProducts"
            v-if="selectedZone.product_ids && selectedZone.product_ids.length > 0"
          >
            <text>查看可预约商品</text>
          </view>
          <view class="zone-popup__empty" v-else>
            <text>该区域暂无可预约商品</text>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { get, resolveImageUrl } from '@/utils/request'
import type { ICampMap, ICampMapZone } from '@/types'
import EmptyState from '@/components/empty-state/index.vue'

const loading = ref(true)
const campMap = ref<ICampMap | null>(null)
const selectedDate = ref('')
const showZonePopup = ref(false)
const selectedZone = ref<ICampMapZone | null>(null)
const mapScale = ref(1)
const showZoomTip = ref(true)

/** 日期选项 */
interface DateOption {
  label: string
  short: string
  value: string
}

const dateOptions = ref<DateOption[]>([])

/** 生成日期选项（今天 + 后6天） */
function initDateOptions() {
  const options: DateOption[] = []
  const weekdays = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']

  for (let i = 0; i < 7; i++) {
    const d = new Date()
    d.setDate(d.getDate() + i)
    const dateStr = formatDateStr(d)
    const month = d.getMonth() + 1
    const day = d.getDate()

    options.push({
      label: i === 0 ? '今天' : i === 1 ? '明天' : weekdays[d.getDay()],
      short: `${month}/${day}`,
      value: dateStr,
    })
  }

  dateOptions.value = options
  selectedDate.value = options[0].value
}

function formatDateStr(d: Date): string {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${dd}`
}

/** 切换日期 */
function onDateChange(date: string) {
  selectedDate.value = date
  loadZones()
}

/** 获取区域状态 */
function getZoneStatus(zone: ICampMapZone): string {
  if (zone.available_count === undefined || zone.total_count === undefined) return 'unknown'
  if (zone.available_count === 0) return 'full'
  if (zone.available_count <= (zone.total_count * 0.3)) return 'tight'
  return 'available'
}

/** 区域热点样式 */
function getZoneStyle(zone: ICampMapZone) {
  const c = zone.coordinates
  if (!c) return {}
  return {
    left: `${c.x}%`,
    top: `${c.y}%`,
    width: `${c.width}%`,
    height: `${c.height}%`,
  }
}

/** 点击区域 */
function onZoneTap(zone: ICampMapZone) {
  selectedZone.value = zone
  showZonePopup.value = true
}

/** 查看商品 */
function onViewProducts() {
  if (!selectedZone.value || !selectedZone.value.product_ids.length) return

  // 跳转到分类页，传区域筛选
  const productId = selectedZone.value.product_ids[0]
  showZonePopup.value = false
  uni.navigateTo({
    url: `/pages/product-detail/index?id=${productId}`,
  })
}

function onMapImageLoad() {
  // 地图图片加载完成
}

function onMapScale(e: { detail: { scale: number } }) {
  mapScale.value = e.detail.scale
  if (showZoomTip.value) {
    showZoomTip.value = false
  }
}

/** 加载地图列表 */
async function loadMapData() {
  loading.value = true
  try {
    const data = await get<ICampMap[]>('/camp-maps', undefined, { needAuth: false })
    if (data && data.length > 0) {
      campMap.value = data[0]
      await loadZones()
    }
  } catch {
    campMap.value = null
  } finally {
    loading.value = false
  }
}

/** 加载区域可用状态 */
async function loadZones() {
  if (!campMap.value) return

  try {
    const zones = await get<ICampMapZone[]>(
      `/camp-maps/${campMap.value.id}/zones`,
      { target_date: selectedDate.value },
      { needAuth: false, showError: false },
    )
    if (zones && Array.isArray(zones)) {
      campMap.value.zones = zones
    }
  } catch {
    // 保持已有区域数据
  }
}

onMounted(() => {
  initDateOptions()
  loadMapData()

  // 3秒后隐藏缩放提示
  setTimeout(() => {
    showZoomTip.value = false
  }, 3000)
})
</script>

<style lang="scss" scoped>
.page-camp-map {
  min-height: 100vh;
  background-color: var(--color-bg);
  display: flex;
  flex-direction: column;
}

.date-bar {
  background-color: var(--color-bg-white);
  padding: 16rpx 0;
  box-shadow: var(--shadow-sm);

  &__scroll {
    display: flex;
    white-space: nowrap;
    padding: 0 24rpx;
  }
}

.date-tab {
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  padding: 12rpx 24rpx;
  margin-right: 12rpx;
  border-radius: var(--radius-lg);
  flex-shrink: 0;
  transition: all 0.2s;

  &:active { opacity: 0.7; }

  &__label {
    font-size: var(--font-size-sm);
    color: var(--color-text-secondary);
  }

  &__date {
    font-size: var(--font-size-xs);
    color: var(--color-text-placeholder);
    margin-top: 4rpx;
  }

  &--active {
    background-color: var(--color-primary);

    .date-tab__label { color: #fff; font-weight: 600; }
    .date-tab__date { color: rgba(255, 255, 255, 0.8); }
  }
}

.legend-bar {
  display: flex;
  justify-content: center;
  gap: 32rpx;
  padding: 16rpx 0;
  background-color: var(--color-bg-white);
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 8rpx;
}

.legend-dot {
  width: 20rpx;
  height: 20rpx;
  border-radius: 50%;

  &--available { background-color: var(--color-green); }
  &--tight { background-color: var(--color-yellow); }
  &--full { background-color: var(--color-red); }
}

.legend-text {
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
}

.map-container {
  flex: 1;
  position: relative;
  overflow: hidden;
}

.map-area {
  width: 100%;
  height: 100%;
  min-height: 800rpx;
}

.map-movable {
  width: 100%;
  height: 100%;
  position: relative;
}

.map-image {
  width: 100%;
}

.zone-hotspot {
  position: absolute;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-md);
  border: 3rpx solid rgba(255, 255, 255, 0.8);
  transition: all 0.2s;

  &:active {
    transform: scale(1.05);
  }

  &--available {
    background-color: rgba(76, 175, 80, 0.35);
    border-color: rgba(76, 175, 80, 0.6);
  }

  &--tight {
    background-color: rgba(255, 193, 7, 0.35);
    border-color: rgba(255, 193, 7, 0.6);
  }

  &--full {
    background-color: rgba(229, 57, 53, 0.35);
    border-color: rgba(229, 57, 53, 0.6);
  }

  &--unknown {
    background-color: rgba(158, 158, 158, 0.25);
    border-color: rgba(158, 158, 158, 0.4);
  }

  &__label {
    font-size: 22rpx;
    font-weight: 700;
    color: #fff;
    text-shadow: 0 1rpx 4rpx rgba(0, 0, 0, 0.5);
  }

  &__count {
    font-size: 18rpx;
    color: #fff;
    text-shadow: 0 1rpx 4rpx rgba(0, 0, 0, 0.5);
    margin-top: 2rpx;
  }
}

.zoom-tip {
  position: absolute;
  bottom: 40rpx;
  left: 50%;
  transform: translateX(-50%);
  background-color: rgba(0, 0, 0, 0.6);
  padding: 12rpx 28rpx;
  border-radius: var(--radius-round);
  animation: fadeInUp 0.3s ease;

  text {
    font-size: var(--font-size-xs);
    color: #fff;
    white-space: nowrap;
  }
}

@keyframes fadeInUp {
  from { opacity: 0; transform: translateX(-50%) translateY(20rpx); }
  to { opacity: 1; transform: translateX(-50%) translateY(0); }
}

.loading-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 24rpx;
}

.loading-spinner {
  width: 64rpx;
  height: 64rpx;
  border: 4rpx solid var(--color-bg-grey);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-text {
  font-size: var(--font-size-sm);
  color: var(--color-text-placeholder);
}

/* 弹层 */
.zone-popup-mask {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  z-index: 100;
  display: flex;
  align-items: flex-end;
}

.zone-popup {
  width: 100%;
  background-color: var(--color-bg-white);
  border-radius: var(--radius-xl) var(--radius-xl) 0 0;
  padding-bottom: env(safe-area-inset-bottom);
  animation: slideUp 0.3s ease;

  &__header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 32rpx 32rpx 16rpx;
  }

  &__name {
    font-size: var(--font-size-xl);
    font-weight: 700;
    color: var(--color-text);
  }

  &__close {
    width: 56rpx;
    height: 56rpx;
    display: flex;
    justify-content: center;
    align-items: center;
    background-color: var(--color-bg-grey);
    border-radius: 50%;

    text { font-size: var(--font-size-base); color: var(--color-text-secondary); }
    &:active { opacity: 0.7; }
  }

  &__body {
    padding: 0 32rpx 32rpx;
  }

  &__desc {
    font-size: var(--font-size-sm);
    color: var(--color-text-secondary);
    line-height: 1.6;
    display: block;
    margin-bottom: 24rpx;
  }

  &__stats {
    display: flex;
    gap: 32rpx;
    margin-bottom: 28rpx;
  }

  &__btn {
    width: 100%;
    height: 88rpx;
    display: flex;
    justify-content: center;
    align-items: center;
    background-color: var(--color-primary);
    border-radius: var(--radius-lg);

    text {
      font-size: var(--font-size-base);
      font-weight: 600;
      color: #fff;
    }

    &:active { opacity: 0.85; }
  }

  &__empty {
    text-align: center;
    padding: 20rpx 0;

    text {
      font-size: var(--font-size-sm);
      color: var(--color-text-placeholder);
    }
  }
}

.zone-stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 20rpx 32rpx;
  background-color: var(--color-bg-grey);
  border-radius: var(--radius-lg);
  flex: 1;

  &__value {
    font-size: var(--font-size-xxl);
    font-weight: 700;
    color: var(--color-text);

    &--available { color: var(--color-green); }
    &--tight { color: var(--color-yellow); }
    &--full { color: var(--color-red); }
  }

  &__label {
    font-size: var(--font-size-xs);
    color: var(--color-text-secondary);
    margin-top: 6rpx;
  }
}

@keyframes slideUp {
  from { transform: translateY(100%); }
  to { transform: translateY(0); }
}
</style>

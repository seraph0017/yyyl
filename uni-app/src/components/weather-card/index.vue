<template>
  <view class="weather-card" v-if="!loadFailed">
    <!-- 加载骨架 -->
    <view class="weather-card__skeleton" v-if="loading">
      <view class="skeleton-bar skeleton-bar--lg" />
      <view class="skeleton-bar skeleton-bar--sm" />
      <view class="skeleton-bar skeleton-bar--md" />
    </view>

    <!-- 天气内容 -->
    <view class="weather-card__content" v-else>
      <!-- 当前天气 -->
      <view class="weather-current">
        <view class="weather-current__left">
          <text class="weather-current__icon">{{ weatherEmoji }}</text>
          <view class="weather-current__info">
            <text class="weather-current__temp">{{ current.temperature }}°</text>
            <text class="weather-current__desc">{{ current.description || current.weather }}</text>
          </view>
        </view>
        <view class="weather-current__right">
          <view class="weather-current__detail">
            <text class="weather-detail__label">💨 {{ current.wind }}</text>
          </view>
          <view class="weather-current__detail">
            <text class="weather-detail__label">💧 {{ current.humidity }}%</text>
          </view>
          <view class="weather-current__detail">
            <text class="weather-detail__label">🌅 {{ current.sunrise }}</text>
          </view>
        </view>
      </view>

      <!-- 露营建议 -->
      <view class="weather-tip" :class="[`weather-tip--${tipLevel}`]">
        <text class="weather-tip__icon">{{ tipIcon }}</text>
        <text class="weather-tip__text">{{ tipText }}</text>
      </view>

      <!-- 未来预报 -->
      <scroll-view class="weather-forecast" scroll-x enable-flex v-if="forecast.length > 0">
        <view
          class="forecast-item"
          v-for="item in forecast"
          :key="item.date"
        >
          <text class="forecast-item__date">{{ formatDate(item.date) }}</text>
          <text class="forecast-item__icon">{{ getForecastEmoji(item.weather) }}</text>
          <text class="forecast-item__weather">{{ item.weather }}</text>
          <text class="forecast-item__temp">{{ item.temperature_min }}°~{{ item.temperature_max }}°</text>
        </view>
      </scroll-view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { get } from '@/utils/request'
import type { IWeatherCurrent, IWeatherForecast } from '@/types'

const loading = ref(true)
const loadFailed = ref(false)

const current = ref<IWeatherCurrent>({
  temperature: 0,
  weather: '',
  wind: '',
  humidity: 0,
  sunrise: '',
  sunset: '',
  icon: '',
  description: '',
})

const forecast = ref<IWeatherForecast[]>([])

/** 天气 → emoji 映射 */
const weatherEmojiMap: Record<string, string> = {
  '晴': '☀️',
  '多云': '⛅',
  '阴': '☁️',
  '小雨': '🌦️',
  '中雨': '🌧️',
  '大雨': '🌧️',
  '暴雨': '⛈️',
  '雷阵雨': '⛈️',
  '雪': '🌨️',
  '小雪': '🌨️',
  '雾': '🌫️',
  '霾': '🌫️',
}

const weatherEmoji = computed(() => {
  if (current.value.icon) return current.value.icon
  return getEmojiByWeather(current.value.weather)
})

function getEmojiByWeather(weather: string): string {
  for (const key of Object.keys(weatherEmojiMap)) {
    if (weather.includes(key)) return weatherEmojiMap[key]
  }
  return '🌤️'
}

function getForecastEmoji(weather: string): string {
  return getEmojiByWeather(weather)
}

/** 露营建议 */
const tipLevel = computed<'good' | 'warn' | 'bad'>(() => {
  const w = current.value.weather
  if (w.includes('雨') || w.includes('雷') || w.includes('暴')) return 'bad'
  if (w.includes('阴') || w.includes('雾') || w.includes('霾') || current.value.humidity > 85) return 'warn'
  return 'good'
})

const tipIcon = computed(() => {
  const map = { good: '🏕️', warn: '⚠️', bad: '🚫' }
  return map[tipLevel.value]
})

const tipText = computed(() => {
  const w = current.value.weather
  if (w.includes('暴雨') || w.includes('雷')) return '恶劣天气，建议取消户外活动'
  if (w.includes('大雨')) return '雨势较大，不建议露营'
  if (w.includes('雨')) return '有降雨，注意防雨准备'
  if (w.includes('雾') || w.includes('霾')) return '能见度低，出行注意安全'
  if (current.value.humidity > 85) return '湿度较高，注意防潮'
  if (current.value.temperature > 35) return '高温天气，注意防暑'
  if (current.value.temperature < 5) return '气温偏低，注意保暖'
  return '天气不错，适合露营！'
})

/** 格式化日期 */
function formatDate(dateStr: string): string {
  const date = new Date(dateStr)
  const today = new Date()
  const tomorrow = new Date(today)
  tomorrow.setDate(today.getDate() + 1)

  if (date.toDateString() === today.toDateString()) return '今天'
  if (date.toDateString() === tomorrow.toDateString()) return '明天'

  const weekdays = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
  return weekdays[date.getDay()]
}

/** 加载数据 */
async function loadWeather() {
  loading.value = true
  loadFailed.value = false

  try {
    const [currentData, forecastRes] = await Promise.all([
      get<IWeatherCurrent>('/weather/current', undefined, { needAuth: false, showError: false }),
      get<{ forecasts: IWeatherForecast[] }>('/weather/forecast', undefined, { needAuth: false, showError: false }),
    ])

    if (currentData) {
      current.value = currentData
    }
    if (forecastRes && forecastRes.forecasts && Array.isArray(forecastRes.forecasts)) {
      forecast.value = forecastRes.forecasts.slice(0, 3)
    }
  } catch {
    loadFailed.value = true
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadWeather()
})
</script>

<style lang="scss" scoped>
.weather-card {
  margin: 24rpx 32rpx 0;
  background: linear-gradient(135deg, #e8f5e9 0%, #fff8e1 100%);
  border-radius: var(--radius-xl);
  overflow: hidden;
  box-shadow: var(--shadow-sm);

  &__skeleton {
    padding: 32rpx;
    display: flex;
    flex-direction: column;
    gap: 20rpx;
  }

  &__content {
    padding: 28rpx;
  }
}

.skeleton-bar {
  height: 28rpx;
  border-radius: var(--radius-sm);
  background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;

  &--lg { width: 60%; height: 48rpx; }
  &--sm { width: 40%; }
  &--md { width: 100%; }
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

.weather-current {
  display: flex;
  justify-content: space-between;
  align-items: center;

  &__left {
    display: flex;
    align-items: center;
    gap: 16rpx;
  }

  &__icon {
    font-size: 72rpx;
  }

  &__info {
    display: flex;
    flex-direction: column;
  }

  &__temp {
    font-size: 56rpx;
    font-weight: 700;
    color: var(--color-text);
    line-height: 1.1;
  }

  &__desc {
    font-size: var(--font-size-sm);
    color: var(--color-text-secondary);
    margin-top: 4rpx;
  }

  &__right {
    display: flex;
    flex-direction: column;
    gap: 6rpx;
  }

  &__detail {
    display: flex;
    align-items: center;
  }
}

.weather-detail__label {
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
}

.weather-tip {
  display: flex;
  align-items: center;
  gap: 10rpx;
  margin-top: 20rpx;
  padding: 16rpx 20rpx;
  border-radius: var(--radius-md);
  background-color: rgba(76, 175, 80, 0.12);

  &--good { background-color: rgba(76, 175, 80, 0.12); }
  &--warn { background-color: rgba(255, 152, 0, 0.12); }
  &--bad { background-color: rgba(229, 57, 53, 0.12); }

  &__icon {
    font-size: 32rpx;
  }

  &__text {
    font-size: var(--font-size-sm);
    color: var(--color-text);
    font-weight: 500;
  }
}

.weather-forecast {
  display: flex;
  gap: 16rpx;
  margin-top: 24rpx;
  white-space: nowrap;
}

.forecast-item {
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  min-width: 140rpx;
  padding: 16rpx 12rpx;
  background-color: rgba(255, 255, 255, 0.6);
  border-radius: var(--radius-md);
  flex-shrink: 0;

  &__date {
    font-size: var(--font-size-xs);
    color: var(--color-text-secondary);
    margin-bottom: 8rpx;
  }

  &__icon {
    font-size: 40rpx;
    margin-bottom: 6rpx;
  }

  &__weather {
    font-size: var(--font-size-xs);
    color: var(--color-text);
    margin-bottom: 4rpx;
  }

  &__temp {
    font-size: var(--font-size-xs);
    color: var(--color-text-secondary);
  }
}
</style>

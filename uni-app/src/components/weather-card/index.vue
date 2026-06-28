<template>
  <view class="weather-card">
    <!-- 加载骨架 -->
    <view class="weather-card__skeleton" v-if="loading">
      <view class="skeleton-bar skeleton-bar--lg" />
      <view class="skeleton-bar skeleton-bar--sm" />
      <view class="skeleton-bar skeleton-bar--md" />
    </view>

    <!-- 天气内容 -->
    <view class="weather-card__content" v-else>
      <view class="weather-unavailable" v-if="weatherUnavailable">
        <text class="weather-unavailable__icon">🌤️</text>
        <view class="weather-unavailable__body">
          <text class="weather-unavailable__title">天气暂不可用，请以现场天气为准</text>
          <text class="weather-unavailable__desc">出行前建议关注最新天气，备好防晒、防雨和保暖装备</text>
        </view>
      </view>

      <!-- 当前天气 -->
      <view class="weather-current" v-else>
        <view class="weather-current__left">
          <text class="weather-current__icon">{{ weatherEmoji }}</text>
          <view class="weather-current__info">
            <view class="weather-current__temp-row">
              <text class="weather-current__temp">{{ current.temperature }}</text>
              <text class="weather-current__degree">°C</text>
            </view>
            <text class="weather-current__desc">{{ current.description || current.weather }}</text>
          </view>
        </view>
        <view class="weather-current__right">
          <view class="weather-current__detail">
            <text class="weather-detail__icon">💨</text>
            <text class="weather-detail__label">{{ current.wind }}</text>
          </view>
          <view class="weather-current__detail">
            <text class="weather-detail__icon">💧</text>
            <text class="weather-detail__label">{{ current.humidity }}%</text>
          </view>
          <view class="weather-current__detail">
            <text class="weather-detail__icon">🌅</text>
            <text class="weather-detail__label">{{ current.sunrise }}</text>
          </view>
        </view>
      </view>

      <!-- 露营建议 -->
      <view class="weather-tip" :class="[`weather-tip--${tipLevel}`]">
        <text class="weather-tip__icon">{{ tipIcon }}</text>
        <text class="weather-tip__text">{{ tipText }}</text>
      </view>

      <!-- 未来几小时 -->
      <scroll-view class="weather-hourly" scroll-x enable-flex v-if="hourlyForecast.length > 0">
        <view
          class="hourly-item"
          v-for="item in hourlyForecast"
          :key="item.datetime"
        >
          <text class="hourly-item__time">{{ item.time }}</text>
          <text class="hourly-item__icon">{{ item.icon || getForecastEmoji(item.weather) }}</text>
          <text class="hourly-item__temp">{{ item.temperature }}°</text>
          <text class="hourly-item__rain" v-if="item.precipitation_probability > 0">{{ item.precipitation_probability }}%</text>
        </view>
      </scroll-view>

      <!-- 未来几天 -->
      <view class="weather-forecast" v-if="forecast.length > 0">
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
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { get } from '@/utils/request'
import type { IWeatherCurrent, IWeatherForecast, IWeatherForecastResponse, IWeatherHourlyForecast } from '@/types'

const loading = ref(true)
const weatherUnavailable = ref(false)

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
const hourlyForecast = ref<IWeatherHourlyForecast[]>([])

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
  weatherUnavailable.value = false

  try {
    const [currentData, forecastRes] = await Promise.all([
      get<IWeatherCurrent>('/weather/current', undefined, { needAuth: false, showError: false }),
      get<IWeatherForecastResponse>('/weather/forecast', undefined, { needAuth: false, showError: false }),
    ])

    if (currentData) {
      current.value = currentData
      hourlyForecast.value = (currentData.hourly_forecasts || []).slice(0, 6)
    }
    if (forecastRes && forecastRes.forecasts && Array.isArray(forecastRes.forecasts)) {
      forecast.value = forecastRes.forecasts.slice(0, 3)
    }
  } catch {
    weatherUnavailable.value = true
    forecast.value = []
    hourlyForecast.value = []
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
  background: linear-gradient(145deg, #eef5ed 0%, #f8f2e4 50%, #fdf5e8 100%);
  border-radius: var(--radius-xl);
  overflow: hidden;
  box-shadow: var(--shadow-md);
  border: 1rpx solid rgba(200, 168, 114, 0.12);
  position: relative;

  &::before {
    content: '';
    position: absolute;
    top: -20rpx;
    right: -20rpx;
    width: 160rpx;
    height: 160rpx;
    background: radial-gradient(circle, rgba(200, 168, 114, 0.08) 0%, transparent 70%);
    pointer-events: none;
  }

  &__skeleton {
    padding: 36rpx;
    display: flex;
    flex-direction: column;
    gap: 20rpx;
  }

  &__content {
    padding: 28rpx 32rpx;
  }
}

.skeleton-bar {
  height: 28rpx;
  border-radius: var(--radius-sm);
  background: linear-gradient(110deg, var(--color-bg-light) 0%, var(--color-bg-warm) 30%, var(--color-bg-light) 60%);
  background-size: 300% 100%;
  animation: shimmer 2s infinite ease-in-out;

  &--lg { width: 60%; height: 48rpx; }
  &--sm { width: 40%; }
  &--md { width: 100%; }
}

@keyframes shimmer {
  0% { background-position: 300% 0; }
  100% { background-position: -300% 0; }
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
    filter: drop-shadow(0 2rpx 4rpx rgba(0, 0, 0, 0.1));
  }

  &__info {
    display: flex;
    flex-direction: column;
  }

  &__temp-row {
    display: flex;
    align-items: flex-start;
  }

  &__temp {
    font-size: 56rpx;
    font-weight: 800;
    color: var(--color-text);
    line-height: 1;
    letter-spacing: 2rpx;
  }

  &__degree {
    font-size: var(--font-size-sm);
    color: var(--color-text-secondary);
    font-weight: 500;
    margin-top: 8rpx;
    margin-left: 2rpx;
  }

  &__desc {
    font-size: var(--font-size-sm);
    color: var(--color-text-secondary);
    margin-top: 6rpx;
    letter-spacing: 1rpx;
  }

  &__right {
    display: flex;
    flex-direction: column;
    gap: 8rpx;
  }

  &__detail {
    display: flex;
    align-items: center;
    gap: 6rpx;
  }
}

.weather-unavailable {
  display: flex;
  align-items: center;
  gap: 18rpx;
  min-height: 156rpx;

  &__icon {
    width: 92rpx;
    height: 92rpx;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    border-radius: var(--radius-lg);
    background: rgba(255, 255, 255, 0.62);
    font-size: 46rpx;
  }

  &__body {
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 8rpx;
  }

  &__title {
    font-size: var(--font-size-base);
    color: var(--color-text);
    font-weight: 700;
    line-height: 1.35;
  }

  &__desc {
    font-size: var(--font-size-xs);
    color: var(--color-text-secondary);
    line-height: 1.5;
  }
}

.weather-detail {
  &__icon {
    font-size: 20rpx;
  }

  &__label {
    font-size: var(--font-size-xs);
    color: var(--color-text-secondary);
    letter-spacing: 0.5rpx;
  }
}

.weather-tip {
  display: flex;
  align-items: center;
  gap: 12rpx;
  margin-top: 24rpx;
  padding: 16rpx 24rpx;
  border-radius: var(--radius-lg);

  &--good {
    background: linear-gradient(135deg, rgba(90, 158, 111, 0.1), rgba(90, 158, 111, 0.05));
    border: 1rpx solid rgba(90, 158, 111, 0.15);
  }

  &--warn {
    background: linear-gradient(135deg, rgba(212, 165, 53, 0.1), rgba(212, 165, 53, 0.05));
    border: 1rpx solid rgba(212, 165, 53, 0.15);
  }

  &--bad {
    background: linear-gradient(135deg, rgba(196, 92, 74, 0.1), rgba(196, 92, 74, 0.05));
    border: 1rpx solid rgba(196, 92, 74, 0.15);
  }

  &__icon {
    font-size: 32rpx;
  }

  &__text {
    font-size: var(--font-size-sm);
    color: var(--color-text);
    font-weight: 500;
    letter-spacing: 1rpx;
  }
}

.weather-forecast {
  display: flex;
  gap: 12rpx;
  margin-top: 24rpx;
  justify-content: center;
  width: 100%;
}

.weather-hourly {
  display: flex;
  gap: 12rpx;
  margin-top: 20rpx;
  white-space: nowrap;
}

.hourly-item {
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  min-width: 106rpx;
  padding: 14rpx 10rpx;
  background: rgba(45, 74, 62, 0.06);
  border: 1rpx solid rgba(45, 74, 62, 0.08);
  border-radius: var(--radius-md);
  flex-shrink: 0;

  &__time {
    font-size: 20rpx;
    color: var(--color-text-secondary);
    margin-bottom: 6rpx;
  }

  &__icon {
    font-size: 34rpx;
    line-height: 1;
    margin-bottom: 6rpx;
  }

  &__temp {
    font-size: 24rpx;
    color: var(--color-text);
    font-weight: 700;
  }

  &__rain {
    font-size: 18rpx;
    color: var(--color-accent);
    margin-top: 2rpx;
  }
}

.forecast-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 160rpx;
  min-height: 196rpx;
  padding: 18rpx 14rpx;
  background: rgba(255, 255, 255, 0.65);
  backdrop-filter: blur(10px);
  border-radius: var(--radius-lg);
  border: 1rpx solid rgba(255, 255, 255, 0.8);
  box-sizing: border-box;

  &__date {
    font-size: var(--font-size-xs);
    color: var(--color-text-secondary);
    margin-bottom: 8rpx;
    font-weight: 500;
    letter-spacing: 1rpx;
  }

  &__icon {
    font-size: 40rpx;
    margin-bottom: 6rpx;
  }

  &__weather {
    font-size: var(--font-size-xs);
    color: var(--color-text);
    margin-bottom: 4rpx;
    font-weight: 500;
  }

  &__temp {
    font-size: var(--font-size-xs);
    color: var(--color-text-placeholder);
  }
}
</style>

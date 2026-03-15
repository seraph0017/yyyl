// 天气 API
import { get } from '@/utils/request'

export function getCurrentWeather() {
  return get<{ code: number; data: object }>('/weather/current')
}

export function getWeatherForecast() {
  return get<{ code: number; data: object }>('/weather/forecast')
}

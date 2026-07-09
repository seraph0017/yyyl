import type { ProductCategory } from '@/types'

export function normalizeProductCategory(
  type: string | undefined | null,
  category?: string | undefined | null,
): ProductCategory {
  const rawCategory = type || category || 'daily_camping'
  if (rawCategory === 'rental') return 'equipment_rental'
  if (rawCategory === 'shop') return 'camp_shop'
  return rawCategory as ProductCategory
}

export function isCampsiteProduct(category: ProductCategory | string | undefined | null): boolean {
  return category === 'daily_camping' || category === 'event_camping'
}

export function isDateBookingProduct(category: ProductCategory | string | undefined | null): boolean {
  return isCampsiteProduct(category) || isActivityProduct(category) || category === 'equipment_rental'
}

export function isRetailProduct(category: ProductCategory | string | undefined | null): boolean {
  return category === 'camp_shop' || category === 'merchandise'
}

export function isActivityProduct(category: ProductCategory | string | undefined | null): boolean {
  return category === 'daily_activity' || category === 'special_activity'
}

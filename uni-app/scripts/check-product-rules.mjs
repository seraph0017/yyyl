import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { join, resolve } from 'node:path'

const rootDir = resolve(new URL('..', import.meta.url).pathname)
const rulesPath = join(rootDir, 'src/utils/product-rules.ts')
const productRulesSource = readFileSync(rulesPath, 'utf8')
const homeSource = readFileSync(join(rootDir, 'src/components/default-home-page/index.vue'), 'utf8')
const orderConfirmSource = readFileSync(join(rootDir, 'src/pages/order-confirm/index.vue'), 'utf8')
const categorySource = readFileSync(join(rootDir, 'src/pages/category/index.vue'), 'utf8')
const detailSource = readFileSync(join(rootDir, 'src/pages/product-detail/index.vue'), 'utf8')
const cmsProductListSource = readFileSync(join(rootDir, 'src/components/cms/CmsProductList.vue'), 'utf8')

assert.match(productRulesSource, /export function normalizeProductCategory/)
assert.match(productRulesSource, /const rawCategory = type \|\| category \|\| 'daily_camping'/)
assert.match(productRulesSource, /export function isCampsiteProduct/)
assert.match(productRulesSource, /daily_camping/)
assert.match(productRulesSource, /event_camping/)
assert.doesNotMatch(productRulesSource, /equipment_rental['"][,\)]\s*\|\|/)
assert.doesNotMatch(productRulesSource, /daily_activity['"][,\)]\s*\|\|/)
assert.doesNotMatch(productRulesSource, /special_activity['"][,\)]\s*\|\|/)

assert.match(homeSource, /savePendingCategoryKey/)
assert.match(homeSource, /savePendingCategoryKey\(_key\)/)

for (const source of [homeSource, orderConfirmSource, categorySource, detailSource, cmsProductListSource]) {
  assert.match(source, /normalizeProductCategory/)
  assert.doesNotMatch(source, /category \|\| .*type/)
}

assert.match(orderConfirmSource, /showIdentitySection/)
assert.match(orderConfirmSource, /v-if="product && showIdentitySection"/)
assert.match(orderConfirmSource, /if \(p && showIdentitySection\.value && p\.identity_mode === 'required' && !selectedIdentity\.value\)/)
assert.match(orderConfirmSource, /if \(showIdentitySection\.value && selectedIdentity\.value\)/)

console.log('product-rules OK')

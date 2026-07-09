import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { test } from 'node:test'
import vm from 'node:vm'
import ts from 'typescript'
import { PNG } from 'pngjs'
import QrCode from 'qrcode-reader'

const productDetailPath = new URL('../src/pages/product-detail/index.vue', import.meta.url)
const orderConfirmPath = new URL('../src/pages/order-confirm/index.vue', import.meta.url)
const identityPath = new URL('../src/pages/identity/index.vue', import.meta.url)
const addressPath = new URL('../src/pages/address/index.vue', import.meta.url)
const orderPath = new URL('../src/pages/order/index.vue', import.meta.url)
const orderDetailPath = new URL('../src/pages/order-detail/index.vue', import.meta.url)
const cartPath = new URL('../src/pages/cart/index.vue', import.meta.url)
const memberPath = new URL('../src/pages/member/index.vue', import.meta.url)
const minePath = new URL('../src/pages/mine/index.vue', import.meta.url)
const authPath = new URL('../src/utils/auth.ts', import.meta.url)
const typesPath = new URL('../src/types/index.ts', import.meta.url)
const campMapPath = new URL('../src/pages-sub/product/camp-map/index.vue', import.meta.url)
const analyticsPath = new URL('../src/utils/analytics.ts', import.meta.url)
const cmsPagePath = new URL('../src/pages/cms-page/index.vue', import.meta.url)
const staffPath = new URL('../src/pages/staff/index.vue', import.meta.url)
const ticketPath = new URL('../src/pages/ticket/index.vue', import.meta.url)
const qrCodePath = new URL('../src/utils/qrcode.ts', import.meta.url)
const customerServicePath = new URL('../src/pages/customer-service/index.vue', import.meta.url)
const defaultHomePagePath = new URL('../src/components/default-home-page/index.vue', import.meta.url)
const weatherCardPath = new URL('../src/components/weather-card/index.vue', import.meta.url)
const requestUtilPath = new URL('../src/utils/request.ts', import.meta.url)
const productRulesPath = new URL('../src/utils/product-rules.ts', import.meta.url)
const cmsImagePath = new URL('../src/components/cms/CmsImage.vue', import.meta.url)
const cmsImageTextPath = new URL('../src/components/cms/CmsImageText.vue', import.meta.url)
const cmsProductListPath = new URL('../src/components/cms/CmsProductList.vue', import.meta.url)
const cmsNoticePath = new URL('../src/components/cms/CmsNotice.vue', import.meta.url)
const cmsNavPath = new URL('../src/components/cms/CmsNav.vue', import.meta.url)
const cmsDividerPath = new URL('../src/components/cms/CmsDivider.vue', import.meta.url)
const cmsLinkPath = new URL('../src/utils/cms-link.ts', import.meta.url)
const cmsTypesPath = new URL('../src/types/cms.ts', import.meta.url)

test('product detail no longer uses fake calendar stock or fixed camping prices', async () => {
  const source = await readFile(productDetailPath, 'utf8')

  assert.ok(!source.includes('Math.random()'), '商品详情页不应再使用 Math.random() 生成库存')
  assert.ok(!source.includes('price: isWeekend ? 168 : 128'), '商品详情页不应再写死周末/工作日价格')
  assert.match(source, /price-calendar|quote/i, '商品详情页应接入后端价格/库存数据')
  assert.match(source, /selectedSkuId\.value \? \{ sku_id: selectedSkuId\.value \} : \{\}/, '价格日历请求应携带已选 SKU，支持 SKU 级共享库存')
  assert.match(source, /validateSelectedDateRange/, '商品详情页应逐日校验选择范围内库存')
  assert.match(source, /getCalendarPriceForDate/, '商品详情页合计价应基于价格日历映射')
})

test('product detail can resolve legacy product qrcode scene directly', async () => {
  const source = await readFile(productDetailPath, 'utf8')

  assert.match(source, /options\?\.scene/, '商品详情页应识别小程序码 scene 参数')
  assert.match(source, /safeDecodeQrcodeScene/, '商品详情页应安全解码 scene')
  assert.match(source, /resolveQrcode\(scene\)/, '旧码直达商品详情页时应调用二维码解析接口')
  assert.match(source, /saveQrcodeAttribution\(data\)/, '扫码进入商品详情仍应保存来源归因')
  assert.match(source, /data\.target_type === 'product' \|\| data\.target_type === 'activity_product'/, '商品二维码应按目标类型加载商品')
  assert.match(source, /await loadProduct\(productId\)/, '解析到商品 ID 后应直接加载对应商品，而不是回退默认商品')
})

test('order confirm must call backend quote before submit', async () => {
  const source = await readFile(orderConfirmPath, 'utf8')

  assert.match(source, /\/orders\/quote/, '订单确认页应调用后端报价接口')
  assert.match(source, /\/cart\/checkout/, '购物车路径应调用购物车结算接口')
  assert.match(source, /\/cart\/quote/, '购物车确认页应调用后端购物车报价接口')
  assert.match(source, /\/cart\/quote'[\s\S]*disclaimer_signed: disclaimerSigned\.value/, '购物车报价应带免责声明签署状态')
  assert.match(source, /\/cart\/checkout'[\s\S]*disclaimer_signed: disclaimerSigned\.value/, '购物车结算应带免责声明签署状态')
  assert.match(source, /applyCartQuote/, '购物车确认页应以服务端报价刷新金额和库存')
  assert.ok(!source.includes("Math.floor(total * 0.2)"), '订单确认页不应前端硬算折扣')
  assert.ok(!source.includes("total = p.current_price * billableUnits"), '订单确认页不应自行计算最终金额')
  assert.ok(!source.includes("orderData.from = 'cart'"), '购物车路径不应把 from=cart 发给普通订单接口')
})

test('order confirm consumes temporary token and claims onsite order', async () => {
  const source = await readFile(orderConfirmPath, 'utf8')

  assert.match(source, /temporaryToken/, '订单确认页应维护 temporary_token 状态')
  assert.match(source, /safeDecodeTemporaryToken/, '订单确认页应安全解码小程序码 scene')
  assert.match(source, /decodeURIComponent\(raw\)/, '订单确认页应解码小程序码 scene')
  assert.match(source, /temporaryClaimError\.value = '临时收款码参数无效'/, 'scene 解码失败应进入临时单错误态')
  assert.match(source, /hasTemporaryTokenParam/, '存在 scene/temporary_token 时即使解码失败也应保持临时单页面态')
  assert.match(source, /from\.value = hasTemporaryTokenParam \? 'temporary' : \(options\?\.from \|\| 'direct'\)/, '坏 scene 不应回退为普通直购页')
  assert.match(source, /ensureUserPhoneBeforeTemporaryClaim/, '扫码临时单应先完成手机号校验再认领')
  assert.match(source, /encodeURIComponent\(temporaryToken\.value\)/, '认领接口应编码 token')
  assert.match(source, /\/orders\/temporary\/\$\{encodeURIComponent\(temporaryToken\.value\)\}\/claim/, '订单确认页应调用临时单认领接口')
  assert.match(source, /applyTemporaryOrderClaim/, '订单确认页应将认领后的正式订单映射为待支付订单')
  assert.match(source, /temporaryClaimedOrder/, '订单确认页应保存认领后的订单')
  assert.match(source, /temporaryClaimError/, '临时单失败应进入明确错误态')
  assert.match(source, /临时收款码不可用/, '临时单失败页应有明确提示')
  assert.match(source, /现场临时订单/, '临时单确认页应有可识别标题')
  assert.match(source, /order_id=\$\{temporaryClaimedOrder\.value\.id\}/, '临时单提交后应进入支付页')
  assert.match(source, /encodeURIComponent\(temporaryClaimedOrder\.value\.order_no\)/, '支付跳转参数应编码')
})

test('cart page normalizes backend cart response shape', async () => {
  const source = await readFile(cartPath, 'utf8')

  assert.match(source, /CartListResponse/, '购物车页应声明并使用后端 { items, summary } 响应')
  assert.match(source, /\.items\s*\|\|\s*\[\]/, '购物车页应从响应 items 读取列表')
  assert.match(source, /item\.image/, '购物车页应兼容后端 image 字段')
  assert.match(source, /item\.checked/, '购物车页应兼容后端 checked 字段')
  assert.match(source, /item\.stock_available/, '购物车页应兼容后端 stock_available 字段')
  assert.match(source, /item\.stock/, '购物车页应使用后端真实 stock 字段')
  assert.match(source, /uni\.showModal\(\{[\s\S]*title:\s*'免责声明'/, '购物车结算应先展示免责声明确认')
  assert.match(source, /confirmText:\s*'已阅读并同意'/, '购物车免责声明确认按钮应清楚表达同意')
  assert.match(source, /if \(res\.confirm\)[\s\S]*disclaimer_signed=1/, '购物车只有用户确认免责声明后才应携带已签署状态')
  assert.doesNotMatch(source, /stock:\s*item\.stock_available === false \? item\.quantity : 999/, '购物车页不应使用 999 作为假库存上限')
  assert.doesNotMatch(source, /get<ICartItem\[]>\('\/cart\/'\)/, '购物车页不应把响应直接当数组处理')
})

test('product detail must call real add-cart API for retail products', async () => {
  const source = await readFile(productDetailPath, 'utf8')

  assert.match(source, /post<[^>]*>\('\/cart\/items'/, '商品详情加入购物车应调用 POST /cart/items')
  assert.match(source, /sku_id/, '加入购物车 payload 应支持 SKU 字段')
  assert.match(source, /selectedSkuId/, '商品详情应维护已选 SKU')
  assert.match(source, /skuOptions/, '商品详情应展示可选 SKU')
  assert.doesNotMatch(source, /<view class="detail-sku" v-if="skuOptions\.length > 0">[\s\S]*<view class="detail-quantity__control">/, 'SKU 选择器不应被零售商品数量区包住')
  assert.match(source, /loadedCalendarMonths\.value = \{\}/, '切换 SKU 后应清理价格日历缓存')
  assert.match(source, /loadPriceCalendarForCurrentMonth\(true\)/, '切换 SKU 后应强制刷新当前月日历')
  assert.match(source, /selectedDates\.value = \[\]/, '切换 SKU 后应清空或重校验已选日期')
  assert.match(source, /generateCalendar\(\)/, '切换 SKU 后应刷新日历 UI')
  const addCartBody = source.slice(source.indexOf('async function onAddToCart'), source.indexOf('/** 立即预定 */'))
  assert.ok(addCartBody.indexOf("await post<unknown>('/cart/items'") < addCartBody.indexOf("uni.showToast({ title: '已加入购物车'"), '成功提示必须发生在真实加购接口之后')
  assert.match(addCartBody, /sku_id:\s*selectedSkuId\.value/, '加入购物车应提交已选 SKU')
})

test('product detail uses product-aware price unit and has stable sku option styles', async () => {
  const source = await readFile(productDetailPath, 'utf8')

  assert.match(source, /:unit="priceUnit"/, '商品详情价格单位不应固定为 /晚')
  assert.match(source, /const priceUnit = computed/, '商品详情应按商品类型计算价格单位')
  assert.match(source, /\.detail-sku\s*\{/, 'SKU 区域应有独立布局样式')
  assert.match(source, /\.detail-sku__item\s*\{/, 'SKU 选项应有基础样式')
  assert.match(source, /\.detail-sku__item--active\s*\{/, 'SKU 选中态应有样式')
  assert.match(source, /\.detail-sku__item--disabled\s*\{/, 'SKU 禁用态应有样式')
})

test('camping sku selection is driven by calendar stock instead of static sku stock', async () => {
  const source = await readFile(productDetailPath, 'utf8')
  const types = await readFile(typesPath, 'utf8')
  const orderConfirmSource = await readFile(orderConfirmPath, 'utf8')

  assert.match(source, /isSkuOptionDisabled/, '商品详情应集中判断 SKU 是否禁用')
  assert.match(source, /sku\.status !== 'active'/, '下架 SKU 应禁用，避免选中后价格日历静默失败')
  assert.match(source, /getSkuAvailableStock\(sku,\s*product\.value \|\| undefined\) <= 0/, 'SKU 禁用应优先使用当前可用库存')
  assert.match(source, /isSkuOptionDisabled\(sku\)/, '模板和点击逻辑应复用 SKU 禁用判断')
  assert.match(source, /selectedSku\.value && isSkuOptionDisabled\(selectedSku\.value\)/, '立即预定前应拦截售罄或停用 SKU')
  assert.match(source, /isRetailProduct\(p\.category\) && p\.stock <= 0/, '零售商品售罄时不应进入下单链路')
  assert.doesNotMatch(source, /!sku \|\| sku\.stock <= 0/, '营位商品不应因静态 SKU stock=0 阻止切换规格')
  assert.match(types, /inventory_mode\?:\s*'independent' \| 'shared_product' \| string/, '小程序 SKU 类型应声明库存模式')
  assert.match(types, /inventory_pool_id\?:\s*number \| null/, '小程序 SKU 类型应声明共享库存池 ID')
  assert.match(types, /inventory_pool_available\?:\s*number \| null/, '小程序 SKU 类型应声明共享池可用库存')
  assert.match(source, /inventory_mode:\s*sku\.inventory_mode \|\| 'independent'/, '商品详情应保留后端 SKU 库存模式')
  assert.match(source, /inventory_pool_available:\s*sku\.inventory_pool_available \?\? null/, '商品详情应保留共享池可用库存')
  assert.match(source, /function getSkuAvailableStock/, '商品详情应集中计算 SKU 当前可用库存')
  assert.match(source, /inventory_pool_available \?\? fallbackProduct\?\.stock \?\? sku\.stock/, '共享 SKU 应优先使用共享池库存，缺失时才回退')
  assert.match(orderConfirmSource, /resolveSkuAvailableStock\(selectedSku,\s*Number\(raw\.stock \|\| 0\)\)/, '订单确认页直购应使用共享 SKU 可用库存')
  assert.match(orderConfirmSource, /sku\.inventory_mode === 'shared_product' \|\| sku\.inventory_pool_id/, '订单确认页应识别共享库存 SKU')
})

test('order confirm submit disables request-layer toast for quote and submit errors', async () => {
  const source = await readFile(orderConfirmPath, 'utf8')

  assert.match(source, /await refreshQuote\(false\)/, '直购提交前报价预校验应关闭请求层 toast，由 catch 统一展示')
  assert.match(source, /\/cart\/checkout[\s\S]*\{\s*showError:\s*false\s*\}/, '购物车提交应关闭请求层错误 toast')
  assert.match(source, /\/orders[\s\S]*\{\s*showError:\s*false\s*\}/, '直购提交应关闭请求层错误 toast')
  assert.match(source, /encodeURIComponent\(orderDetail\.order_no \|\| checkout\.order_no\)/, '购物车单订单支付跳转应编码订单号')
  assert.match(source, /encodeURIComponent\(result\.order_no\)/, '直购支付跳转应编码订单号')
  assert.match(source, /p && isRetailProduct\(p\.category\) && p\.stock <= 0/, '订单确认页提交前应兜底拦截售罄零售商品')
})

test('date booking products must choose a date before next step and submit', async () => {
  const productSource = await readFile(productDetailPath, 'utf8')
  const confirmSource = await readFile(orderConfirmPath, 'utf8')
  const rulesSource = await readFile(productRulesPath, 'utf8')

  assert.match(rulesSource, /category === 'equipment_rental'/, '装备租赁也属于必须选择日期的预订商品')
  const onBookBody = productSource.slice(productSource.indexOf('function onBook()'), productSource.indexOf('/** 联系客服 */'))
  assert.match(onBookBody, /isDateBookingProduct\(p\.category\) && selectedDates\.value\.length === 0[\s\S]*请先选择日期/, '详情页下一步前必须先选择日期')
  assert.ok(onBookBody.indexOf('selectedDates.value.length === 0') < onBookBody.indexOf('uni.navigateTo'), '日期必选校验必须发生在跳转订单确认页之前')
  assert.match(confirmSource, /isDateBookingProduct\(p\.category\) && dates\.value\.length === 0[\s\S]*请选择预约日期/, '确认页提交前必须兜底校验预约日期')
  assert.match(confirmSource, /isDateBookingProduct\(product\.value\.category\) && dates\.value\.length === 0[\s\S]*return null/, '报价前无日期时不应调用报价接口')
})

test('identity form handles masked server fields without resubmitting asterisks', async () => {
  const identitySource = await readFile(identityPath, 'utf8')
  const confirmSource = await readFile(orderConfirmPath, 'utf8')

  assert.match(identitySource, /id_card_masked/, '出行人列表应消费后端身份证脱敏字段')
  assert.match(identitySource, /formData\.id_card = isMaskedValue\(item\.id_card\) \? '' : \(item\.id_card \|\| ''\)/, '编辑时不应把带星号的身份证回填提交')
  assert.match(identitySource, /请重新输入完整身份证号/, '编辑脱敏身份证时应提示重新输入完整号码')
  assert.match(identitySource, /if \(!editingId\.value \|\| formData\.id_card\)/, '新增出行人必须填写身份证；编辑时未重填身份证不应阻塞保存')
  assert.match(identitySource, /if \(formData\.id_card\) payload\.id_card = formData\.id_card/, '编辑出行人时只有重新输入完整身份证才提交 id_card')
  assert.match(identitySource, /if \(formData\.phone\) payload\.phone = formData\.phone/, '编辑出行人时只有重新输入完整手机号才提交 phone')
  assert.match(confirmSource, /id_card_masked/, '订单确认页选择出行人时应展示后端脱敏身份证')
  assert.match(confirmSource, /await loadIdentities\(\)/, '从出行人页返回订单确认页后应刷新出行人列表')
})

test('order confirm initial quote errors are shown once with backend message', async () => {
  const source = await readFile(orderConfirmPath, 'utf8')

  assert.match(source, /await refreshQuote\(false\)/, '首屏直购报价应关闭请求层 toast')
  assert.match(source, /\/cart\/quote[\s\S]*\{\s*showError:\s*false\s*\}/, '首屏购物车报价应关闭请求层 toast')
  assert.match(source, /\/orders\/\$\{firstOrderId\}[\s\S]*\{\s*showError:\s*false\s*\}/, '订单详情回查应关闭请求层错误 toast，避免重复提示')
  assert.match(source, /catch \(err: any\)[\s\S]*err\?\.message \|\| '加载数据失败'/, '首屏加载失败应由页面统一展示后端错误')
})

test('product detail sku calendar reload failure gives user feedback', async () => {
  const source = await readFile(productDetailPath, 'utf8')

  assert.doesNotMatch(source, /loadPriceCalendarForCurrentMonth\(true\)\.catch\(\(\) => \{\}\)/, 'SKU 切换刷新日历失败不应静默吞掉')
  assert.match(source, /规格日历加载失败，请稍后重试/, 'SKU 切换刷新日历失败应有轻提示')
})

test('direct order confirm shows real product image and sku spec instead of camping placeholder', async () => {
  const source = await readFile(orderConfirmPath, 'utf8')

  assert.doesNotMatch(source, /<text>营<\/text>/, '直购确认页不应使用固定“营”占位')
  assert.match(source, /directProductImage/, '直购确认页应展示商品或 SKU 图片')
  assert.match(source, /selectedSkuLabel/, '直购确认页应展示已选 SKU 规格')
  assert.match(source, /resolveProductImage|resolveImageUrl/, '直购确认页应解析后端商品图片')
})

test('activity booking selects time slot and submits it through quote and order payload', async () => {
  const productSource = await readFile(productDetailPath, 'utf8')
  const confirmSource = await readFile(orderConfirmPath, 'utf8')

  assert.match(productSource, /isActivityProduct/, '商品详情应识别活动类商品')
  assert.match(productSource, /isDateBookingProduct/, '活动和营位应共用日期预订判断')
  assert.match(productSource, /v-if="isDateBookingProduct\(product\.category\)"/, '活动商品也应展示日期选择')
  assert.match(productSource, /if \(isDateBookingProduct\(p\.category\)\)[\s\S]*loadPriceCalendarForCurrentMonth/, '活动商品也应加载价格库存日历')
  assert.match(productSource, /isDateBookingProduct\(p\.category\) && selectedDates\.value\.length === 0/, '活动下单前应要求选择预约日期')
  assert.match(productSource, /const dateQuery = isDateBookingProduct\(p\.category\) \? selectedDates\.value\.join\(','\) : ''/, '活动跳转确认页时应携带预约日期')
  assert.match(productSource, /activitySlotOptions/, '商品详情应将活动 time_slots 映射成可选场次')
  assert.match(productSource, /selectedActivitySlot/, '商品详情应维护已选活动场次')
  assert.match(productSource, /请选择预约时间/, '活动有多个场次时应要求用户选择预约时间')
  assert.match(productSource, /time_slot=\$\{encodeURIComponent\(selectedActivitySlot\.value\)\}/, '跳转确认页时应携带编码后的 time_slot')

  assert.match(confirmSource, /activityTimeSlot/, '订单确认页应维护直购活动场次')
  assert.match(confirmSource, /options\?\.time_slot/, '订单确认页应读取详情页传入的 time_slot')
  assert.match(confirmSource, /预约时间：\{\{ activityTimeSlot \}\}/, '订单确认页应展示活动预约时间')
  assert.match(confirmSource, /dates:\s*isDateBookingProduct\(p\.category\) \? dates\.value : \[\]/, '订单确认页应给活动和营位提交预约日期')
  assert.match(confirmSource, /if \(!isDateBookingProduct\(p\.category\)\)[\s\S]*dates\.value = \[\]/, '订单确认页加载活动商品后不应清空详情页传入的预约日期')
  assert.doesNotMatch(confirmSource, /if \(!isCampsiteProduct\(p\.category\)\)[\s\S]{0,80}dates\.value = \[\]/, '订单确认页不应把活动商品当作无日期商品清空 dates')
  assert.match(confirmSource, /item\.time_slot = activityTimeSlot\.value/, '报价和提交订单 payload 应携带活动 time_slot')
  assert.match(productSource, /isActivityProduct\(product\.value\?\.category\)[\s\S]*selectedDates\.value = \[date\]/, '活动商品日历应支持单日选择，而不是住宿离店范围')
  assert.match(productSource, /isActivityProduct\(product\.category\) && selectedDates\.length > 0/, '活动商品日期区域应展示单日活动日期')
  assert.match(productSource, /if \(!isActivityProduct\(product\.value\?\.category\) && checkInDate\.value && !checkOutDate\.value\)/, '活动单日选择后确认日历不应再要求离店日期')
  assert.match(productSource, /isActivityProduct\(p\.category\) && selectedActivitySlot\.value \? \{ time_slot: selectedActivitySlot\.value \} : \{\}/, '活动价格库存日历请求应携带已选场次')
  assert.match(productSource, /const monthKey = `\$\{year\}-\$\{String\(month\)\.padStart\(2, '0'\)\}:\$\{selectedSkuId\.value \|\| 0\}:\$\{selectedActivitySlot\.value \|\| ''\}`/, '价格日历缓存应按 SKU 和活动场次隔离')
  assert.match(productSource, /async function onSelectActivitySlot\(slot: string\)[\s\S]*selectedDates\.value = \[\][\s\S]*loadedCalendarMonths\.value = \{\}[\s\S]*priceCalendarMap\.value = \{\}[\s\S]*await loadPriceCalendarForCurrentMonth\(true\)/, '切换活动场次应清空旧日期并重载该场次库存日历')
})

test('address selection and save flow are miniapp-safe', async () => {
  const confirmSource = await readFile(orderConfirmPath, 'utf8')
  const addressSource = await readFile(addressPath, 'utf8')

  assert.doesNotMatch(confirmSource, /URLSearchParams/, '微信小程序地址选择不应依赖浏览器 URLSearchParams')
  assert.match(confirmSource, /url:\s*'\/pages\/address\/index\?action=select'/, '选择地址应使用固定小程序页面参数')
  assert.match(addressSource, /getOpenerEventChannel\?\.\(\)\.emit\?\.\('select', item\)/, '地址页应通过 event channel 回传所选地址')
  assert.match(addressSource, /if \(saving\.value\) return/, '地址保存应防止重复提交')
  assert.match(addressSource, /手机号已脱敏，修改需重新输入完整手机号/, '编辑脱敏手机号时应有明确提示')
})

test('cart and cart checkout show backend sku specs for multi-sku items', async () => {
  const cartSource = await readFile(cartPath, 'utf8')
  const confirmSource = await readFile(orderConfirmPath, 'utf8')

  assert.match(cartSource, /sku_spec_values/, '购物车页应映射后端 SKU 规格字段')
  assert.match(cartSource, /formatSkuLabel\(item\.sku_spec_values\)/, '购物车页应展示 SKU 规格文案')
  assert.match(confirmSource, /sku_spec_values/, '购物车确认页应保留 SKU 规格字段')
  assert.match(confirmSource, /formatSkuLabel\(item\.sku_spec_values\)/, '购物车确认页应展示 SKU 规格文案')
})

test('cart order confirm must show selected items and totals before checkout', async () => {
  const source = await readFile(orderConfirmPath, 'utf8')

  assert.match(source, /cartProducts/, '购物车确认页应维护商品列表用于核对')
  assert.match(source, /loadCartCheckoutPreview/, '购物车确认页应加载购物车预览')
  assert.match(source, /item_ids/, '购物车确认页应按选中 item_ids 过滤预览')
  assert.match(source, /uni\.switchTab\(\{\s*url:\s*'\/pages\/order\/index'/, '购物车拆单后应 switchTab 到订单 tabBar 页面')
  assert.doesNotMatch(source, /uni\.redirectTo\(\{\s*url:\s*'\/pages\/order\/index'/, '购物车拆单后不应 redirectTo tabBar 页面')
  assert.doesNotMatch(source, /totalPrice\.value = 0[\s\S]*return/, '购物车确认页不应直接置零返回')
})

test('checkout date that is sold out should not show sold-out conflict label', async () => {
  const source = await readFile(productDetailPath, 'utf8')

  assert.match(source, /canUseAsCheckoutDate/, '日历应区分离店日边界')
  assert.match(source, /!canUseAsCheckoutDate\(item\)">售罄/, '合法离店日不应同时显示售罄文案')
})

test('phone authorization prompt switches to mine tab page', async () => {
  const source = await readFile(orderConfirmPath, 'utf8')
  const auth = await readFile(authPath, 'utf8')

  assert.match(source, /uni\.switchTab\(\{\s*url:\s*'\/pages\/mine\/index'/, '手机号授权入口应使用 switchTab 跳转 tabBar 我的页')
  assert.doesNotMatch(source, /uni\.navigateTo\(\{\s*url:\s*'\/pages\/mine\/index'/, '不应 navigateTo tabBar 页面')
  assert.match(auth, /uni\.switchTab\(\{\s*url:\s*'\/pages\/mine\/index'/, 'auth.requireLogin 应使用 switchTab 跳转 tabBar 我的页')
  assert.doesNotMatch(auth, /uni\.navigateTo\(\{\s*url:\s*'\/pages\/mine\/index'/, 'auth.requireLogin 不应 navigateTo tabBar 页面')
})

test('mine page requires phone authorization for login and missing phone binding', async () => {
  const source = await readFile(minePath, 'utf8')

  assert.match(source, /open-type="getPhoneNumber"/, '我的页登录入口应使用微信手机号授权')
  assert.match(source, /@getphonenumber="onPhoneLogin"/, '手机号授权按钮应接入 onPhoneLogin')
  assert.match(source, /v-if="!userStore\.userInfo\.phone"/, '已登录但缺少手机号时应展示补授权入口')
  assert.match(source, /phoneLogin\(e\)/, '手机号授权应调用真实 phoneLogin 服务')
  assert.doesNotMatch(source, /@tap="onLogin"/, '我的页不应保留绕过手机号授权的普通登录按钮')
  assert.doesNotMatch(source, /wxLogin/, '我的页不应通过静默登录绕过手机号选择')
})

test('order confirm should inspect logged-in phone before submitting', async () => {
  const source = await readFile(orderConfirmPath, 'utf8')

  assert.match(source, /getUserInfo|phone/i, '订单确认页应读取已登录用户手机号')
})

test('order list and detail render sku specs date time quantity and remarks', async () => {
  const listSource = await readFile(orderPath, 'utf8')
  const detailSource = await readFile(orderDetailPath, 'utf8')

  assert.match(listSource, /formatOrderPhone\(order\)/, '订单列表应展示用户手机号或脱敏手机号')
  assert.match(listSource, /user_phone_masked \|\| order\.user_phone/, '订单列表手机号应优先使用脱敏手机号')
  assert.match(listSource, /formatOrderPaymentTime\(order\)/, '订单列表应展示后端实际支付时间')
  assert.match(listSource, /order\.payment_time \? formatOrderDate\(order\.payment_time\) : '未支付'/, '订单列表支付时间应使用 payment_time 而非 created_at')
  assert.match(listSource, /formatOrderRemark\(order\)/, '订单列表应展示订单备注')
  assert.match(listSource, /formatSkuSpecLabel\(item\.sku_spec_values\)/, '订单列表应展示 SKU 规格')
  assert.match(listSource, /formatOrderItemMeta\(goods\)/, '订单列表应统一展示日期、场次和数量口径')
  assert.match(listSource, /getOrderDetailSummary\(order\)/, '订单列表底部应展示 X人X晚/X单 口径')

  assert.match(detailSource, /formatSkuSpecLabel\(item\.sku_spec_values\)/, '订单详情应展示 SKU 规格')
  assert.match(detailSource, /formatOrderItemMeta\(item\)/, '订单详情应统一展示日期、场次和数量口径')
  assert.match(detailSource, /order\.remark \|\| '-'/, '订单详情应展示订单备注')
  assert.match(detailSource, /user_phone_masked \|\| order\.user_phone/, '订单详情应展示用户手机号')
  assert.match(detailSource, /item\.product_image \|\| item\.cover_image/, '订单详情应优先使用订单项商品图片')
  assert.match(detailSource, /resolveImageUrl\(image,\s*'thumb'\)/, '订单详情商品图应使用缩略图变体')
  assert.match(detailSource, /order\.payment_time/, '订单详情应使用后端 payment_time 字段展示支付时间')
  assert.doesNotMatch(detailSource, /order\.paid_at/, '订单详情不应继续读取后端未返回的 paid_at 旧字段')
})

test('shared inventory and quote response types are declared', async () => {
  const source = await readFile(typesPath, 'utf8')

  assert.match(source, /IOrderQuote|IPriceCalendar|inventory_pool_id/i, '小程序类型应声明报价与共享库存字段')
})

test('auth utility exposes stored user info lookup', async () => {
  const source = await readFile(authPath, 'utf8')

  assert.match(source, /getUserInfo/, 'auth 工具应能读取 user_info')
})

test('auth utility accepts backend user_info login response field', async () => {
  const source = await readFile(authPath, 'utf8')
  const types = await readFile(typesPath, 'utf8')

  assert.match(types, /user_info\?:\s*IUserInfo/, '登录结果类型应兼容后端 user_info 字段')
  assert.match(source, /result\.user_info\s*\|\|\s*result\.user/, '保存登录信息应优先兼容后端 user_info 字段')
  assert.doesNotMatch(source, /JSON\.stringify\(result\.user\)/, '本地存储不应只写 result.user')
})

test('member page is unified around membership card experience', async () => {
  const source = await readFile(memberPath, 'utf8')

  assert.match(source, /会员卡/, '会员页主标题和主卡片应统一显示会员卡')
  assert.match(source, /\/members\/membership-card/, '会员页数据加载应优先调用统一会员卡接口')
  assert.match(source, /\/members\/annual-card/, '会员页应保留年卡旧接口兜底')
  assert.match(source, /\/members\/times-cards/, '会员页应保留次数卡旧接口兜底')
  assert.match(source, /\/members\/membership-card\/activate/, '会员页激活入口应准备统一激活接口')
  assert.match(source, /\/members\/times-cards\/activate/, '会员页应保留旧激活码流程兼容')
  assert.match(source, /normalizeMembershipCard|buildMembershipCard/, '会员页应有统一会员卡适配层')
  assert.match(source, /卡种/, '会员卡展示应包含卡种')
  assert.match(source, /使用模式/, '会员卡展示应包含使用模式')
  assert.match(source, /状态/, '会员卡展示应包含状态')
  assert.match(source, /有效期/, '会员卡展示应包含有效期')
  assert.match(source, /剩余天数/, '会员卡展示应包含剩余天数')
  assert.match(source, /剩余次数/, '会员卡展示应包含剩余次数')
  assert.match(source, /适用商品/, '会员卡展示应包含适用商品')
  assert.match(source, /激活/, '会员页应保留激活入口')
  assert.doesNotMatch(source, /member-tabs/, '会员页不应再保留年卡/次数卡/积分分栏结构')
  assert.doesNotMatch(source, /annual-card__|times-card__|points-card__/, '会员页不应继续依赖旧年卡/次数卡/积分卡片结构')
  assert.doesNotMatch(source, /annual-card__/, '会员页不应继续依赖旧年卡卡片结构')
  assert.doesNotMatch(source, /times-card__/, '会员页不应继续依赖旧次数卡卡片结构')
})

test('member page contract types declare unified membership card shape', async () => {
  const source = await readFile(typesPath, 'utf8')

  assert.match(source, /export interface IMembershipCard/, '类型文件应声明统一会员卡类型')
  assert.match(source, /card_type/, '统一会员卡类型应包含卡种字段')
  assert.match(source, /usage_mode/, '统一会员卡类型应包含使用模式字段')
  assert.match(source, /remaining_days/, '统一会员卡类型应包含剩余天数字段')
  assert.match(source, /remaining_times/, '统一会员卡类型应包含剩余次数字段')
  assert.match(source, /applicable_products/, '统一会员卡类型应包含适用商品字段')
  assert.match(source, /IMembershipCardLegacyResponse/, '类型文件应声明旧会员接口聚合响应')
  assert.match(source, /IMembershipCardApiResponse/, '类型文件应声明统一会员卡接口响应')
})

test('camp map tracks page views and hotspot clicks with configured links', async () => {
  const source = await readFile(campMapPath, 'utf8')
  const types = await readFile(typesPath, 'utf8')
  const analytics = await readFile(analyticsPath, 'utf8')

  assert.match(types, /link_type/, '营地地图热区类型应声明链接类型')
  assert.match(types, /click_count/, '营地地图热区类型应声明点击次数')
  assert.match(source, /recordPageView\('camp-map',\s*'营地地图'\)/, '营地地图页应上报页面浏览')
  assert.match(analytics, /\/analytics\/page-view/, '页面浏览埋点工具应调用后端接口')
  assert.match(source, /\/camp-maps\/zones\/\$\{zone\.id\}\/click/, '营地地图页应上报热区点击')
  assert.match(source, /handleCmsLink/, '营地地图热区应复用 CMS 链接跳转')
  assert.doesNotMatch(source, /as any/, '营地地图链接跳转不应绕过类型检查')
  assert.match(source, /link_label/, '热区按钮应支持后台配置文案')
  assert.match(source, /map-content/, '地图热区应和底图放在同一个由图片撑开的内容盒中')
  assert.match(source, /zone\.zone_code \|\| zone\.zone_name/, '区域编码为空时热区标签应兜底区域名')
})

test('camp map exposes explicit zoom and reset controls', async () => {
  const source = await readFile(campMapPath, 'utf8')

  assert.match(source, /map-controls/, '营地地图应提供悬浮缩放控制区')
  assert.match(source, /zoomIn/, '营地地图应提供放大操作')
  assert.match(source, /zoomOut/, '营地地图应提供缩小操作')
  assert.match(source, /resetMapView/, '营地地图应提供复位操作')
  assert.match(source, /:x="mapOffsetX"/, '复位操作应能重置横向拖动偏移')
  assert.match(source, /:y="mapOffsetY"/, '复位操作应能重置纵向拖动偏移')
  assert.match(source, /width:\s*88rpx/, '缩放按钮触控宽度应不小于 88rpx')
  assert.match(source, /height:\s*88rpx/, '缩放按钮触控高度应不小于 88rpx')
  assert.match(source, /text-overflow:\s*ellipsis/, '地图按钮和标签应有文本溢出保护')
  assert.match(source, /line-height:\s*28rpx/, '热区标签应显式设置行高，避免继承地图容器 line-height: 0')
})

test('product and cms pages report page views through analytics utility', async () => {
  const analytics = await readFile(analyticsPath, 'utf8')
  const productSource = await readFile(productDetailPath, 'utf8')
  const cmsSource = await readFile(cmsPagePath, 'utf8')

  assert.match(analytics, /\/analytics\/page-view/, '小程序应有统一页面浏览埋点工具')
  assert.match(productSource, /recordPageView\(`product:\$\{p\.id\}`,\s*p\.name\)/, '商品详情加载成功后应上报浏览量')
  assert.match(cmsSource, /recordCmsPageView/, 'CMS 页面应封装单次页面浏览上报')
  assert.match(cmsSource, /recordPageView\(`cms:\$\{pageCode\.value\}`/, 'CMS 页面应按 page_code 上报浏览量')
})

test('staff page renders pending tickets orders history and order detail', async () => {
  const source = await readFile(staffPath, 'utf8')

  assert.match(source, /activeTab/, '员工页应使用 tab 管理待核销、今日订单、核销历史')
  assert.match(source, /pendingTickets/, '员工页应维护待核销列表')
  assert.match(source, /todayOrders/, '员工页应维护今日订单列表')
  assert.match(source, /verifyLogs/, '员工页应维护核销历史列表')
  assert.match(source, /\/staff\/tickets\/pending/, '员工页应调用待核销接口')
  assert.match(source, /\/staff\/orders\/today/, '员工页应调用今日订单接口')
  assert.match(source, /\/staff\/tickets\/logs/, '员工页应调用核销历史接口')
  assert.match(source, /\/staff\/orders\/\$\{orderId\}/, '员工页应按订单 ID 拉取员工端订单详情')
  assert.match(source, /showOrderDetail/, '员工页应展示订单详情弹层')
  assert.match(source, /user_phone_masked/, '员工页应展示用户手机号脱敏字段')
  assert.match(source, /remark/, '员工页应展示订单备注')
  assert.doesNotMatch(source, /功能开发中/, '员工页不应再用“功能开发中”占位订单或库存入口')
})

test('staff scan uses backend qr_token contract and refreshes lists after success', async () => {
  const source = await readFile(staffPath, 'utf8')

  assert.match(source, /qr_token:\s*res\.result/, '扫码核销 payload 应按后端 TicketScanRequest 提交 qr_token')
  assert.doesNotMatch(source, /qr_content:\s*res\.result/, '扫码核销不应提交旧的 qr_content 字段')
  assert.match(source, /needs_verification_code/, '员工页应处理会员卡验证码确认流程')
  assert.match(source, /loadStaffDashboard/, '核销成功后应刷新员工端列表')
  assert.match(source, /device_info/, '扫码核销应携带设备信息用于审计')
})

test('staff page guards direct page access by login and staff role', async () => {
  const source = await readFile(staffPath, 'utf8')

  assert.match(source, /useUserStore/, '员工页应读取用户 store 进行页面级权限判断')
  assert.match(source, /restoreFromStorage\(\)/, '员工页进入时应先恢复本地登录态')
  assert.match(source, /ensureStaffAccess/, '员工页应封装员工权限守卫')
  assert.match(source, /!userStore\.isLoggedIn/, '员工页应拦截未登录访问')
  assert.match(source, /!userStore\.isStaff/, '员工页应拦截非员工访问')
  assert.match(source, /uni\.switchTab\(\{\s*url:\s*'\/pages\/mine\/index'/, '员工页无权限时应回到我的页')
})

test('staff page supports onsite temporary order and payment collection', async () => {
  const source = await readFile(staffPath, 'utf8')
  const types = await readFile(typesPath, 'utf8')

  assert.match(types, /ITemporaryOrderCreatePayload/, '小程序类型应声明现场临时单创建 payload')
  assert.match(types, /ITemporaryOrderSession/, '小程序类型应声明现场临时单会话响应')
  assert.match(source, /key:\s*'onsite'/, '员工页应有现场收款 tab')
  assert.match(source, /onsiteForm/, '员工页应维护现场收款表单')
  assert.match(source, /customer_scan_qr/, '员工页应支持顾客扫码支付')
  assert.match(source, /merchant_scan_code/, '员工页应支持商户扫付款码')
  assert.match(source, /auth_code/, '付款码模式应提交 auth_code')
  assert.match(source, /\/staff\/orders\/temporary/, '员工页应调用现场临时单接口')
  assert.match(source, /miniapp_path/, '顾客扫码模式应展示后端返回的小程序路径')
  assert.match(source, /qrcode_image_url/, '顾客扫码模式应展示真实小程序码图片')
  assert.match(source, /<image[\s\S]*onsiteSession\.qrcode_image_url/, '员工页应渲染可扫码小程序码')
  assert.match(source, /@error="onOnsiteQrcodeError"/, '二维码加载失败应有兜底状态')
  assert.match(source, /onsiteQrcodeLoadFailed/, '二维码加载失败应提示员工')
  assert.match(source, /临时收款码/, '员工页应展示临时收款码信息')
  assert.match(source, /付款码收款已提交/, '付款码提交后应给出状态反馈')
  assert.match(source, /\.onsite-segment__item[\s\S]*height:\s*88rpx/, '现场收款分段控件触控高度应不小于 88rpx')
  assert.match(source, /\.onsite-mini-btn[\s\S]*height:\s*88rpx/, '现场收款小按钮触控高度应不小于 88rpx')
  assert.match(source, /\.onsite-action[\s\S]*height:\s*88rpx/, '现场收款提交/重置触控高度应不小于 88rpx')
  assert.match(types, /requires_query\?:\s*boolean/, '付款码结果类型应暴露是否需要查单')
  assert.match(source, /onsiteResultRequiresQuery/, '员工页应识别需要查单的付款码结果')
  assert.match(source, /queryOnsiteCodePayResult/, '员工页应提供付款码查单动作')
  assert.match(source, /\/staff\/orders\/temporary\/\$\{onsiteSession\.value\.id\}\/query-codepay/, '员工查单应调用后端查单接口')
  assert.match(source, /resetOnsiteForm/, '提交成功后应能重置表单')
})

test('staff scan cancel should not show noisy failure toast', async () => {
  const source = await readFile(staffPath, 'utf8')

  assert.match(source, /err\?\.errMsg\?\.includes\('cancel'\)[\s\S]*return/, '用户取消扫码时应直接返回，不弹失败提示')
})

test('ticket page renders real qr matrix from backend token', async () => {
  const source = await readFile(ticketPath, 'utf8')
  const qrSource = await readFile(qrCodePath, 'utf8')

  assert.match(source, /generateQrMatrix/, '票券页应使用二维码工具生成矩阵')
  assert.match(source, /qr_matrix|qrMatrix/, '票券页应保存并渲染二维码矩阵')
  assert.match(source, /v-for="\(?row,\s*rowIndex\)? in item\.qr_matrix"/, '票券页应按矩阵行渲染二维码并使用稳定行 key')
  assert.match(source, /v-for="\(?cell,\s*cellIndex\)? in row"/, '票券页应按矩阵单元渲染二维码并使用稳定列 key')
  assert.match(source, /ticket\.qr_matrix\s*=\s*generateQrMatrix\(data\.qrcode_token/, '刷新 token 后必须重新生成二维码矩阵')
  assert.doesNotMatch(source, /ticket-qr__placeholder/, '票券页不应再用占位内容代替二维码')
  assert.doesNotMatch(source, /onPreviewQr\(item\.qrcode_token\)/, '票券页不应只通过 toast 预览票码')
  assert.match(qrSource, /ReedSolomon|errorCorrection|generateQrMatrix/, '二维码工具应包含纠错编码并导出 generateQrMatrix')
})

test('ticket qr matrix decodes back to backend token', async () => {
  const qrSource = await readFile(qrCodePath, 'utf8')
  const output = ts.transpileModule(qrSource, {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2020,
    },
  }).outputText
  const module = { exports: {} }
  vm.runInNewContext(output, { module, exports: module.exports })

  const token = '0123456789abcdef0123456789abcdef'
  const matrix = module.exports.generateQrMatrix(token)
  assert.equal(matrix.length, 25, '32 位票券 token 应使用可稳定扫码的 v2-L QR 矩阵')
  const decoded = await decodeQrMatrix(matrix)
  assert.equal(decoded, token, '二维码矩阵应能被标准解码器读回原始 qr_token')
})

test('ticket page keeps qr scan area and ticket text layout stable', async () => {
  const source = await readFile(ticketPath, 'utf8')

  assert.match(source, /\.ticket-info\s*\{[\s\S]*min-width:\s*0/, '票券信息区应允许文本收缩，避免挤压状态标签')
  assert.match(source, /\.ticket-name[\s\S]*text-overflow:\s*ellipsis/, '长商品名应省略显示')
  assert.match(source, /\.ticket-no[\s\S]*text-overflow:\s*ellipsis/, '长票号应省略显示')
  assert.match(source, /&__box[\s\S]*padding:\s*48rpx/, 'QR 外框应保留 4 模块静区')
  assert.doesNotMatch(source, /&__box[\s\S]*border:\s*1rpx/, 'QR 静区不应被边框挤占')
  assert.match(source, /&__refresh[\s\S]*height:\s*88rpx/, '刷新票码按钮触控高度应不小于 88rpx')
})

test('customer service page asks knowledge base with sources feedback and human fallback', async () => {
  const source = await readFile(customerServicePath, 'utf8')
  const types = await readFile(typesPath, 'utf8')

  assert.match(source, /\/customer-service\/ask/, '小程序智能客服应调用后端知识库问答接口')
  assert.match(source, /chatMessages/, '客服页应维护对话消息流')
  assert.match(source, /source_refs|sources/, '客服回答应展示来源引用')
  assert.match(source, /needs_human/, '无知识来源时应展示人工客服兜底')
  assert.match(source, /submitFeedback/, '客服回答应支持有用/无用反馈')
  assert.match(source, /\/customer-service\/ask-logs\/\$\{message\.log_id\}\/feedback/, '反馈应回写后端问答日志')
  assert.match(source, /showError:\s*false/, '问答失败应由页面统一提示，避免重复 toast')
  assert.doesNotMatch(source, /分类开发中/, '客服分类不应再用开发中占位')

  assert.match(types, /ICustomerServiceAskResult/)
  assert.match(types, /sources:\s*ICustomerServiceSource\[]/)
  assert.match(types, /needs_human:\s*boolean/)
  assert.match(types, /log_id:\s*number/)
})

test('customer service keeps faq fallback avoids duplicate errors and uses stable mobile taps', async () => {
  const source = await readFile(customerServicePath, 'utf8')

  assert.match(source, /sendFaqQuestion\(item\)/, '热门 FAQ 点击应保留旧 FAQ 答案作为知识库未命中回退')
  assert.match(source, /fallback_answer/, 'FAQ 回退消息应记录并使用旧 answer')
  assert.match(source, /result\.needs_human[\s\S]*fallbackAnswer/, '知识库未命中时应优先展示旧 FAQ 答案')
  assert.doesNotMatch(source, /catch \(err: any\)[\s\S]{0,260}uni\.showToast\(\{ title: '智能客服暂不可用'/, '问答失败不应同时追加消息和弹固定 toast')
  assert.match(source, /lastMessageAnchor\.value = ''[\s\S]*nextTick\(\(\) => \{[\s\S]*lastMessageAnchor\.value = `msg-\$\{chatMessages\.value\[chatMessages\.value\.length - 1\]\.id\}`/, '滚动锚点应切换到最新消息 ID')
  assert.match(source, /\.quick-chip[\s\S]*height:\s*88rpx/, '快捷问题触控高度应不小于 88rpx')
  assert.match(source, /\.feedback-row__actions[\s\S]*min-height:\s*88rpx/, '反馈操作触控高度应不小于 88rpx')
  assert.match(source, /&__btn[\s\S]*height:\s*88rpx/, '人工客服按钮触控高度应不小于 88rpx')
  assert.match(source, /&__send[\s\S]*height:\s*88rpx/, '发送按钮触控高度应不小于 88rpx')
  assert.match(source, /\.source_refs__item[\s\S]*max-width:\s*100%[\s\S]*word-break:\s*break-word/, '来源引用长标题应有溢出保护')
})

test('home weather card remains visible with fallback when weather request fails', async () => {
  const homeSource = await readFile(defaultHomePagePath, 'utf8')
  const weatherSource = await readFile(weatherCardPath, 'utf8')

  assert.match(homeSource, /<weather-card\s*\/>/, '默认首页应保留天气卡片')
  assert.doesNotMatch(weatherSource, /<view class="weather-card" v-if="!loadFailed">/, '天气请求失败不应让首页天气卡整块消失')
  assert.doesNotMatch(weatherSource, /loadFailed\.value = true/, '天气请求失败不应进入整块隐藏状态')
  assert.match(weatherSource, /weatherUnavailable/, '天气卡应有接口不可用兜底态')
  assert.match(weatherSource, /天气暂不可用，请以现场天气为准/, '天气卡兜底态应给用户明确提示')
})

test('miniapp request defaults to production api when env files are missing', async () => {
  const source = await readFile(requestUtilPath, 'utf8')

  assert.match(source, /DEFAULT_API_BASE_URL\s*=\s*'https:\/\/www\.yyylcamp\.com\/api\/v1'/, '默认 API 域名应指向线上服务')
  assert.match(source, /DEFAULT_SERVER_BASE\s*=\s*'https:\/\/www\.yyylcamp\.com'/, '默认资源域名应指向线上服务')
  assert.doesNotMatch(source, /VITE_API_BASE_URL\s*\|\|\s*'http:\/\/localhost:8000\/api\/v1'/, '缺少 env 时不应回落到 localhost API')
  assert.doesNotMatch(source, /VITE_SERVER_BASE\s*\|\|\s*'http:\/\/localhost:8000'/, '缺少 env 时不应回落到 localhost 资源域名')
})

test('cms image text consumes editor colors font sizes and admin field names', async () => {
  const source = await readFile(cmsImageTextPath, 'utf8')
  const cmsTypes = await readFile(cmsTypesPath, 'utf8')

  assert.match(cmsTypes, /image_url\?:\s*string/, '小程序图文卡片类型应兼容 Admin 保存的 image_url 字段')
  assert.match(cmsTypes, /title_color\?:\s*string/, '小程序图文卡片类型应声明标题颜色')
  assert.match(cmsTypes, /desc_color\?:\s*string/, '小程序图文卡片类型应声明描述颜色')
  assert.match(cmsTypes, /title_font_size\?:\s*number \| string/, '小程序图文卡片类型应声明标题字号')
  assert.match(cmsTypes, /desc_font_size\?:\s*number \| string/, '小程序图文卡片类型应声明描述字号')
  assert.match(cmsTypes, /title_font_family\?:\s*string/, '小程序图文卡片类型应声明标题字体')
  assert.match(cmsTypes, /desc_font_weight\?:\s*string/, '小程序图文卡片类型应声明描述字重')

  assert.match(source, /props\.data\.image \|\| props\.data\.image_url/, '图文卡片应兼容 image 与 image_url')
  assert.match(source, /titleTextStyle/, '标题应绑定样式对象')
  assert.match(source, /descTextStyle/, '描述应绑定样式对象')
  assert.match(source, /props\.data\.title_color/, '标题应消费装修配置的标题颜色')
  assert.match(source, /props\.data\.desc_color/, '描述应消费装修配置的描述颜色')
  assert.match(source, /normalizeRpxSize\(props\.data\.title_font_size,\s*32\)/, '标题字号应按 rpx 归一化')
  assert.match(source, /normalizeRpxSize\(props\.data\.desc_font_size,\s*26\)/, '描述字号应按 rpx 归一化')
  assert.match(source, /normalizeFontFamily\(props\.data\.title_font_family\)/, '标题应消费装修配置的字体')
  assert.match(source, /fontWeight:\s*props\.data\.title_font_weight \|\| '600'/, '标题应消费装修配置的字重')
  assert.match(source, /layoutMode === 'right-left'/, '小程序应兼容 Admin 的右图左文布局')
  assert.match(source, /!\['vertical', 'top-bottom'\]\.includes\(layoutMode\.value\)/, '小程序应兼容 Admin 的上图下文布局')
})

test('cms renderer consumes admin image notice nav divider and miniprogram contracts', async () => {
  const imageSource = await readFile(cmsImagePath, 'utf8')
  const noticeSource = await readFile(cmsNoticePath, 'utf8')
  const navSource = await readFile(cmsNavPath, 'utf8')
  const dividerSource = await readFile(cmsDividerPath, 'utf8')
  const linkSource = await readFile(cmsLinkPath, 'utf8')
  const cmsTypes = await readFile(cmsTypesPath, 'utf8')

  assert.match(cmsTypes, /url\?:\s*string/, '小程序图片组件类型应兼容 Admin 单图 url')
  assert.match(cmsTypes, /hotspots\?:\s*CmsImageHotspot\[\]/, '小程序图片组件类型应声明热区')
  assert.match(imageSource, /normalizedImages/, '小程序图片组件应把 Admin 单图 url 归一成 images 数组')
  assert.match(imageSource, /normalizedHotspots/, '小程序图片组件应消费图片热区')
  assert.match(imageSource, /hotspot\.link/, '点击热区应触发热区链接')
  assert.match(imageSource, /imageItemStyle/, '小程序图片组件应消费 Admin 单图宽高配置')
  assert.match(imageSource, /props\.data\.width/, '小程序图片组件应读取 Admin width 字段')
  assert.match(imageSource, /props\.data\.height/, '小程序图片组件应读取 Admin height 字段')

  assert.match(cmsTypes, /texts\?:\s*string\[\]/, '公告类型应兼容 Admin 保存的 texts')
  assert.match(noticeSource, /normalizedNotices/, '公告组件应把 texts 归一成 notices')
  assert.match(noticeSource, /props\.data\.text_color/, '公告组件应消费 Admin 文本颜色')

  assert.match(cmsTypes, /label\?:\s*string/, '导航项类型应兼容 Admin label 字段')
  assert.match(navSource, /item\.name \|\| item\.label/, '导航组件应兼容 label/name')

  assert.match(cmsTypes, /line_style\?:\s*'solid' \| 'dashed'/, '分割线类型保留小程序 line_style 字段')
  assert.match(cmsTypes, /style\?:\s*'solid' \| 'dashed'/, '分割线类型应兼容 Admin style 字段')
  assert.match(dividerSource, /data\.line_style \|\| data\.style/, '分割线组件应兼容 Admin style')
  assert.match(dividerSource, /data\.margin_horizontal \?\? data\.margin/, '分割线组件应兼容 Admin margin')

  assert.match(linkSource, /parseMiniprogramTarget/, '小程序跳转应解析 Admin 存在 target 中的 appId/path JSON')
})

test('cms product list maps category keys and keeps legacy category id fallback', async () => {
  const source = await readFile(cmsProductListPath, 'utf8')
  const cmsTypes = await readFile(cmsTypesPath, 'utf8')

  assert.match(cmsTypes, /category_id\?:\s*number/, 'CMS 商品列表类型应临时保留旧 category_id')
  assert.match(source, /CMS_CATEGORY_TO_TYPE/, 'CMS 商品列表应把装修分类 key 映射为后端商品类型')
  assert.match(source, /equipment_rental:\s*'rental'/, '装备租赁 tab key 应映射为后端 rental 类型')
  assert.match(source, /camp_shop:\s*'shop'/, '小商店 tab key 应映射为后端 shop 类型')
  assert.match(source, /LEGACY_CATEGORY_ID_TO_KEY/, 'CMS 商品列表应兼容旧 category_id 配置')
  assert.match(source, /params\.type = productType/, '可消费分类 key 应优先按 type 查询，避免 category 精确过滤失效')
  assert.match(source, /params\.category = String\(props\.data\.category_id\)/, '无法映射的旧 category_id 应保留 category 兜底')
  assert.match(source, /params\.ids = props\.data\.product_ids\.join\(','\)/, '手动商品应把 product_ids 传给后端 ids 过滤')
})

test('product detail normalizes relative image urls inside rich text', async () => {
  const source = await readFile(productDetailPath, 'utf8')

  assert.match(source, /normalizeRichTextImages/, '商品详情应归一化富文本中的相对图片 URL')
  assert.match(source, /const nextSrc = resolveImageUrl\(srcMatch\[2\], 'large'\)/, '富文本相对图片应转换为完整 large 图片 URL')
  assert.match(source, /max-width:100%;height:auto;display:block;/, '富文本图片应注入自适应展示样式')
})

test('miniapp request image variants cover png webp same-domain urls and normalized variants', async () => {
  const source = await readFile(requestUtilPath, 'utf8')

  assert.match(source, /jpe\?g\|png\|webp/, '图片变体转换应覆盖 JPG、PNG、WebP')
  assert.match(source, /getSameServerImagePath/, '同域绝对 URL 应先规整成站内路径再应用派生图')
  assert.match(source, /path\.replace\(IMAGE_VARIANT_PREFIX_RE,\s*'\/images\/'\)/, '已有 thumb/large/banner 路径应先还原为原图路径')
  assert.match(source, /return `\$\{SERVER_BASE\}\$\{applyImageVariant\(sameServerPath, variant\)\}`/, '同域绝对图片 URL 应按场景转换派生图')
  assert.match(source, /originalPath\.split\(\s*\/\[\?#\]\/\s*\)\[0\]/, '带 query/hash 的图片路径应按真实 pathname 判断扩展名')
})

function decodeQrMatrix(matrix) {
  const quiet = 4
  const scale = 8
  const size = matrix.length + quiet * 2
  const png = new PNG({ width: size * scale, height: size * scale })

  for (let y = 0; y < png.height; y += 1) {
    for (let x = 0; x < png.width; x += 1) {
      const mx = Math.floor(x / scale) - quiet
      const my = Math.floor(y / scale) - quiet
      const dark = my >= 0 && my < matrix.length && mx >= 0 && mx < matrix.length && matrix[my][mx]
      const index = (png.width * y + x) << 2
      const value = dark ? 0 : 255
      png.data[index] = value
      png.data[index + 1] = value
      png.data[index + 2] = value
      png.data[index + 3] = 255
    }
  }

  return new Promise((resolve, reject) => {
    const qr = new QrCode()
    qr.callback = (err, value) => {
      if (err) {
        reject(err)
        return
      }
      resolve(value.result)
    }
    qr.decode(png)
  })
}

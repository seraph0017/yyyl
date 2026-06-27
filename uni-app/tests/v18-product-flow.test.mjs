import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { test } from 'node:test'
import vm from 'node:vm'
import ts from 'typescript'
import { PNG } from 'pngjs'
import QrCode from 'qrcode-reader'

const productDetailPath = new URL('../src/pages/product-detail/index.vue', import.meta.url)
const orderConfirmPath = new URL('../src/pages/order-confirm/index.vue', import.meta.url)
const cartPath = new URL('../src/pages/cart/index.vue', import.meta.url)
const memberPath = new URL('../src/pages/member/index.vue', import.meta.url)
const authPath = new URL('../src/utils/auth.ts', import.meta.url)
const typesPath = new URL('../src/types/index.ts', import.meta.url)
const campMapPath = new URL('../src/pages-sub/product/camp-map/index.vue', import.meta.url)
const analyticsPath = new URL('../src/utils/analytics.ts', import.meta.url)
const cmsPagePath = new URL('../src/pages/cms-page/index.vue', import.meta.url)
const staffPath = new URL('../src/pages/staff/index.vue', import.meta.url)
const ticketPath = new URL('../src/pages/ticket/index.vue', import.meta.url)
const qrCodePath = new URL('../src/utils/qrcode.ts', import.meta.url)
const customerServicePath = new URL('../src/pages/customer-service/index.vue', import.meta.url)

test('product detail no longer uses fake calendar stock or fixed camping prices', async () => {
  const source = await readFile(productDetailPath, 'utf8')

  assert.ok(!source.includes('Math.random()'), '商品详情页不应再使用 Math.random() 生成库存')
  assert.ok(!source.includes('price: isWeekend ? 168 : 128'), '商品详情页不应再写死周末/工作日价格')
  assert.match(source, /price-calendar|quote/i, '商品详情页应接入后端价格/库存数据')
  assert.match(source, /selectedSkuId\.value \? \{ sku_id: selectedSkuId\.value \} : \{\}/, '价格日历请求应携带已选 SKU，支持 SKU 级共享库存')
  assert.match(source, /validateSelectedDateRange/, '商品详情页应逐日校验选择范围内库存')
  assert.match(source, /getCalendarPriceForDate/, '商品详情页合计价应基于价格日历映射')
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

  assert.match(source, /isSkuOptionDisabled/, '商品详情应集中判断 SKU 是否禁用')
  assert.match(source, /sku\.status !== 'active'/, '下架 SKU 应禁用，避免选中后价格日历静默失败')
  assert.match(source, /isRetailProduct\(product\.value\?\.category\)[\s\S]*sku\.stock <= 0/, '仅零售商品应按 SKU 静态库存禁用规格')
  assert.match(source, /isSkuOptionDisabled\(sku\)/, '模板和点击逻辑应复用 SKU 禁用判断')
  assert.match(source, /selectedSku\.value && isSkuOptionDisabled\(selectedSku\.value\)/, '立即预定前应拦截售罄或停用 SKU')
  assert.match(source, /isRetailProduct\(p\.category\) && p\.stock <= 0/, '零售商品售罄时不应进入下单链路')
  assert.doesNotMatch(source, /!sku \|\| sku\.stock <= 0/, '营位商品不应因静态 SKU stock=0 阻止切换规格')
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

test('order confirm should inspect logged-in phone before submitting', async () => {
  const source = await readFile(orderConfirmPath, 'utf8')

  assert.match(source, /getUserInfo|phone/i, '订单确认页应读取已登录用户手机号')
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

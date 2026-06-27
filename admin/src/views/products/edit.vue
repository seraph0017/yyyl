<template>
  <div class="page-container">
    <div class="card-box">
      <div class="flex-between mb-20">
        <h3>{{ isEdit ? '编辑商品' : '新增商品' }}</h3>
        <el-button @click="router.back()">返回</el-button>
      </div>

      <el-form ref="formRef" :model="form" :rules="rules" label-width="118px" class="product-editor">
        <el-tabs v-model="activeTab">
          <el-tab-pane label="基础信息" name="base">
            <div class="editor-section">
              <el-form-item label="商品名称" prop="name">
                <el-input v-model="form.name" maxlength="100" show-word-limit />
              </el-form-item>
              <el-form-item label="商品类型" prop="type">
                <el-select v-model="form.type" style="width: 100%;">
                  <el-option label="日常露营" value="daily_camping" />
                  <el-option label="活动露营" value="event_camping" />
                  <el-option label="装备租赁" value="rental" />
                  <el-option label="日常活动" value="daily_activity" />
                  <el-option label="特定活动" value="special_activity" />
                  <el-option label="小商店" value="shop" />
                  <el-option label="周边商品" value="merchandise" />
                </el-select>
              </el-form-item>
              <el-form-item label="业务分类">
                <el-input v-model="form.category" maxlength="50" placeholder="如 campsite / drink / family" />
              </el-form-item>
              <el-form-item label="预约模式">
                <el-radio-group v-model="form.booking_mode">
                  <el-radio-button label="by_position">孤品</el-radio-button>
                  <el-radio-button label="by_quantity">通品</el-radio-button>
                </el-radio-group>
              </el-form-item>
              <el-form-item label="基础价格" prop="base_price">
                <el-input-number v-model="form.base_price" :min="0" :precision="2" controls-position="right" />
              </el-form-item>
              <el-form-item label="状态">
                <el-radio-group v-model="form.status">
                  <el-radio value="draft">草稿</el-radio>
                  <el-radio value="on_sale">上架</el-radio>
                  <el-radio value="off_sale">下架</el-radio>
                </el-radio-group>
              </el-form-item>
              <el-form-item label="售卖时间">
                <el-date-picker
                  v-model="saleRange"
                  type="datetimerange"
                  value-format="YYYY-MM-DDTHH:mm:ssZ"
                  start-placeholder="开售时间"
                  end-placeholder="停售时间"
                  @change="handleSaleRangeChange"
                />
              </el-form-item>
              <el-form-item label="退款规则">
                <div class="inline-controls">
                  <el-select v-model="form.refund_deadline_type" style="width: 120px">
                    <el-option label="提前小时" value="hours" />
                    <el-option label="提前天数" value="days" />
                  </el-select>
                  <el-input-number v-model="form.refund_deadline_value" :min="0" controls-position="right" />
                </div>
              </el-form-item>
              <el-form-item label="开关">
                <div class="switch-grid">
                  <el-switch v-model="form.require_disclaimer" active-text="免责声明" />
                  <el-switch v-model="form.require_camping_ticket" active-text="需露营票" />
                  <el-switch v-model="form.is_seckill" active-text="秒杀" />
                </div>
              </el-form-item>
              <el-form-item label="支付超时">
                <div class="inline-controls">
                  <el-input-number v-model="form.normal_payment_timeout" :min="60" controls-position="right" />
                  <el-input-number v-model="form.seckill_payment_timeout" :min="60" controls-position="right" />
                </div>
              </el-form-item>
              <el-form-item label="排序">
                <el-input-number v-model="form.sort_order" :min="0" controls-position="right" />
              </el-form-item>
            </div>
          </el-tab-pane>

          <el-tab-pane label="详情内容" name="content">
            <div class="editor-section">
              <el-form-item label="商品图片">
                <div class="image-editor">
                  <div v-for="(image, index) in form.images" :key="index" class="image-row">
                    <el-input v-model="image.url" placeholder="图片 URL" />
                    <el-input-number v-model="image.sort_order" :min="0" controls-position="right" />
                    <el-button @click="removeImage(index)">移除</el-button>
                  </div>
                  <el-button @click="addImage">添加图片</el-button>
                </div>
              </el-form-item>
              <el-form-item label="富文本描述">
                <el-input v-model="form.description" type="textarea" :rows="10" placeholder="支持 HTML，预览会做安全过滤" />
              </el-form-item>
              <el-form-item label="安全预览">
                <div class="rich-preview" v-html="safeDescriptionPreview"></div>
              </el-form-item>
            </div>
          </el-tab-pane>

          <el-tab-pane label="类型属性" name="extension">
            <div class="editor-section">
              <template v-if="isCampingType">
                <el-form-item label="区域">
                  <el-input v-model="form.ext_camping.area" placeholder="如 A区 / 林下区" />
                </el-form-item>
                <el-form-item label="营位编号">
                  <el-input v-model="form.ext_camping.position_name" />
                </el-form-item>
                <el-form-item label="活动日期" v-if="form.type === 'event_camping'">
                  <el-date-picker
                    v-model="campingEventRange"
                    type="daterange"
                    value-format="YYYY-MM-DD"
                    start-placeholder="开始日期"
                    end-placeholder="结束日期"
                    @change="handleCampingEventRangeChange"
                  />
                </el-form-item>
                <el-form-item label="设施">
                  <div class="switch-grid">
                    <el-switch v-model="form.ext_camping.has_electricity" active-text="有电" />
                    <el-switch v-model="form.ext_camping.has_platform" active-text="木平台" />
                  </div>
                </el-form-item>
                <el-form-item label="最大人数">
                  <el-input-number v-model="form.ext_camping.max_persons" :min="0" controls-position="right" />
                </el-form-item>
              </template>

              <template v-else-if="isActivityType">
                <el-form-item label="预约单位">
                  <el-radio-group v-model="form.ext_activity.booking_unit">
                    <el-radio-button label="person">按人</el-radio-button>
                    <el-radio-button label="group">按组</el-radio-button>
                  </el-radio-group>
                </el-form-item>
                <el-form-item label="活动日期" v-if="form.type === 'special_activity'">
                  <el-date-picker v-model="form.ext_activity.event_date" type="date" value-format="YYYY-MM-DD" />
                </el-form-item>
                <el-form-item label="场次">
                  <div class="image-editor">
                    <div v-for="(slot, index) in form.ext_activity.time_slots" :key="index" class="image-row">
                      <el-time-picker v-model="slot.start" value-format="HH:mm" placeholder="开始" />
                      <el-time-picker v-model="slot.end" value-format="HH:mm" placeholder="结束" />
                      <el-input-number v-model="slot.capacity" :min="0" controls-position="right" />
                      <el-button @click="removeTimeSlot(index)">移除</el-button>
                    </div>
                    <el-button @click="addTimeSlot">添加场次</el-button>
                  </div>
                </el-form-item>
              </template>

              <template v-else-if="form.type === 'rental'">
                <el-form-item label="押金">
                  <el-input-number v-model="form.ext_rental.deposit_amount" :min="0" :precision="2" controls-position="right" />
                </el-form-item>
                <el-form-item label="租赁分类">
                  <el-select v-model="form.ext_rental.rental_category" style="width: 100%">
                    <el-option label="过夜装备" value="overnight" />
                    <el-option label="照明" value="lighting" />
                    <el-option label="家具" value="furniture" />
                    <el-option label="交通" value="vehicle" />
                    <el-option label="其他" value="other" />
                  </el-select>
                </el-form-item>
              </template>

              <template v-else>
                <el-form-item label="多规格">
                  <el-switch v-model="form.ext_shop.has_sku" />
                </el-form-item>
                <el-form-item label="规格定义">
                  <el-input
                    v-model="specDefinitionsText"
                    type="textarea"
                    :rows="6"
                    placeholder='JSON，例如 [{"name":"颜色","values":["红","蓝"]}]'
                  />
                </el-form-item>
                <el-form-item label="销售类型">
                  <el-radio-group v-model="form.ext_shop.shop_type">
                    <el-radio-button label="onsite">现场</el-radio-button>
                    <el-radio-button label="online">线上</el-radio-button>
                  </el-radio-group>
                </el-form-item>
                <el-form-item label="物流">
                  <el-switch v-model="form.ext_shop.shipping_required" active-text="需要邮寄" />
                </el-form-item>
              </template>
            </div>
          </el-tab-pane>

          <el-tab-pane label="SKU" name="sku">
            <div class="editor-section">
              <el-table :data="form.skus" border>
                <el-table-column label="编码" min-width="160">
                  <template #default="{ row }">
                    <el-input v-model="row.sku_code" placeholder="不填自动生成" />
                  </template>
                </el-table-column>
                <el-table-column label="规格 JSON" min-width="220">
                  <template #default="{ row }">
                    <el-input v-model="row.spec_values_text" placeholder='{"规格":"默认"}' />
                  </template>
                </el-table-column>
                <el-table-column label="价格" width="140">
                  <template #default="{ row }">
                    <el-input-number v-model="row.price" :min="0" :precision="2" controls-position="right" />
                  </template>
                </el-table-column>
                <el-table-column label="库存" width="120">
                  <template #default="{ row }">
                    <el-input-number v-model="row.stock" :min="0" controls-position="right" />
                  </template>
                </el-table-column>
                <el-table-column label="图片 URL" min-width="180">
                  <template #default="{ row }">
                    <el-input v-model="row.image_url" placeholder="SKU 图片 URL" clearable />
                  </template>
                </el-table-column>
                <el-table-column label="状态" width="110">
                  <template #default="{ row }">
                    <el-select v-model="row.status">
                      <el-option label="启用" value="active" />
                      <el-option label="停用" value="inactive" />
                    </el-select>
                  </template>
                </el-table-column>
                <el-table-column label="操作" width="90">
                  <template #default="{ $index }">
                    <el-button link type="danger" @click="removeSku($index)">移除</el-button>
                  </template>
                </el-table-column>
              </el-table>
              <el-button class="mt-12" @click="addSku">添加 SKU</el-button>
            </div>
          </el-tab-pane>
        </el-tabs>

        <el-form-item class="editor-footer">
          <el-button type="primary" :loading="saving" @click="handleSubmit">保存</el-button>
          <el-button @click="router.back()">取消</el-button>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import DOMPurify from 'dompurify'
import { createProduct, getAdminProductDetail, updateProduct, updateProductStatus } from '@/api/product'
import type {
  ActivityExt,
  CampingExt,
  Product,
  ProductCreateRequest,
  ProductImage,
  ProductSkuUpsert,
  ProductStatus,
  ProductType,
  RentalExt,
  ShopExt,
} from '@/types'

interface EditableSku extends ProductSkuUpsert {
  spec_values_text: string
}

interface ProductForm {
  name: string
  status: ProductStatus
  type: ProductType
  category: string
  booking_mode: string
  base_price: number
  images: ProductImage[]
  description: string
  sale_start_at?: string | null
  sale_end_at?: string | null
  refund_deadline_type: 'days' | 'hours'
  refund_deadline_value: number
  require_disclaimer: boolean
  require_camping_ticket: boolean
  is_seckill: boolean
  seckill_payment_timeout: number
  normal_payment_timeout: number
  sort_order: number
  ext_camping: CampingExt
  ext_activity: ActivityExt
  ext_rental: RentalExt
  ext_shop: ShopExt
  skus: EditableSku[]
}

const router = useRouter()
const route = useRoute()
const formRef = ref<FormInstance>()
const activeTab = ref('base')
const saving = ref(false)
const saleRange = ref<[string, string] | null>(null)
const campingEventRange = ref<[string, string] | null>(null)
const specDefinitionsText = ref('[]')

const isEdit = computed(() => !!route.params.id)
const productId = computed(() => Number(route.params.id || 0))
const isCampingType = computed(() => ['daily_camping', 'event_camping'].includes(form.type))
const isActivityType = computed(() => ['daily_activity', 'special_activity'].includes(form.type))
const safeDescriptionPreview = computed(() => DOMPurify.sanitize(form.description || ''))

const form = reactive<ProductForm>({
  name: '',
  type: 'daily_camping',
  category: 'campsite',
  status: 'draft',
  booking_mode: 'by_quantity',
  base_price: 0,
  images: [],
  description: '',
  sale_start_at: null,
  sale_end_at: null,
  refund_deadline_type: 'hours',
  refund_deadline_value: 24,
  require_disclaimer: true,
  require_camping_ticket: false,
  is_seckill: false,
  seckill_payment_timeout: 300,
  normal_payment_timeout: 1800,
  sort_order: 0,
  ext_camping: {
    has_electricity: false,
    has_platform: false,
    area: '',
    position_name: '',
    max_persons: 0,
    event_start_date: null,
    event_end_date: null,
  },
  ext_activity: {
    booking_unit: 'person',
    time_slots: [],
    event_date: null,
  },
  ext_rental: {
    deposit_amount: 0,
    rental_category: 'other',
    damage_config: [],
  },
  ext_shop: {
    has_sku: false,
    spec_definitions: [],
    shipping_required: false,
    shop_type: 'onsite',
  },
  skus: [],
})

const rules: FormRules = {
  name: [{ required: true, message: '请输入商品名称', trigger: 'blur' }],
  type: [{ required: true, message: '请选择商品类型', trigger: 'change' }],
  base_price: [{ required: true, message: '请输入基础价格', trigger: 'blur' }],
}

function normalizeImages(images: Product['images'] | undefined): ProductImage[] {
  return (images || []).map((image: ProductImage | string, index: number) => {
    if (typeof image === 'string') return { url: image, sort_order: index }
    return { url: image.url || '', sort_order: image.sort_order ?? index, alt: image.alt }
  })
}

function resetFormWithProduct(product: Product) {
  Object.assign(form, {
    name: product.name,
    type: product.type,
    category: String(product.category || product.type),
    status: product.status,
    booking_mode: product.booking_mode || 'by_quantity',
    base_price: Number(product.base_price || 0),
    images: normalizeImages(product.images),
    description: product.description || '',
    sale_start_at: product.sale_start_at || null,
    sale_end_at: product.sale_end_at || null,
    refund_deadline_type: product.refund_deadline_type || 'hours',
    refund_deadline_value: product.refund_deadline_value ?? 24,
    require_disclaimer: product.require_disclaimer ?? true,
    require_camping_ticket: product.require_camping_ticket ?? false,
    is_seckill: product.is_seckill ?? false,
    seckill_payment_timeout: product.seckill_payment_timeout ?? 300,
    normal_payment_timeout: product.normal_payment_timeout ?? 1800,
    sort_order: product.sort_order ?? 0,
    ext_camping: { ...form.ext_camping, ...(product.ext_camping || {}) },
    ext_activity: { ...form.ext_activity, ...(product.ext_activity || {}) },
    ext_rental: { ...form.ext_rental, ...(product.ext_rental || {}) },
    ext_shop: { ...form.ext_shop, ...(product.ext_shop || {}) },
    skus: (product.skus || []).map(sku => ({
      id: sku.id,
      sku_code: sku.sku_code,
      spec_values: sku.spec_values || sku.attributes || {},
      spec_values_text: JSON.stringify(sku.spec_values || sku.attributes || {}),
      price: Number(sku.price || 0),
      stock: Number(sku.stock || 0),
      status: sku.status || 'active',
      image_url: sku.image_url || null,
    })),
  })
  saleRange.value = product.sale_start_at && product.sale_end_at ? [product.sale_start_at, product.sale_end_at] : null
  campingEventRange.value = form.ext_camping.event_start_date && form.ext_camping.event_end_date
    ? [form.ext_camping.event_start_date, form.ext_camping.event_end_date]
    : null
  specDefinitionsText.value = JSON.stringify(form.ext_shop.spec_definitions || [])
}

async function fetchDetail() {
  if (!isEdit.value) return
  const res = await getAdminProductDetail(productId.value)
  resetFormWithProduct(res.data)
}

function addImage() {
  form.images.push({ url: '', sort_order: form.images.length })
}

function removeImage(index: number) {
  form.images.splice(index, 1)
}

function addTimeSlot() {
  form.ext_activity.time_slots = [
    ...(form.ext_activity.time_slots || []),
    { start: '09:00', end: '10:00', capacity: 10 },
  ]
}

function removeTimeSlot(index: number) {
  form.ext_activity.time_slots?.splice(index, 1)
}

function addSku() {
  form.skus.push({
    sku_code: '',
    spec_values: {},
    spec_values_text: '{}',
    price: form.base_price,
    stock: 0,
    status: 'active',
    image_url: null,
  })
}

function removeSku(index: number) {
  form.skus.splice(index, 1)
}

function handleSaleRangeChange(value: [string, string] | null) {
  form.sale_start_at = value?.[0] || null
  form.sale_end_at = value?.[1] || null
}

function handleCampingEventRangeChange(value: [string, string] | null) {
  form.ext_camping.event_start_date = value?.[0] || null
  form.ext_camping.event_end_date = value?.[1] || null
}

function parseJsonArray(text: string, fallback: Array<Record<string, any>>) {
  try {
    const parsed = JSON.parse(text || '[]')
    return Array.isArray(parsed) ? parsed : fallback
  } catch {
    throw new Error('规格定义 JSON 格式错误')
  }
}

function parseSkuSpec(row: EditableSku) {
  try {
    const parsed = JSON.parse(row.spec_values_text || '{}')
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : {}
  } catch {
    throw new Error(`SKU ${row.sku_code || '未命名'} 规格 JSON 格式错误`)
  }
}

function ensureSkuCode(row: EditableSku, index: number): string {
  const skuCode = (row.sku_code || '').trim() || `P${productId.value || 'NEW'}-${Date.now()}-${index + 1}`
  if (!skuCode) {
    throw new Error('SKU 编码不能为空')
  }
  row.sku_code = skuCode
  return skuCode
}

function buildProductPayload(): ProductCreateRequest {
  const payload: ProductCreateRequest = {
    name: form.name,
    type: form.type,
    category: form.category as ProductCreateRequest['category'],
    status: form.status,
    booking_mode: form.booking_mode,
    base_price: form.base_price,
    images: form.images.filter(image => image.url),
    description: form.description,
    sale_start_at: form.sale_start_at,
    sale_end_at: form.sale_end_at,
    refund_deadline_type: form.refund_deadline_type,
    refund_deadline_value: form.refund_deadline_value,
    require_disclaimer: form.require_disclaimer,
    require_camping_ticket: form.require_camping_ticket,
    is_seckill: form.is_seckill,
    seckill_payment_timeout: form.seckill_payment_timeout,
    normal_payment_timeout: form.normal_payment_timeout,
    sort_order: form.sort_order,
    skus: form.skus.map((row, index) => ({
      id: row.id,
      sku_code: ensureSkuCode(row, index),
      spec_values: parseSkuSpec(row),
      price: row.price,
      stock: row.stock,
      status: row.status,
      image_url: row.image_url || null,
    })),
  }

  if (isCampingType.value) payload.ext_camping = form.ext_camping
  if (isActivityType.value) payload.ext_activity = form.ext_activity
  if (form.type === 'rental') payload.ext_rental = form.ext_rental
  if (['shop', 'merchandise'].includes(form.type)) {
    payload.ext_shop = {
      ...form.ext_shop,
      spec_definitions: parseJsonArray(specDefinitionsText.value, []),
    }
  }
  return payload
}

async function handleSubmit() {
  if (!formRef.value) return
  await formRef.value.validate()

  saving.value = true
  try {
    const payload = buildProductPayload()
    if (isEdit.value) {
      await updateProduct(productId.value, payload)
      ElMessage.success('更新成功')
    } else {
      const createPayload = { ...payload, status: 'draft' as const }
      const created = await createProduct(createPayload)
      if (payload.status && payload.status !== 'draft') {
        await updateProductStatus(created.data.id, payload.status)
      }
      ElMessage.success('创建成功')
    }
    router.push('/products')
  } catch (err: any) {
    ElMessage.error(err?.message || '保存失败')
  } finally {
    saving.value = false
  }
}

onMounted(fetchDetail)
</script>

<style lang="scss" scoped>
.product-editor {
  max-width: 980px;
}

.editor-section {
  max-width: 820px;
  padding-top: 12px;
}

.inline-controls {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
}

.switch-grid {
  display: flex;
  gap: 18px;
  flex-wrap: wrap;
}

.image-editor {
  display: flex;
  flex-direction: column;
  gap: 10px;
  width: 100%;
}

.image-row {
  display: grid;
  grid-template-columns: minmax(180px, 1fr) 140px auto;
  gap: 10px;
  align-items: center;
}

@media (max-width: 720px) {
  .image-row {
    grid-template-columns: 1fr;
  }

  .inline-controls,
  .switch-grid {
    align-items: flex-start;
    flex-direction: column;
  }
}

.rich-preview {
  width: 100%;
  min-height: 140px;
  padding: 12px;
  border: 1px solid var(--color-border-light);
  border-radius: 8px;
  background: var(--color-bg);
  line-height: 1.7;
}

.editor-footer {
  margin-top: 20px;
}

.mt-12 {
  margin-top: 12px;
}
</style>

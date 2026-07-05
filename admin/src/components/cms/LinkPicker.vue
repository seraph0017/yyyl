<template>
  <el-dialog
    :model-value="visible"
    title="链接选择器"
    width="520px"
    aria-label="链接选择器"
    @update:model-value="emit('update:visible', $event)"
    @close="emit('update:visible', false)"
  >
    <el-form label-width="90px" size="default">
      <!-- 链接类型 -->
      <el-form-item label="链接类型">
        <el-select v-model="localLink.type" style="width: 100%" @change="onTypeChange">
          <el-option label="无链接" value="none" />
          <el-option label="商品" value="product" />
          <el-option label="页面路径" value="page" />
          <el-option label="商品分类" value="category" />
          <el-option label="CMS活动页" value="activity" />
          <el-option label="H5链接" value="h5" />
          <el-option label="小程序" value="miniprogram" />
        </el-select>
      </el-form-item>

      <!-- 根据类型展示不同配置 -->

      <!-- 商品选择 -->
      <template v-if="localLink.type === 'product'">
        <el-form-item label="选择商品">
          <el-select
            v-model="localLink.target"
            filterable
            remote
            :remote-method="searchProducts"
            :loading="productLoading"
            placeholder="搜索并选择商品"
            style="width: 100%"
            @change="onProductChange"
          >
            <el-option
              v-for="product in productOptions"
              :key="product.id"
              :label="product.name"
              :value="String(product.id)"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="显示名称">
          <el-input v-model="localLink.title" placeholder="商品名称" />
        </el-form-item>
      </template>

      <!-- 页面路径 -->
      <template v-if="localLink.type === 'page'">
        <el-form-item label="页面路径">
          <el-input v-model="localLink.target" placeholder="/pages/xxx/index" />
        </el-form-item>
        <el-form-item label="显示名称">
          <el-input v-model="localLink.title" placeholder="页面名称" />
        </el-form-item>
      </template>

      <!-- 商品分类 -->
      <template v-if="localLink.type === 'category'">
        <el-form-item label="商品分类">
          <el-select
            v-model="localLink.target"
            filterable
            placeholder="选择商品分类"
            style="width: 100%"
            @change="onCategoryChange"
          >
            <el-option
              v-for="category in categoryOptions"
              :key="category.value"
              :label="category.label"
              :value="category.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="显示名称">
          <el-input v-model="localLink.title" placeholder="分类名称" />
        </el-form-item>
      </template>

      <!-- CMS 活动页 -->
      <template v-if="localLink.type === 'activity'">
        <el-form-item label="活动页">
          <el-select
            v-model="localLink.target"
            filterable
            :loading="pageLoading"
            placeholder="选择 CMS 活动页"
            style="width: 100%"
            @change="onPageChange"
          >
            <el-option
              v-for="page in pageOptions"
              :key="page.page_code"
              :label="`${page.title}（${page.page_code}）`"
              :value="page.page_code"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="显示名称">
          <el-input v-model="localLink.title" placeholder="活动名称" />
        </el-form-item>
      </template>

      <!-- H5 链接 -->
      <template v-if="localLink.type === 'h5'">
        <el-form-item label="URL地址">
          <el-input v-model="localLink.target" placeholder="https://example.com">
            <template #prepend>URL</template>
          </el-input>
          <div v-if="localLink.target && !isValidUrl(localLink.target)" class="url-error">
            请输入有效的 URL 地址
          </div>
        </el-form-item>
        <el-form-item label="显示名称">
          <el-input v-model="localLink.title" placeholder="链接名称" />
        </el-form-item>
      </template>

      <!-- 小程序 -->
      <template v-if="localLink.type === 'miniprogram'">
        <el-form-item label="AppID">
          <el-input v-model="miniAppId" placeholder="小程序 AppID" @blur="updateMiniprogramTarget" />
        </el-form-item>
        <el-form-item label="路径">
          <el-input v-model="miniPath" placeholder="pages/index/index" @blur="updateMiniprogramTarget" />
        </el-form-item>
        <el-form-item label="显示名称">
          <el-input v-model="localLink.title" placeholder="小程序名称" />
        </el-form-item>
      </template>
    </el-form>

    <template #footer>
      <el-button @click="emit('update:visible', false)">取消</el-button>
      <el-button type="primary" @click="handleConfirm">确定</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref, watch } from 'vue'
import { getProducts } from '@/api/product'
import { getCmsPages } from '@/api/cms'
import type { CmsPage, LinkConfig } from '@/types/cms'
import type { Product } from '@/types'

const props = defineProps<{
  modelValue: LinkConfig
  visible: boolean
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: LinkConfig): void
  (e: 'update:visible', value: boolean): void
}>()

const localLink = reactive<LinkConfig>({
  type: 'none',
  target: '',
  title: '',
})

// 小程序特有字段
const miniAppId = ref('')
const miniPath = ref('')
const productLoading = ref(false)
const productOptions = ref<Array<Pick<Product, 'id' | 'name'>>>([])
const pageLoading = ref(false)
const pageOptions = ref<Array<Pick<CmsPage, 'page_code' | 'title'>>>([])
const categoryOptions = [
  { label: '日常露营', value: 'daily_camping' },
  { label: '活动露营', value: 'event_camping' },
  { label: '装备租赁', value: 'equipment_rental' },
  { label: '日常活动', value: 'daily_activity' },
  { label: '特定活动', value: 'special_activity' },
  { label: '小商店', value: 'camp_shop' },
  { label: '周边商品', value: 'merchandise' },
]

function syncLocalLink(value?: LinkConfig) {
  const nextValue = value || { type: 'none', target: '', title: '' }
  Object.assign(localLink, nextValue)
  if (nextValue.type === 'miniprogram' && nextValue.target) {
    try {
      const parsed = JSON.parse(nextValue.target)
      miniAppId.value = parsed.appId || ''
      miniPath.value = parsed.path || ''
    } catch {
      miniAppId.value = ''
      miniPath.value = ''
    }
  } else {
    miniAppId.value = ''
    miniPath.value = ''
  }
}

// 同步外部值
watch(
  () => props.modelValue,
  (val) => {
    syncLocalLink(val)
  },
  { immediate: true, deep: true }
)

watch(
  () => props.visible,
  (visible) => {
    if (visible) {
      syncLocalLink(props.modelValue)
      if (props.modelValue?.type === 'activity' || pageOptions.value === undefined) {
        fetchPages()
      }
    }
  }
)

// 切换类型时重置
function onTypeChange() {
  localLink.target = ''
  localLink.title = ''
  miniAppId.value = ''
  miniPath.value = ''
  if (localLink.type === 'activity') {
    fetchPages()
  }
}

// 更新小程序目标
function updateMiniprogramTarget() {
  localLink.target = JSON.stringify({ appId: miniAppId.value, path: miniPath.value })
}

async function searchProducts(keyword = '') {
  productLoading.value = true
  try {
    const res = await getProducts({
      page: 1,
      page_size: 50,
      keyword: keyword || undefined,
    })
    productOptions.value = (res.data.list || []).map(product => ({
      id: product.id,
      name: product.name,
    }))
  } finally {
    productLoading.value = false
  }
}

async function fetchPages() {
  pageLoading.value = true
  try {
    const res = await getCmsPages({ page: 1, page_size: 100 })
    pageOptions.value = (res.data.list || [])
      .filter(page => ['activity', 'promotion', 'custom', 'home'].includes(page.page_type))
      .map(page => ({
        page_code: page.page_code,
        title: page.title,
      }))
  } finally {
    pageLoading.value = false
  }
}

function onProductChange(value: string) {
  const selected = productOptions.value?.find(product => String(product.id) === String(value))
  if (selected) {
    localLink.title = selected.name
  }
}

function onCategoryChange(value: string) {
  const selected = categoryOptions.find(category => category.value === value)
  if (selected) {
    localLink.title = selected.label
  }
}

function onPageChange(value: string) {
  const selected = pageOptions.value?.find(page => page.page_code === value)
  if (selected) {
    localLink.title = selected.title
  }
}

// URL 校验
function isValidUrl(url: string): boolean {
  try {
    new URL(url)
    return true
  } catch {
    return false
  }
}

// 确认
function handleConfirm() {
  // H5 URL 校验
  if (localLink.type === 'h5' && localLink.target && !isValidUrl(localLink.target)) {
    ElMessage.warning('请输入有效的 URL 地址')
    return
  }
  emit('update:modelValue', { ...localLink })
  emit('update:visible', false)
}

onMounted(() => {
  searchProducts()
  fetchPages()
})
</script>

<style lang="scss" scoped>
.url-error {
  color: var(--el-color-danger);
  font-size: 12px;
  margin-top: 4px;
}
</style>

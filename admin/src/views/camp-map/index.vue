<template>
  <div class="page-container">
    <div class="camp-map-layout">
      <!-- 左侧：地图列表 -->
      <div class="card-box map-list-panel">
        <div class="flex-between mb-16">
          <h3>营地地图</h3>
          <el-button type="primary" size="small" @click="handleCreateMap">
            <el-icon><Plus /></el-icon>新建
          </el-button>
        </div>

        <div v-loading="loading" class="map-list">
          <div
            v-for="map in mapList"
            :key="map.id"
            class="map-list-item"
            :class="{ active: selectedMap?.id === map.id }"
            @click="selectMap(map)"
          >
            <div class="map-item-info">
              <div class="map-item-name">{{ map.name }}</div>
              <div class="map-item-meta">
                <el-tag :type="map.status === 'active' ? 'success' : 'info'" size="small">
                  {{ map.status === 'active' ? '启用' : '停用' }}
                </el-tag>
                <span class="zone-count">{{ map.zones?.length || 0 }} 个区域</span>
              </div>
            </div>
            <div class="map-item-actions">
              <el-tooltip content="编辑" placement="top" :show-after="400">
                <el-button class="action-btn action-btn--edit" circle size="small" @click.stop="handleEditMap(map)">
                  <el-icon><Edit /></el-icon>
                </el-button>
              </el-tooltip>
              <el-tooltip content="删除" placement="top" :show-after="400">
                <el-button class="action-btn action-btn--delete" circle size="small" @click.stop="handleDeleteMap(map)">
                  <el-icon><Delete /></el-icon>
                </el-button>
              </el-tooltip>
            </div>
          </div>
          <el-empty v-if="!loading && mapList.length === 0" description="暂无地图" />
        </div>
      </div>

      <!-- 右侧：地图预览和区域管理 -->
      <div class="card-box map-preview-panel">
        <template v-if="selectedMap">
          <div class="flex-between mb-16">
            <h3>{{ selectedMap.name }} — 区域管理</h3>
            <el-button type="primary" size="small" @click="handleCreateZone">
              <el-icon><Plus /></el-icon>添加区域
            </el-button>
          </div>

          <!-- 地图图片预览 -->
          <div class="map-image-wrapper mb-16">
            <div v-if="selectedMap.map_image" class="map-preview-scroll">
              <div class="map-preview-canvas">
                <img
                  :src="selectedMap.map_image"
                  alt="营地地图"
                  class="map-image"
                />
                <button
                  v-for="zone in selectedMap.zones || []"
                  :key="zone.id"
                  type="button"
                  class="map-zone-overlay"
                  :style="getZoneOverlayStyle(zone)"
                  @click="handleEditZone(zone)"
                >
                  <span>{{ zone.zone_code || zone.zone_name }}</span>
                </button>
              </div>
              <el-image
                :src="selectedMap.map_image"
                class="map-preview-hidden"
                :preview-src-list="[selectedMap.map_image]"
              />
            </div>
            <el-empty v-else description="暂未上传地图图片" />
          </div>

          <!-- 区域列表 -->
          <el-table :data="selectedMap.zones || []" stripe size="small">
            <el-table-column prop="zone_name" label="区域名称" min-width="120" />
            <el-table-column prop="zone_code" label="区域编码" width="100" />
            <el-table-column label="坐标" width="200">
              <template #default="{ row }">
                <span class="text-secondary">
                  x:{{ row.coordinates?.x }}, y:{{ row.coordinates?.y }},
                  {{ row.coordinates?.width }}×{{ row.coordinates?.height }}
                </span>
              </template>
            </el-table-column>
            <el-table-column label="关联商品" width="100" align="center">
              <template #default="{ row }">
                <el-tag size="small">{{ row.product_ids?.length || 0 }} 个</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="热区链接" min-width="150">
              <template #default="{ row }">
                <el-tag v-if="row.link_type && row.link_type !== 'none'" size="small" type="warning">
                  {{ getLinkTypeLabel(row.link_type) }}
                </el-tag>
                <span v-else class="text-secondary">未配置</span>
              </template>
            </el-table-column>
            <el-table-column prop="click_count" label="点击" width="72" align="center" />
            <el-table-column prop="sort_order" label="排序" width="60" align="center" />
            <el-table-column label="操作" width="120" fixed="right" align="center">
              <template #default="{ row }">
                <div class="action-buttons">
                  <el-tooltip content="编辑" placement="top" :show-after="400">
                    <el-button class="action-btn action-btn--edit" circle size="small" @click="handleEditZone(row)">
                      <el-icon><Edit /></el-icon>
                    </el-button>
                  </el-tooltip>
                  <el-tooltip content="删除" placement="top" :show-after="400">
                    <el-button class="action-btn action-btn--delete" circle size="small" @click="handleDeleteZone(row)">
                      <el-icon><Delete /></el-icon>
                    </el-button>
                  </el-tooltip>
                </div>
              </template>
            </el-table-column>
          </el-table>
        </template>
        <el-empty v-else description="请从左侧选择一个地图" />
      </div>
    </div>

    <!-- 地图新建/编辑弹窗 -->
    <el-dialog v-model="mapDialogVisible" :title="editingMapId ? '编辑地图' : '新建地图'" width="500px" destroy-on-close>
      <el-form ref="mapFormRef" :model="mapForm" :rules="mapFormRules" label-width="90px">
        <el-form-item label="地图名称" prop="name">
          <el-input v-model="mapForm.name" placeholder="请输入地图名称" />
        </el-form-item>
        <el-form-item label="地图类型" prop="map_type">
          <el-select v-model="mapForm.map_type" placeholder="选择类型" style="width: 100%">
            <el-option label="图片地图" value="image" />
            <el-option label="SVG地图" value="svg" />
          </el-select>
        </el-form-item>
        <el-form-item label="地图图片" prop="map_image">
          <el-input v-model="mapForm.map_image" placeholder="图片URL（支持上传）">
            <template #append>
              <el-upload
                :show-file-list="false"
                action="/api/v1/admin/cms/assets/upload"
                :headers="uploadHeaders"
                :on-success="handleMapImageUpload"
              >
                <el-button>上传</el-button>
              </el-upload>
            </template>
          </el-input>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="mapDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmitMap">确定</el-button>
      </template>
    </el-dialog>

    <!-- 区域新建/编辑弹窗 -->
    <el-dialog v-model="zoneDialogVisible" :title="editingZoneId ? '编辑区域' : '新建区域'" width="560px" destroy-on-close>
      <el-form ref="zoneFormRef" :model="zoneForm" :rules="zoneFormRules" label-width="90px">
        <el-form-item label="区域名称" prop="zone_name">
          <el-input v-model="zoneForm.zone_name" placeholder="如 A区、湖畔区" />
        </el-form-item>
        <el-form-item label="区域编码" prop="zone_code">
          <el-input v-model="zoneForm.zone_code" placeholder="如 zone_a（可选）" />
        </el-form-item>
        <el-form-item label="坐标">
          <div class="coordinates-row">
            <el-input-number v-model="zoneForm.coordinates.x" :min="0" :max="100" placeholder="X" controls-position="right" />
            <el-input-number v-model="zoneForm.coordinates.y" :min="0" :max="100" placeholder="Y" controls-position="right" />
            <el-input-number v-model="zoneForm.coordinates.width" :min="1" :max="100" placeholder="宽" controls-position="right" />
            <el-input-number v-model="zoneForm.coordinates.height" :min="1" :max="100" placeholder="高" controls-position="right" />
          </div>
        </el-form-item>
        <el-form-item label="关联商品">
          <el-select v-model="zoneForm.product_ids" multiple filterable placeholder="选择关联的商品" style="width: 100%">
            <el-option v-for="p in productList" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="链接类型">
          <el-segmented
            v-model="zoneForm.link_type"
            :options="linkTypeOptions"
            @change="handleLinkTypeChange"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item v-if="zoneForm.link_type === 'product'" label="链接目标">
          <el-select
            v-model="zoneForm.link_target"
            class="link-product-select"
            filterable
            placeholder="选择要跳转的商品"
            style="width: 100%"
          >
            <el-option
              v-for="p in productList"
              :key="p.id"
              :label="p.name"
              :value="String(p.id)"
            />
          </el-select>
        </el-form-item>
        <el-form-item v-else-if="zoneForm.link_type && zoneForm.link_type !== 'none'" label="链接目标">
          <el-input v-model="zoneForm.link_target" :placeholder="linkTargetPlaceholder" />
        </el-form-item>
        <el-form-item v-if="zoneForm.link_type && zoneForm.link_type !== 'none'" label="按钮文案">
          <el-input v-model="zoneForm.link_label" placeholder="如 查看详情、立即预约" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="zoneForm.description" type="textarea" :rows="3" placeholder="区域描述（选填）" />
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="zoneForm.sort_order" :min="0" :max="999" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="zoneDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmitZone">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { Plus, Edit, Delete } from '@element-plus/icons-vue'
import { getCampMaps, createCampMap, updateCampMap, deleteCampMap, createCampMapZone, updateCampMapZone, deleteCampMapZone } from '@/api/camp-map'
import { get, getToken, getCurrentSiteId } from '@/utils/request'
import type { CampMap, CampMapZone, CampMapCreate, CampMapZoneCreate } from '@/types'

type ZoneLinkType = 'none' | 'product' | 'cms' | 'h5'
type ZoneFormState = Omit<CampMapZoneCreate, 'link_type'> & {
  link_type: ZoneLinkType
}

const loading = ref(false)
const submitting = ref(false)
const mapList = ref<CampMap[]>([])
const selectedMap = ref<CampMap | null>(null)

// 商品列表
const productList = ref<{ id: number; name: string }[]>([])
async function fetchProducts() {
  try {
    const res = await get<{ code: number; data: { list: { id: number; name: string }[]; pagination: { total: number } } }>('/admin/products', { page: 1, page_size: 200 })
    productList.value = res.data.list
  } catch {
    productList.value = []
    ElMessage.error('商品列表加载失败，请检查网络后重试')
  }
}

// 上传请求头
const uploadHeaders = computed(() => ({
  Authorization: `Bearer ${getToken()}`,
  'X-Site-Id': getCurrentSiteId(),
}))

// ========== 地图管理 ==========
const mapDialogVisible = ref(false)
const editingMapId = ref<number | null>(null)
const mapFormRef = ref<FormInstance>()
const mapForm = reactive<CampMapCreate>({
  name: '',
  map_image: '',
  map_type: 'image',
})

const mapFormRules: FormRules = {
  name: [{ required: true, message: '请输入地图名称', trigger: 'blur' }],
  map_type: [{ required: true, message: '请选择地图类型', trigger: 'change' }],
}

async function fetchMaps() {
  loading.value = true
  try {
    const res = await getCampMaps()
    mapList.value = res.data.list
    // 如果之前有选中的地图，刷新其数据
    if (selectedMap.value) {
      const updated = mapList.value.find(m => m.id === selectedMap.value!.id)
      selectedMap.value = updated || null
    }
  } catch {
    mapList.value = []
  } finally {
    loading.value = false
  }
}

function selectMap(map: CampMap) {
  selectedMap.value = map
}

function handleCreateMap() {
  editingMapId.value = null
  mapForm.name = ''
  mapForm.map_image = ''
  mapForm.map_type = 'image'
  mapDialogVisible.value = true
}

function handleEditMap(map: CampMap) {
  editingMapId.value = map.id
  mapForm.name = map.name
  mapForm.map_image = map.map_image
  mapForm.map_type = map.map_type
  mapDialogVisible.value = true
}

async function handleDeleteMap(map: CampMap) {
  await ElMessageBox.confirm(`确认删除地图「${map.name}」及其所有区域？`, '删除确认', { type: 'warning' })
  await deleteCampMap(map.id)
  ElMessage.success('删除成功')
  if (selectedMap.value?.id === map.id) {
    selectedMap.value = null
  }
  fetchMaps()
}

async function handleSubmitMap() {
  await mapFormRef.value?.validate()
  submitting.value = true
  try {
    if (editingMapId.value) {
      await updateCampMap(editingMapId.value, { ...mapForm })
      ElMessage.success('更新成功')
    } else {
      await createCampMap({ ...mapForm })
      ElMessage.success('创建成功')
    }
    mapDialogVisible.value = false
    fetchMaps()
  } finally {
    submitting.value = false
  }
}

function handleMapImageUpload(response: any) {
  const url = response.data?.file_url || response.data?.url
  if (url) {
    mapForm.map_image = url
    ElMessage.success('图片上传成功')
  }
}

// ========== 区域管理 ==========
const zoneDialogVisible = ref(false)
const editingZoneId = ref<number | null>(null)
const zoneFormRef = ref<FormInstance>()
const zoneForm = reactive<ZoneFormState>({
  zone_name: '',
  zone_code: '',
  coordinates: { x: 0, y: 0, width: 100, height: 100 },
  product_ids: [],
  description: '',
  sort_order: 0,
  link_type: 'none',
  link_target: null,
  link_label: null,
})

const zoneFormRules: FormRules = {
  zone_name: [{ required: true, message: '请输入区域名称', trigger: 'blur' }],
}

const linkTypeOptions = [
  { label: '无', value: 'none' },
  { label: '商品', value: 'product' },
  { label: 'CMS', value: 'cms' },
  { label: 'H5', value: 'h5' },
]

const linkTargetPlaceholder = computed(() => {
  if (zoneForm.link_type === 'none') return ''
  if (zoneForm.link_type === 'product') return '选择商品'
  if (zoneForm.link_type === 'cms') return 'CMS 页面编码，如 spring_campaign'
  if (zoneForm.link_type === 'h5') return 'https:// 开头的外部链接'
  return ''
})

function getLinkTypeLabel(type?: string | null) {
  const item = linkTypeOptions.find(option => option.value === type)
  return item?.label || '未知'
}

function getZoneOverlayStyle(zone: CampMapZone) {
  const c = zone.coordinates || { x: 0, y: 0, width: 0, height: 0 }
  return {
    left: `${c.x}%`,
    top: `${c.y}%`,
    width: `${c.width}%`,
    height: `${c.height}%`,
  }
}

function handleLinkTypeChange() {
  zoneForm.link_target = null
  zoneForm.link_label = null
}

function validateZoneCoordinates(): boolean {
  const { x, y, width, height } = zoneForm.coordinates
  if ([x, y, width, height].some(value => typeof value !== 'number' || Number.isNaN(value))) {
    ElMessage.warning('请填写完整的百分比坐标')
    return false
  }
  if (x < 0 || y < 0 || width <= 0 || height <= 0 || x > 100 || y > 100 || width > 100 || height > 100) {
    ElMessage.warning('坐标必须在 0-100 的百分比范围内')
    return false
  }
  if (x + width > 100) {
    ElMessage.warning('热区宽度超出底图范围')
    return false
  }
  if (y + height > 100) {
    ElMessage.warning('热区高度超出底图范围')
    return false
  }
  return true
}

function validateZoneLink(): boolean {
  if (!zoneForm.link_type || zoneForm.link_type === 'none') return true
  const target = String(zoneForm.link_target || '').trim()
  if (!target) {
    ElMessage.warning('请填写链接目标')
    return false
  }
  if (zoneForm.link_type === 'product') {
    if (productList.value.length === 0) {
      ElMessage.warning('商品列表加载失败，暂不能保存商品热区链接')
      return false
    }
    const selectedProductIds = new Set(productList.value.map(item => String(item.id)))
    if (!selectedProductIds.has(target)) {
      ElMessage.warning('请选择有效商品')
      return false
    }
  }
  if (zoneForm.link_type === 'cms' && !/^[A-Za-z0-9_-]{2,50}$/.test(target)) {
    ElMessage.warning('CMS 页面编码仅支持字母、数字、下划线和短横线')
    return false
  }
  if (zoneForm.link_type === 'h5' && !/^https:\/\//.test(target)) {
    ElMessage.warning('H5 链接必须以 https:// 开头')
    return false
  }
  zoneForm.link_target = target
  return true
}

function handleCreateZone() {
  editingZoneId.value = null
  zoneForm.zone_name = ''
  zoneForm.zone_code = ''
  zoneForm.coordinates = { x: 0, y: 0, width: 100, height: 100 }
  zoneForm.product_ids = []
  zoneForm.description = ''
  zoneForm.sort_order = 0
  zoneForm.link_type = 'none'
  zoneForm.link_target = null
  zoneForm.link_label = null
  zoneDialogVisible.value = true
}

function handleEditZone(zone: CampMapZone) {
  editingZoneId.value = zone.id
  zoneForm.zone_name = zone.zone_name
  zoneForm.zone_code = zone.zone_code
  zoneForm.coordinates = { ...zone.coordinates }
  zoneForm.product_ids = [...zone.product_ids]
  zoneForm.description = zone.description
  zoneForm.sort_order = zone.sort_order
  zoneForm.link_type = (zone.link_type && zone.link_type !== null ? zone.link_type : 'none') as ZoneLinkType
  zoneForm.link_target = zone.link_target || null
  zoneForm.link_label = zone.link_label || null
  zoneDialogVisible.value = true
}

async function handleDeleteZone(zone: CampMapZone) {
  await ElMessageBox.confirm(`确认删除区域「${zone.zone_name}」？`, '删除确认', { type: 'warning' })
  await deleteCampMapZone(zone.id)
  ElMessage.success('删除成功')
  fetchMaps()
}

async function handleSubmitZone() {
  await zoneFormRef.value?.validate()
  if (!selectedMap.value) return
  if (!validateZoneCoordinates()) return
  if (!validateZoneLink()) return
  submitting.value = true
  try {
    if (editingZoneId.value) {
      await updateCampMapZone(editingZoneId.value, { ...zoneForm })
      ElMessage.success('更新成功')
    } else {
      await createCampMapZone(selectedMap.value.id, { ...zoneForm })
      ElMessage.success('创建成功')
    }
    zoneDialogVisible.value = false
    fetchMaps()
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  fetchMaps()
  fetchProducts()
})
</script>

<style lang="scss" scoped>
.camp-map-layout {
  display: flex;
  gap: 16px;
  min-height: calc(100vh - 120px);
}

.map-list-panel {
  width: 320px;
  flex-shrink: 0;
}

.map-preview-panel {
  flex: 1;
  min-width: 0;
}

.map-list {
  .map-list-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px;
    border-radius: 6px;
    cursor: pointer;
    transition: background 0.2s;
    border: 1px solid transparent;

    &:hover { background: var(--color-bg-warm); }
    &.active {
      background: rgba(61, 139, 94, 0.06);
      border-color: var(--color-primary);
    }

    .map-item-name {
      font-size: 14px;
      font-weight: 600;
      margin-bottom: 4px;
    }
    .map-item-meta {
      display: flex;
      align-items: center;
      gap: 8px;
      .zone-count { font-size: 12px; color: var(--color-text-placeholder); }
    }
    .map-item-actions {
      flex-shrink: 0;
    }
  }
}

.map-image-wrapper {
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-small);
  overflow: hidden;
  min-height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-bg-warm);
  padding: 12px;

  .map-preview-scroll {
    width: 100%;
    max-height: 420px;
    overflow: auto;
    text-align: center;
  }

  .map-preview-canvas {
    position: relative;
    display: inline-block;
    line-height: 0;
    max-width: 100%;
  }

  .map-image {
    display: block;
    max-width: 100%;
    height: auto;
    object-fit: contain;
  }

  .map-preview-hidden {
    display: none;
  }
}

.map-zone-overlay {
  position: absolute;
  border: 2px solid rgba(200, 168, 114, 0.92);
  background: rgba(45, 74, 62, 0.16);
  color: #fff;
  border-radius: 4px;
  padding: 0;
  cursor: pointer;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.34);
  transition: border-color 0.2s, background-color 0.2s, transform 0.2s;

  &:hover {
    border-color: var(--color-primary);
    background: rgba(45, 74, 62, 0.28);
    transform: scale(1.02);
  }

  span {
    display: inline-flex;
    align-items: center;
    max-width: 100%;
    min-height: 20px;
    padding: 2px 6px;
    border-radius: 0 0 4px 0;
    background: rgba(45, 74, 62, 0.82);
    font-size: 12px;
    line-height: 16px;
    color: #fff;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
}

.coordinates-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;

  :deep(.el-input-number) {
    flex: 1 1 110px;
    min-width: 104px;
    max-width: 130px;
  }
}

.text-secondary {
  font-size: 12px;
  color: var(--color-text-placeholder);
}
</style>

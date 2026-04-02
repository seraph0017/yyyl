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
        <el-form-item label="商品ID">
          <el-input v-model="localLink.target" placeholder="输入商品ID" />
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
        <el-form-item label="分类ID">
          <el-input v-model="localLink.target" placeholder="输入分类ID" />
        </el-form-item>
        <el-form-item label="显示名称">
          <el-input v-model="localLink.title" placeholder="分类名称" />
        </el-form-item>
      </template>

      <!-- CMS 活动页 -->
      <template v-if="localLink.type === 'activity'">
        <el-form-item label="页面ID">
          <el-input v-model="localLink.target" placeholder="CMS页面ID" />
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
import { reactive, ref, watch } from 'vue'
import type { LinkConfig } from '@/types/cms'

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

// 同步外部值
watch(
  () => props.modelValue,
  (val) => {
    if (val) {
      Object.assign(localLink, val)
      // 解析小程序配置
      if (val.type === 'miniprogram' && val.target) {
        try {
          const parsed = JSON.parse(val.target)
          miniAppId.value = parsed.appId || ''
          miniPath.value = parsed.path || ''
        } catch {
          miniAppId.value = ''
          miniPath.value = ''
        }
      }
    }
  },
  { immediate: true, deep: true }
)

// 切换类型时重置
function onTypeChange() {
  localLink.target = ''
  localLink.title = ''
  miniAppId.value = ''
  miniPath.value = ''
}

// 更新小程序目标
function updateMiniprogramTarget() {
  localLink.target = JSON.stringify({ appId: miniAppId.value, path: miniPath.value })
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
</script>

<style lang="scss" scoped>
.url-error {
  color: var(--el-color-danger);
  font-size: 12px;
  margin-top: 4px;
}
</style>

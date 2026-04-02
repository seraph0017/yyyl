<template>
  <el-form label-width="80px" size="small">
    <!-- 导航项列表 -->
    <el-form-item label="导航项">
      <draggable
        v-model="localItems"
        item-key="label"
        handle=".nav-drag-handle"
        class="nav-items-list"
        @change="emitChange"
      >
        <template #item="{ element, index }">
          <div class="nav-item-row">
            <div class="nav-drag-handle">⠿</div>
            <div class="nav-item-icon" @click="openAssetLibrary(index)">
              <img v-if="element.icon" :src="element.icon" />
              <el-icon v-else><Plus /></el-icon>
            </div>
            <el-input v-model="element.label" placeholder="文字" class="nav-item-input" @blur="emitChange" />
            <el-button link size="small" @click="openLinkPicker(index)">链接</el-button>
            <el-button :icon="Delete" link type="danger" size="small" @click="removeItem(index)" />
          </div>
        </template>
      </draggable>
      <el-button type="primary" link @click="addItem">
        <el-icon><Plus /></el-icon>添加导航
      </el-button>
    </el-form-item>

    <!-- 每行列数 -->
    <el-form-item label="每行列数">
      <el-radio-group v-model="localProps.columns" @change="emitChange">
        <el-radio-button :value="4">4列</el-radio-button>
        <el-radio-button :value="5">5列</el-radio-button>
      </el-radio-group>
    </el-form-item>

    <!-- 显示文字 -->
    <el-form-item label="显示文字">
      <el-switch v-model="localProps.show_label" @change="emitChange" />
    </el-form-item>

    <AssetLibrary v-model:visible="assetVisible" file-type="image" @select="onAssetSelect" />
    <LinkPicker v-model="currentLink" v-model:visible="linkVisible" @update:modelValue="onLinkChange" />
  </el-form>
</template>

<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import draggable from 'vuedraggable'
import { Plus, Delete } from '@element-plus/icons-vue'
import type { NavPropsConfig, LinkConfig, CmsAsset } from '@/types/cms'
import AssetLibrary from '../AssetLibrary.vue'
import LinkPicker from '../LinkPicker.vue'

const props = defineProps<{ modelValue: NavPropsConfig }>()
const emit = defineEmits<{ (e: 'update:modelValue', value: NavPropsConfig): void }>()

const localProps = reactive<NavPropsConfig>({
  items: [],
  columns: 4,
  show_label: true,
})

const localItems = ref<NavPropsConfig['items']>([])
const assetVisible = ref(false)
const linkVisible = ref(false)
const editingIndex = ref(-1)
const currentLink = ref<LinkConfig>({ type: 'none', target: '', title: '' })

watch(() => props.modelValue, (val) => {
  if (val) {
    Object.assign(localProps, val)
    localItems.value = [...(val.items || [])]
  }
}, { immediate: true, deep: true })

function emitChange() {
  emit('update:modelValue', { ...localProps, items: [...localItems.value] })
}

function addItem() {
  localItems.value.push({ icon: '', label: '', link: { type: 'none', target: '', title: '' } })
  emitChange()
}

function removeItem(index: number) {
  localItems.value.splice(index, 1)
  emitChange()
}

function openAssetLibrary(index: number) {
  editingIndex.value = index
  assetVisible.value = true
}

function onAssetSelect(assets: CmsAsset[]) {
  if (assets.length > 0 && editingIndex.value >= 0) {
    localItems.value[editingIndex.value].icon = assets[0].file_url
    emitChange()
  }
  assetVisible.value = false
}

function openLinkPicker(index: number) {
  editingIndex.value = index
  currentLink.value = { ...(localItems.value[index].link || { type: 'none', target: '', title: '' }) }
  linkVisible.value = true
}

function onLinkChange(link: LinkConfig) {
  if (editingIndex.value >= 0) {
    localItems.value[editingIndex.value].link = { ...link }
    emitChange()
  }
}
</script>

<style lang="scss" scoped>
.nav-items-list {
  width: 100%;
}

.nav-item-row {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 8px;
  margin-bottom: 6px;
  background: #f5f7fa;
  border-radius: 6px;
  border: 1px solid #ebeef5;
}

.nav-drag-handle {
  cursor: grab;
  color: #909399;
  font-size: 12px;
}

.nav-item-icon {
  width: 32px;
  height: 32px;
  border: 1px dashed #dcdfe6;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  overflow: hidden;
  flex-shrink: 0;
  background: #fff;

  img {
    width: 100%;
    height: 100%;
    object-fit: contain;
  }

  .el-icon { color: #c0c4cc; font-size: 14px; }
}

.nav-item-input {
  flex: 1;
  min-width: 0;
}
</style>

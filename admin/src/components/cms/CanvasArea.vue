<template>
  <div class="canvas-wrapper">
    <div
      class="phone-frame"
      :class="{ 'phone-frame--desktop': previewMode === 'desktop' }"
      :style="{ backgroundColor: pageSettings.background_color }"
    >
      <!-- 标题栏模拟 -->
      <div
        class="phone-status-bar"
        :style="{ backgroundColor: pageSettings.title_bar_color, color: pageSettings.title_bar_text_color }"
      >
        <span class="status-bar-title">{{ previewMode === 'desktop' ? '桌面预览' : '手机预览' }}</span>
      </div>

      <!-- 组件列表（可拖拽排序） -->
      <draggable
        :list="localComponents"
        group="cms"
        item-key="id"
        handle=".drag-handle"
        ghost-class="drag-ghost"
        @change="onDragChange"
        class="canvas-body"
      >
        <template #item="{ element }">
          <div
            class="canvas-component"
            :class="{ 'is-selected': element.id === selectedId }"
            :style="{
              marginTop: (element.style?.margin_top || 0) + 'px',
              marginBottom: (element.style?.margin_bottom || 0) + 'px',
              borderRadius: (element.style?.border_radius || 0) + 'px',
              background: element.style?.background || 'transparent',
            }"
            @click.stop="emit('select', element.id)"
          >
            <!-- 拖拽手柄 -->
            <div class="drag-handle" aria-label="拖拽排序" title="拖拽排序">⠿</div>

            <!-- 组件预览 -->
            <component
              :is="getPreviewComponent(element.type)"
              v-bind="element.props"
            />

            <!-- 选中浮层操作 -->
            <div v-if="element.id === selectedId" class="component-actions">
              <el-tooltip content="上移" placement="top">
                <el-button
                  :icon="ArrowUp"
                  circle
                  size="small"
                  aria-label="上移组件"
                  :disabled="getIndex(element.id) === 0"
                  @click.stop="handleMove(element.id, -1)"
                />
              </el-tooltip>
              <el-tooltip content="下移" placement="top">
                <el-button
                  :icon="ArrowDown"
                  circle
                  size="small"
                  aria-label="下移组件"
                  :disabled="getIndex(element.id) === localComponents.length - 1"
                  @click.stop="handleMove(element.id, 1)"
                />
              </el-tooltip>
              <el-tooltip content="复制" placement="top">
                <el-button
                  :icon="CopyDocument"
                  circle
                  size="small"
                  aria-label="复制组件"
                  @click.stop="handleDuplicate(element.id)"
                />
              </el-tooltip>
              <el-tooltip content="删除" placement="top">
                <el-button
                  :icon="Delete"
                  circle
                  size="small"
                  type="danger"
                  aria-label="删除组件"
                  @click.stop="handleRemove(element.id)"
                />
              </el-tooltip>
            </div>
          </div>
        </template>
      </draggable>

      <!-- 空状态 -->
      <div v-if="localComponents.length === 0" class="canvas-empty">
        <el-icon :size="48"><Files /></el-icon>
        <p>从左侧拖入或点击组件开始搭建页面</p>
        <span class="canvas-empty__hint">支持拖拽排序和实时预览</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, type Component as VueComponent } from 'vue'
import draggable from 'vuedraggable'
import { ArrowUp, ArrowDown, CopyDocument, Delete, Files, ShoppingBag, Ticket, Bell } from '@element-plus/icons-vue'
import type { ComponentItem, CmsConfig } from '@/types/cms'
import { useCmsStore } from '@/stores/cms'

// 画布预览组件：复用 Landing 系列组件
import LandingBanner from '@/components/landing/LandingBanner.vue'
import LandingImage from '@/components/landing/LandingImage.vue'
import LandingImageText from '@/components/landing/LandingImageText.vue'
import LandingRichText from '@/components/landing/LandingRichText.vue'
import LandingVideo from '@/components/landing/LandingVideo.vue'
import LandingNav from '@/components/landing/LandingNav.vue'
import LandingSpacer from '@/components/landing/LandingSpacer.vue'
import LandingDivider from '@/components/landing/LandingDivider.vue'

const props = defineProps<{
  components: ComponentItem[]
  selectedId: string | null
  pageSettings: CmsConfig['page_settings']
  previewMode: 'mobile' | 'desktop'
}>()

const emit = defineEmits<{
  (e: 'select', componentId: string): void
  (e: 'reorder', newList: ComponentItem[]): void
}>()

const cmsStore = useCmsStore()

// 本地副本用于 draggable 绑定
const localComponents = ref<ComponentItem[]>([])

watch(
  () => props.components,
  (val) => {
    localComponents.value = [...val]
  },
  { immediate: true, deep: true }
)

// 预览组件映射
const previewComponentMap: Record<string, VueComponent | { template: string }> = {
  banner: LandingBanner,
  image: LandingImage,
  image_text: LandingImageText,
  rich_text: LandingRichText,
  video: LandingVideo,
  nav: LandingNav,
  spacer: LandingSpacer,
  divider: LandingDivider,
  // 以下在画布中使用占位预览
  product_list: { template: '<div class="canvas-placeholder"><el-icon><ShoppingBag /></el-icon> 商品列表（预览占位）</div>', components: { ShoppingBag } },
  coupon: { template: '<div class="canvas-placeholder"><el-icon><Ticket /></el-icon> 优惠券（预览占位）</div>', components: { Ticket } },
  notice: { template: '<div class="canvas-placeholder"><el-icon><Bell /></el-icon> 公告栏（预览占位）</div>', components: { Bell } },
}

function getPreviewComponent(type: string) {
  return previewComponentMap[type] || { template: '<div class="canvas-placeholder">未知组件</div>' }
}

// 拖拽事件
function onDragChange() {
  emit('reorder', [...localComponents.value])
}

// 获取组件索引
function getIndex(id: string) {
  return localComponents.value.findIndex(c => c.id === id)
}

// 上移/下移
function handleMove(id: string, direction: number) {
  const idx = getIndex(id)
  const targetIdx = idx + direction
  if (targetIdx < 0 || targetIdx >= localComponents.value.length) return
  cmsStore.moveComponent(idx, targetIdx)
}

// 复制组件
function handleDuplicate(id: string) {
  cmsStore.duplicateComponent(id)
}

// 删除组件（需确认）
async function handleRemove(id: string) {
  try {
    await ElMessageBox.confirm('确定删除该组件？', '确认删除', {
      type: 'warning',
      confirmButtonText: '确定',
      cancelButtonText: '取消',
    })
    cmsStore.removeComponent(id)
  } catch {
    // 取消删除
  }
}
</script>

<style lang="scss" scoped>
.canvas-wrapper {
  flex: 1;
  display: flex;
  justify-content: center;
  align-items: flex-start;
  padding: 20px;
  background: #f0f2f5;
  overflow-y: auto;
  min-height: 0;
}

.phone-frame {
  width: 375px;
  min-height: 667px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.15);
  overflow: hidden;
  position: relative;
  display: flex;
  flex-direction: column;

  &--desktop {
    width: 1000px;
    min-height: 600px;
  }
}

.phone-status-bar {
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 500;
  flex-shrink: 0;
}

.status-bar-title {
  opacity: 0.9;
}

.canvas-body {
  flex: 1;
  min-height: 200px;
  padding: 0;
}

.canvas-component {
  position: relative;
  cursor: pointer;
  border: 2px solid transparent;
  transition: border-color 0.2s ease;

  &:hover {
    border-color: rgba(45, 74, 62, 0.3);
  }

  &.is-selected {
    border-color: var(--color-primary, #2d4a3e);
    box-shadow: 0 0 0 1px var(--color-primary, #2d4a3e);
  }

  .drag-handle {
    position: absolute;
    top: 4px;
    left: 4px;
    z-index: 10;
    width: 24px;
    height: 24px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 4px;
    background: rgba(0, 0, 0, 0.5);
    color: #fff;
    font-size: 14px;
    cursor: grab;
    opacity: 0;
    transition: opacity 0.2s;
  }

  &:hover .drag-handle {
    opacity: 1;
  }
}

.component-actions {
  position: absolute;
  top: -40px;
  right: 0;
  display: flex;
  gap: 4px;
  background: #fff;
  border-radius: 6px;
  padding: 4px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.15);
  z-index: 20;
}

.canvas-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 20px;
  color: var(--color-text-placeholder, #c0c4cc);

  .el-icon {
    margin-bottom: 12px;
  }

  p {
    font-size: 14px;
    margin: 0 0 8px;
  }

  &__hint {
    font-size: 12px;
    color: var(--color-text-placeholder, #dcdfe6);
  }
}

.drag-ghost {
  opacity: 0.4;
  border: 2px dashed var(--color-primary, #2d4a3e);
  background: rgba(45, 74, 62, 0.05);
}

:deep(.canvas-placeholder) {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 24px 16px;
  background: #f5f7fa;
  color: #909399;
  font-size: 14px;
  border: 1px dashed #dcdfe6;
  margin: 8px;
  border-radius: 4px;
}
</style>

<template>
  <div class="property-panel">
    <!-- 选中组件时：显示组件属性表单 -->
    <template v-if="component">
      <div class="panel-header">
        <span class="panel-title">{{ componentName }}</span>
        <el-tag size="small" type="info">{{ component.type }}</el-tag>
      </div>

      <!-- 动态属性表单 -->
      <el-scrollbar class="panel-body">
        <div class="props-section">
          <div class="section-title">组件属性</div>
          <component
            :is="getPropsComponent(component.type)"
            :modelValue="component.props"
            @update:modelValue="onPropsChange"
          />
        </div>

        <!-- 通用样式设置 -->
        <div class="props-section">
          <div class="section-title">通用样式</div>
          <el-form label-width="80px" size="small">
            <el-form-item label="上外边距">
              <el-input-number
                :model-value="component.style.margin_top"
                :min="0"
                :max="100"
                @update:model-value="(v: number) => onStyleChange({ margin_top: v })"
              />
            </el-form-item>
            <el-form-item label="下外边距">
              <el-input-number
                :model-value="component.style.margin_bottom"
                :min="0"
                :max="100"
                @update:model-value="(v: number) => onStyleChange({ margin_bottom: v })"
              />
            </el-form-item>
            <el-form-item label="圆角">
              <el-input-number
                :model-value="component.style.border_radius || 0"
                :min="0"
                :max="50"
                @update:model-value="(v: number) => onStyleChange({ border_radius: v })"
              />
            </el-form-item>
            <el-form-item label="背景色">
              <el-color-picker
                :model-value="component.style.background || ''"
                show-alpha
                @update:model-value="(v: string) => onStyleChange({ background: v || undefined })"
              />
            </el-form-item>
          </el-form>
        </div>
      </el-scrollbar>
    </template>

    <!-- 未选中组件时：显示页面全局设置 -->
    <template v-else>
      <div class="panel-header">
        <span class="panel-title">页面设置</span>
      </div>
      <el-scrollbar class="panel-body">
        <div class="props-section">
          <div class="section-title">全局样式</div>
          <el-form label-width="100px" size="small">
            <el-form-item label="背景色">
              <el-color-picker
                :model-value="pageSettings.background_color"
                @update:model-value="(v: string) => onPageSettingsChange({ background_color: v })"
              />
            </el-form-item>
            <el-form-item label="标题栏颜色">
              <el-color-picker
                :model-value="pageSettings.title_bar_color"
                @update:model-value="(v: string) => onPageSettingsChange({ title_bar_color: v })"
              />
            </el-form-item>
            <el-form-item label="标题栏文字">
              <el-color-picker
                :model-value="pageSettings.title_bar_text_color"
                @update:model-value="(v: string) => onPageSettingsChange({ title_bar_text_color: v })"
              />
            </el-form-item>
          </el-form>
        </div>
      </el-scrollbar>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, type Component as VueComponent } from 'vue'
import type { ComponentItem, CmsConfig } from '@/types/cms'

// 属性表单组件
import BannerProps from './props/BannerProps.vue'
import ImageProps from './props/ImageProps.vue'
import ImageTextProps from './props/ImageTextProps.vue'
import NoticeProps from './props/NoticeProps.vue'
import NavProps from './props/NavProps.vue'
import ProductListProps from './props/ProductListProps.vue'
import CouponProps from './props/CouponProps.vue'
import RichTextProps from './props/RichTextProps.vue'
import SpacerProps from './props/SpacerProps.vue'
import DividerProps from './props/DividerProps.vue'
import VideoProps from './props/VideoProps.vue'

const props = defineProps<{
  component: ComponentItem | null
  pageSettings: CmsConfig['page_settings']
}>()

const emit = defineEmits<{
  (e: 'update', componentId: string, updates: Partial<ComponentItem>): void
  (e: 'updatePageSettings', settings: Partial<CmsConfig['page_settings']>): void
}>()

// 组件名称映射
const nameMap: Record<string, string> = {
  banner: '轮播图',
  image: '图片',
  image_text: '图文卡片',
  notice: '公告栏',
  nav: '快捷导航',
  product_list: '商品列表',
  coupon: '优惠券',
  rich_text: '富文本',
  spacer: '间距',
  divider: '分割线',
  video: '视频',
}

const componentName = computed(() => {
  return props.component ? (nameMap[props.component.type] || '未知组件') : ''
})

// 属性表单组件映射
const propsComponentMap: Record<string, VueComponent> = {
  banner: BannerProps,
  image: ImageProps,
  image_text: ImageTextProps,
  notice: NoticeProps,
  nav: NavProps,
  product_list: ProductListProps,
  coupon: CouponProps,
  rich_text: RichTextProps,
  spacer: SpacerProps,
  divider: DividerProps,
  video: VideoProps,
}

function getPropsComponent(type: string) {
  return propsComponentMap[type] || null
}

// 属性变更
function onPropsChange(newProps: Record<string, any>) {
  if (props.component) {
    emit('update', props.component.id, { props: newProps })
  }
}

// 样式变更
function onStyleChange(style: Partial<ComponentItem['style']>) {
  if (props.component) {
    emit('update', props.component.id, { style: { ...props.component.style, ...style } })
  }
}

// 页面设置变更
function onPageSettingsChange(settings: Partial<CmsConfig['page_settings']>) {
  emit('updatePageSettings', settings)
}
</script>

<style lang="scss" scoped>
.property-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid var(--color-border-light, #ebeef5);
}

.panel-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text);
}

.panel-body {
  flex: 1;
  overflow-y: auto;
}

.props-section {
  padding: 12px 16px;
  border-bottom: 1px solid var(--color-border-light, #ebeef5);

  &:last-child {
    border-bottom: none;
  }
}

.section-title {
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text-secondary);
  margin-bottom: 12px;
}

:deep(.el-form-item) {
  margin-bottom: 12px;
}
</style>

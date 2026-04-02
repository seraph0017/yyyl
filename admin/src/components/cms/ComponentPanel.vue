<template>
  <div class="component-panel">
    <div class="panel-title">组件库</div>
    <div v-for="group in componentGroups" :key="group.label" class="component-group">
      <div class="group-label">{{ group.label }}</div>
      <draggable
        :list="group.components"
        :group="{ name: 'cms', pull: 'clone', put: false }"
        :clone="cloneComponent"
        item-key="type"
        :sort="false"
        class="component-grid"
      >
        <template #item="{ element }">
          <div class="component-item" @click="emit('add', element.type)">
            <el-icon :size="24"><component :is="element.icon" /></el-icon>
            <span class="component-item__name">{{ element.name }}</span>
          </div>
        </template>
      </draggable>
    </div>
  </div>
</template>

<script setup lang="ts">
import draggable from 'vuedraggable'
import {
  PictureFilled, Postcard, ChatDotSquare, Grid,
  Goods, Ticket, Document, Minus, VideoCamera,
  Picture, Operation,
} from '@element-plus/icons-vue'
import type { ComponentGroup } from '@/types/cms'

const emit = defineEmits<{
  (e: 'add', componentType: string): void
}>()

// 组件分组定义
const componentGroups: ComponentGroup[] = [
  {
    label: '基础组件',
    components: [
      {
        type: 'banner',
        name: '轮播图',
        icon: 'PictureFilled',
        defaultProps: {
          images: [],
          interval: 5,
          indicator_style: 'dot',
          autoplay: true,
          border_radius: 0,
        },
      },
      {
        type: 'image',
        name: '图片',
        icon: 'Picture',
        defaultProps: {
          url: '',
          link: { type: 'none', target: '', title: '' },
          mode: 'widthFix',
          width: '100%',
        },
      },
      {
        type: 'image_text',
        name: '图文卡片',
        icon: 'Postcard',
        defaultProps: {
          layout: 'left-right',
          image_url: '',
          title: '标题文字',
          description: '描述文字',
          link: { type: 'none', target: '', title: '' },
          title_color: '#333333',
          desc_color: '#999999',
        },
      },
      {
        type: 'notice',
        name: '公告栏',
        icon: 'ChatDotSquare',
        defaultProps: {
          texts: ['欢迎来到一月一露营地'],
          speed: 50,
          background_color: '#FFF9E6',
          text_color: '#FF6600',
          icon: '',
        },
      },
      {
        type: 'nav',
        name: '快捷导航',
        icon: 'Grid',
        defaultProps: {
          items: [],
          columns: 4,
          show_label: true,
        },
      },
      {
        type: 'video',
        name: '视频',
        icon: 'VideoCamera',
        defaultProps: {
          url: '',
          poster: '',
          autoplay: false,
          loop: false,
        },
      },
    ],
  },
  {
    label: '营销组件',
    components: [
      {
        type: 'product_list',
        name: '商品列表',
        icon: 'Goods',
        defaultProps: {
          source: 'manual',
          product_ids: [],
          count: 6,
          layout: 'grid',
          columns: 2,
        },
      },
      {
        type: 'coupon',
        name: '优惠券',
        icon: 'Ticket',
        defaultProps: {
          coupon_ids: [],
          layout: 'horizontal',
        },
      },
    ],
  },
  {
    label: '辅助组件',
    components: [
      {
        type: 'rich_text',
        name: '富文本',
        icon: 'Document',
        defaultProps: {
          content: '<p>请输入内容</p>',
        },
      },
      {
        type: 'spacer',
        name: '间距',
        icon: 'Operation',
        defaultProps: {
          height: 20,
        },
      },
      {
        type: 'divider',
        name: '分割线',
        icon: 'Minus',
        defaultProps: {
          style: 'solid',
          color: '#EEEEEE',
          margin: 16,
        },
      },
    ],
  },
]

// 克隆组件（用于拖拽）
function cloneComponent(item: ComponentGroup['components'][0]) {
  return { ...item }
}
</script>

<style lang="scss" scoped>
.component-panel {
  height: 100%;
  overflow-y: auto;
  padding: 12px;
}

.panel-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: 12px;
  padding: 0 4px;
}

.component-group {
  margin-bottom: 16px;
}

.group-label {
  font-size: 12px;
  color: var(--color-text-secondary);
  margin-bottom: 8px;
  padding: 0 4px;
}

.component-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.component-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 12px 8px;
  border-radius: 8px;
  border: 1px solid var(--color-border-light, #ebeef5);
  background: var(--color-bg, #fff);
  cursor: grab;
  transition: all 0.2s ease;
  user-select: none;

  &:hover {
    border-color: var(--color-primary, #2d4a3e);
    background: var(--color-bg-warm, #faf6f0);
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  }

  &:active {
    cursor: grabbing;
  }

  .el-icon {
    color: var(--color-text-secondary);
  }

  &__name {
    font-size: 12px;
    color: var(--color-text);
    white-space: nowrap;
  }
}
</style>

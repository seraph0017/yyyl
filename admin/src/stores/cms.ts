// CMS 编辑器状态管理
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { CmsConfig, ComponentItem, CmsPage } from '@/types/cms'
import { v4 as uuidv4 } from 'uuid'

export const useCmsStore = defineStore('cms', () => {
  // ---- State ----
  const page = ref<CmsPage | null>(null)
  const config = ref<CmsConfig>({
    version: 1,
    page_settings: {
      background_color: '#faf6f0',
      title_bar_color: '#2d4a3e',
      title_bar_text_color: '#ffffff',
    },
    components: [],
  })
  const selectedComponentId = ref<string | null>(null)
  const undoStack = ref<string[]>([])     // JSON快照栈
  const redoStack = ref<string[]>([])
  const isDirty = ref(false)              // 是否有未保存修改
  const lastSavedAt = ref<string | null>(null)
  const clipboard = ref<ComponentItem | null>(null)  // 组件剪贴板
  const readonly = ref(false)             // 只读模式标志（编辑锁冲突时启用）

  // ---- Computed ----
  const selectedComponent = computed(() => {
    if (!selectedComponentId.value) return null
    return config.value.components.find(c => c.id === selectedComponentId.value) || null
  })

  const componentCount = computed(() => config.value.components.length)

  // ---- 撤销/重做 ----
  const MAX_UNDO = 50

  function pushSnapshot() {
    const snapshot = JSON.stringify(config.value)
    undoStack.value.push(snapshot)
    if (undoStack.value.length > MAX_UNDO) {
      undoStack.value.shift()
    }
    redoStack.value = []  // 新操作清空重做栈
    isDirty.value = true
  }

  function undo() {
    if (undoStack.value.length === 0) return
    redoStack.value.push(JSON.stringify(config.value))
    const prev = undoStack.value.pop()!
    config.value = JSON.parse(prev)
    isDirty.value = true
  }

  function redo() {
    if (redoStack.value.length === 0) return
    undoStack.value.push(JSON.stringify(config.value))
    const next = redoStack.value.pop()!
    config.value = JSON.parse(next)
    isDirty.value = true
  }

  // ---- 组件操作 ----

  function addComponent(type: string, defaultProps: Record<string, any>, index?: number) {
    // 组件数量上限30检查
    if (config.value.components.length >= 30) {
      ElMessage.warning('组件数量已达上限（30个），请拆分页面')
      return
    }
    pushSnapshot()
    const newComp: ComponentItem = {
      id: uuidv4(),
      type,
      props: { ...defaultProps },
      style: { margin_top: 0, margin_bottom: 10 },
    }
    if (index !== undefined) {
      config.value.components.splice(index, 0, newComp)
    } else {
      config.value.components.push(newComp)
    }
    selectedComponentId.value = newComp.id
  }

  function removeComponent(id: string) {
    pushSnapshot()
    const idx = config.value.components.findIndex(c => c.id === id)
    if (idx > -1) {
      config.value.components.splice(idx, 1)
      if (selectedComponentId.value === id) {
        selectedComponentId.value = null
      }
    }
  }

  function moveComponent(fromIndex: number, toIndex: number) {
    pushSnapshot()
    const [item] = config.value.components.splice(fromIndex, 1)
    config.value.components.splice(toIndex, 0, item)
  }

  function duplicateComponent(id: string) {
    pushSnapshot()
    const idx = config.value.components.findIndex(c => c.id === id)
    if (idx > -1) {
      const copy: ComponentItem = JSON.parse(JSON.stringify(config.value.components[idx]))
      copy.id = uuidv4()
      config.value.components.splice(idx + 1, 0, copy)
      selectedComponentId.value = copy.id
    }
  }

  function copyToClipboard(id: string) {
    const comp = config.value.components.find(c => c.id === id)
    if (comp) {
      clipboard.value = JSON.parse(JSON.stringify(comp))
    }
  }

  function pasteFromClipboard() {
    if (!clipboard.value) return
    if (config.value.components.length >= 30) {
      ElMessage.warning('组件数量已达上限（30个），请拆分页面')
      return
    }
    pushSnapshot()
    const pasted: ComponentItem = JSON.parse(JSON.stringify(clipboard.value))
    pasted.id = uuidv4()
    // 粘贴到选中组件后面，或列表末尾
    const idx = selectedComponentId.value
      ? config.value.components.findIndex(c => c.id === selectedComponentId.value)
      : -1
    if (idx > -1) {
      config.value.components.splice(idx + 1, 0, pasted)
    } else {
      config.value.components.push(pasted)
    }
    selectedComponentId.value = pasted.id
  }

  function updateComponentProps(id: string, props: Record<string, any>) {
    pushSnapshot()
    const comp = config.value.components.find(c => c.id === id)
    if (comp) {
      comp.props = { ...comp.props, ...props }
    }
  }

  function updateComponentStyle(id: string, style: Partial<ComponentItem['style']>) {
    pushSnapshot()
    const comp = config.value.components.find(c => c.id === id)
    if (comp) {
      comp.style = { ...comp.style, ...style }
    }
  }

  // ---- 初始化/重置 ----

  function initFromPage(pageData: CmsPage) {
    page.value = pageData
    if (pageData.draft_config) {
      config.value = JSON.parse(JSON.stringify(pageData.draft_config))
    } else {
      config.value = {
        version: 1,
        page_settings: { background_color: '#faf6f0', title_bar_color: '#2d4a3e', title_bar_text_color: '#ffffff' },
        components: [],
      }
    }
    undoStack.value = []
    redoStack.value = []
    isDirty.value = false
    selectedComponentId.value = null
  }

  function $reset() {
    page.value = null
    config.value = { version: 1, page_settings: { background_color: '#faf6f0', title_bar_color: '#2d4a3e', title_bar_text_color: '#ffffff' }, components: [] }
    selectedComponentId.value = null
    undoStack.value = []
    redoStack.value = []
    isDirty.value = false
    lastSavedAt.value = null
    clipboard.value = null
    readonly.value = false
  }

  return {
    page, config, selectedComponentId, undoStack, redoStack, isDirty, lastSavedAt, clipboard, readonly,
    selectedComponent, componentCount,
    pushSnapshot, undo, redo,
    addComponent, removeComponent, moveComponent, duplicateComponent,
    copyToClipboard, pasteFromClipboard,
    updateComponentProps, updateComponentStyle,
    initFromPage, $reset,
  }
})

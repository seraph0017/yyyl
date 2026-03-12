<template>
  <el-container class="layout-container">
    <!-- 侧边栏 -->
    <el-aside :width="appStore.sidebarCollapsed ? '64px' : '220px'" class="layout-aside">
      <div class="logo-container">
        <img src="@/assets/logo.svg" alt="logo" class="logo-icon" />
        <span v-if="!appStore.sidebarCollapsed" class="logo-text">某露营地</span>
      </div>
      <el-scrollbar>
        <el-menu
          :default-active="activeMenu"
          :collapse="appStore.sidebarCollapsed"
          router
          class="sidebar-menu"
          background-color="#1a1a2e"
          text-color="#a0a0b8"
          active-text-color="#4CAF50"
        >
          <template v-for="item in menuItems" :key="item.path">
            <el-menu-item v-if="!item.children" :index="item.path">
              <el-icon><component :is="item.icon" /></el-icon>
              <template #title>{{ item.title }}</template>
            </el-menu-item>
            <el-sub-menu v-else :index="item.path">
              <template #title>
                <el-icon><component :is="item.icon" /></el-icon>
                <span>{{ item.title }}</span>
              </template>
              <el-menu-item
                v-for="child in item.children"
                :key="child.path"
                :index="child.path"
              >
                {{ child.title }}
              </el-menu-item>
            </el-sub-menu>
          </template>
        </el-menu>
      </el-scrollbar>
    </el-aside>

    <!-- 主区域 -->
    <el-container>
      <!-- 顶栏 -->
      <el-header class="layout-header">
        <div class="header-left">
          <el-icon class="collapse-btn" @click="appStore.toggleSidebar">
            <Fold v-if="!appStore.sidebarCollapsed" />
            <Expand v-else />
          </el-icon>
          <el-breadcrumb separator="/">
            <el-breadcrumb-item
              v-for="item in breadcrumbs"
              :key="item.path"
              :to="item.path ? { path: item.path } : undefined"
            >
              {{ item.title }}
            </el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        <div class="header-right">
          <el-dropdown trigger="click" @command="handleCommand">
            <div class="user-info">
              <el-avatar :size="32" :src="userStore.userInfo?.avatar">
                {{ userStore.userInfo?.real_name?.charAt(0) || 'A' }}
              </el-avatar>
              <span class="username">{{ userStore.userInfo?.real_name || '管理员' }}</span>
              <el-icon><ArrowDown /></el-icon>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item>
                  <el-tag size="small" type="success">{{ userStore.roleName }}</el-tag>
                </el-dropdown-item>
                <el-dropdown-item divided command="logout">
                  <el-icon><SwitchButton /></el-icon>退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <!-- 内容区 -->
      <el-main class="layout-main">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <keep-alive :include="cachedViews">
              <component :is="Component" />
            </keep-alive>
          </transition>
        </router-view>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAppStore } from '@/stores/app'
import { useUserStore } from '@/stores/user'
import {
  Fold, Expand, ArrowDown, SwitchButton,
  DataAnalysis, Calendar, Goods, List, User,
  Money, TrendCharts, ChatLineSquare, Document,
  Bell, UserFilled, Setting, Notebook,
} from '@element-plus/icons-vue'

const route = useRoute()
const appStore = useAppStore()
const userStore = useUserStore()

// 缓存的视图
const cachedViews = ['Dashboard', 'Products', 'Orders', 'Members']

// 当前激活菜单
const activeMenu = computed(() => {
  const { activeMenu } = route.meta
  if (activeMenu) return activeMenu as string
  return route.path
})

// 面包屑
const breadcrumbs = computed(() => {
  const matched = route.matched.filter(item => item.meta?.title)
  return matched.map(item => ({
    path: item.path,
    title: item.meta.title as string,
  }))
})

// 菜单配置
const menuItems = computed(() => {
  const items = [
    { path: '/dashboard', title: 'Dashboard', icon: DataAnalysis },
    { path: '/calendar', title: '营地日历', icon: Calendar },
    { path: '/products', title: '商品管理', icon: Goods },
    { path: '/orders', title: '订单管理', icon: List },
    {
      path: '/member-group',
      title: '会员管理',
      icon: User,
      children: [
        { path: '/members', title: '会员列表' },
        { path: '/annual-cards', title: '年卡管理' },
        { path: '/times-cards', title: '次数卡管理' },
      ],
    },
    { path: '/finance', title: '财务管理', icon: Money },
    { path: '/reports', title: '数据统计', icon: TrendCharts },
    {
      path: '/content-group',
      title: '内容管理',
      icon: Document,
      children: [
        { path: '/faq', title: 'FAQ管理' },
        { path: '/pages', title: '页面编辑' },
        { path: '/notifications', title: '消息管理' },
      ],
    },
    {
      path: '/system-group',
      title: '系统设置',
      icon: Setting,
      children: [
        { path: '/staff', title: '员工管理' },
        { path: '/settings', title: '系统设置' },
        { path: '/logs', title: '操作日志' },
      ],
    },
  ]

  // 非管理员隐藏部分菜单
  if (!userStore.isAdmin) {
    return items.filter(item => !['finance', '/system-group'].includes(item.path))
  }
  return items
})

function handleCommand(command: string) {
  if (command === 'logout') {
    userStore.logout()
  }
}
</script>

<style lang="scss" scoped>
.layout-container {
  height: 100vh;
  overflow: hidden;
}

.layout-aside {
  background: #1a1a2e;
  transition: width 0.3s;
  overflow: hidden;

  .logo-container {
    height: 60px;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    padding: 0 16px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.06);

    .logo-icon {
      width: 32px;
      height: 32px;
    }

    .logo-text {
      font-size: 18px;
      font-weight: 600;
      color: #fff;
      white-space: nowrap;
    }
  }

  .sidebar-menu {
    border: none;

    :deep(.el-menu-item.is-active) {
      background: rgba(76, 175, 80, 0.15);
      border-right: 3px solid #4CAF50;
    }
  }
}

.layout-header {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  background: #fff;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
  z-index: 10;

  .header-left {
    display: flex;
    align-items: center;
    gap: 16px;

    .collapse-btn {
      font-size: 20px;
      cursor: pointer;
      color: #606266;
      &:hover { color: var(--color-primary); }
    }
  }

  .header-right {
    .user-info {
      display: flex;
      align-items: center;
      gap: 8px;
      cursor: pointer;
      .username {
        font-size: 14px;
        color: #303133;
      }
    }
  }
}

.layout-main {
  background: var(--color-bg);
  overflow-y: auto;
  padding: 0;
}

// 路由切换动画
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>

<template>
  <el-container class="layout-container">
    <!-- 侧边栏 -->
    <el-aside :width="appStore.sidebarCollapsed ? '68px' : '240px'" class="layout-aside">
      <div class="sidebar-brand">
        <img src="@/assets/logo.svg" alt="logo" class="sidebar-brand__logo" />
        <transition name="fade-text">
          <span v-if="!appStore.sidebarCollapsed" class="sidebar-brand__name">{{ brand.name }}</span>
        </transition>
      </div>
      <el-scrollbar class="sidebar-scroll">
        <el-menu
          :default-active="activeMenu"
          :collapse="appStore.sidebarCollapsed"
          router
          class="sidebar-menu"
          background-color="transparent"
          text-color="#8a9a90"
          active-text-color="#7ed4a0"
        >
          <template v-for="item in menuItems" :key="item.path">
            <el-menu-item v-if="!item.children" :index="item.path" class="sidebar-menu-item">
              <el-icon><component :is="item.icon" /></el-icon>
              <template #title>{{ item.title }}</template>
            </el-menu-item>
            <el-sub-menu v-else :index="item.path" class="sidebar-submenu">
              <template #title>
                <el-icon><component :is="item.icon" /></el-icon>
                <span>{{ item.title }}</span>
              </template>
              <el-menu-item
                v-for="child in item.children"
                :key="child.path"
                :index="child.path"
                class="sidebar-menu-item sidebar-menu-item--child"
              >
                {{ child.title }}
              </el-menu-item>
            </el-sub-menu>
          </template>
        </el-menu>
      </el-scrollbar>

      <!-- 侧边栏底部版本号 -->
      <div class="sidebar-footer" v-if="!appStore.sidebarCollapsed">
        <span class="sidebar-footer__version">v1.5</span>
      </div>
    </el-aside>

    <!-- 主区域 -->
    <el-container class="layout-body">
      <!-- 顶栏 -->
      <el-header class="layout-header">
        <div class="header-left">
          <div class="collapse-btn" @click="appStore.toggleSidebar">
            <el-icon :size="18">
              <Fold v-if="!appStore.sidebarCollapsed" />
              <Expand v-else />
            </el-icon>
          </div>
          <el-breadcrumb separator="/" class="header-breadcrumb">
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
            <div class="user-capsule">
              <el-avatar :size="30" :src="userStore.userInfo?.avatar" class="user-capsule__avatar">
                {{ userStore.userInfo?.real_name?.charAt(0) || 'A' }}
              </el-avatar>
              <span class="user-capsule__name">{{ userStore.userInfo?.real_name || '管理员' }}</span>
              <el-icon :size="12"><ArrowDown /></el-icon>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item disabled>
                  <el-tag size="small" effect="plain" type="success" round>{{ userStore.roleName }}</el-tag>
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
          <transition name="page-fade" mode="out-in">
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
import { brandConfig as brand } from '@/config/brand'
import {
  Fold, Expand, ArrowDown, SwitchButton,
  DataAnalysis, Calendar, Goods, List, User,
  Money, TrendCharts, ChatLineSquare, Document,
  Bell, UserFilled, Setting, Notebook, Place,
  Connection, MapLocation, Aim, Timer, Wallet, DataLine, Trophy,
} from '@element-plus/icons-vue'

const route = useRoute()
const appStore = useAppStore()
const userStore = useUserStore()

const cachedViews = ['Dashboard', 'Products', 'Campsites', 'Orders', 'Members']

const activeMenu = computed(() => {
  const { activeMenu } = route.meta
  if (activeMenu) return activeMenu as string
  return route.path
})

const breadcrumbs = computed(() => {
  const matched = route.matched.filter(item => item.meta?.title)
  return matched.map(item => ({
    path: item.path,
    title: item.meta.title as string,
  }))
})

const menuItems = computed(() => {
  const items = [
    { path: '/dashboard', title: 'Dashboard', icon: DataAnalysis },
    { path: '/calendar', title: '营地日历', icon: Calendar },
    { path: '/campsites', title: '营位管理', icon: Place },
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
      path: '/ops-group',
      title: '运营管理',
      icon: Connection,
      children: [
        { path: '/bundles', title: '搭配组合' },
        { path: '/seckill-monitor', title: '秒杀监控' },
        { path: '/camp-maps', title: '营地地图' },
        { path: '/games', title: '游戏管理' },
      ],
    },
    {
      path: '/work-group',
      title: '工作系统',
      icon: Wallet,
      children: [
        { path: '/expenses', title: '报销管理' },
        { path: '/expense-stats', title: '报销统计' },
        { path: '/performance', title: '绩效管理' },
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

  if (!userStore.isAdmin) {
    return items.filter(item => !['finance', '/system-group', '/work-group'].includes(item.path))
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

// ==================== 侧边栏 — 深邃森林 ====================
.layout-aside {
  background: var(--color-sidebar);
  transition: width 0.4s var(--ease-out-expo);
  overflow: hidden;
  position: relative;

  // 右侧微光分割线
  &::after {
    content: '';
    position: absolute;
    top: 0;
    right: 0;
    bottom: 0;
    width: 1px;
    background: linear-gradient(
      180deg,
      transparent 0%,
      rgba(61, 139, 94, 0.15) 30%,
      rgba(200, 168, 114, 0.1) 70%,
      transparent 100%
    );
  }
}

.sidebar-brand {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 0 18px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);

  &__logo {
    width: 30px;
    height: 30px;
    flex-shrink: 0;
    filter: drop-shadow(0 0 8px rgba(61, 139, 94, 0.3));
  }

  &__name {
    font-size: 17px;
    font-weight: 700;
    color: #e0e8e4;
    white-space: nowrap;
    letter-spacing: 2px;
  }
}

.sidebar-scroll {
  flex: 1;
  overflow: hidden;
}

.sidebar-menu {
  border: none;
  padding: 8px 0;

  :deep(.el-menu-item) {
    height: 44px;
    line-height: 44px;
    margin: 2px 8px;
    border-radius: 8px;
    font-size: 13px;
    letter-spacing: 0.5px;
    transition: all 0.25s ease;

    &:hover {
      background: var(--color-sidebar-hover) !important;
    }

    &.is-active {
      background: var(--color-sidebar-active) !important;
      color: var(--color-text-sidebar-active) !important;
      font-weight: 600;
      position: relative;

      &::before {
        content: '';
        position: absolute;
        left: 0;
        top: 50%;
        transform: translateY(-50%);
        width: 3px;
        height: 18px;
        background: linear-gradient(180deg, var(--color-primary-light), var(--color-accent));
        border-radius: 0 3px 3px 0;
      }
    }
  }

  :deep(.el-sub-menu) {
    .el-sub-menu__title {
      height: 44px;
      line-height: 44px;
      margin: 2px 8px;
      border-radius: 8px;
      font-size: 13px;
      letter-spacing: 0.5px;

      &:hover {
        background: var(--color-sidebar-hover) !important;
      }
    }
  }
}

.sidebar-footer {
  padding: 12px 18px;
  border-top: 1px solid rgba(255, 255, 255, 0.04);

  &__version {
    font-size: 11px;
    color: rgba(138, 154, 144, 0.4);
    letter-spacing: 1px;
  }
}

// ==================== 主体区域 ====================
.layout-body {
  flex: 1;
  overflow: hidden;
}

// ==================== 顶栏 ====================
.layout-header {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(20px);
  border-bottom: 1px solid var(--color-border-light);
  z-index: 10;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.collapse-btn {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  cursor: pointer;
  color: var(--color-text-secondary);
  transition: var(--transition-base);

  &:hover {
    background: var(--color-bg-warm);
    color: var(--color-primary);
  }
}

.header-breadcrumb {
  :deep(.el-breadcrumb__item) {
    .el-breadcrumb__inner {
      font-weight: 400;
      color: var(--color-text-placeholder);
      letter-spacing: 0.3px;
    }

    &:last-child .el-breadcrumb__inner {
      color: var(--color-text);
      font-weight: 500;
    }
  }
}

.header-right {
  display: flex;
  align-items: center;
}

.user-capsule {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 12px 4px 4px;
  border-radius: 20px;
  cursor: pointer;
  transition: var(--transition-base);
  border: 1px solid transparent;

  &:hover {
    background: var(--color-bg-warm);
    border-color: var(--color-border-light);
  }

  &__avatar {
    background: linear-gradient(135deg, var(--color-primary), var(--color-primary-light));
    font-size: 12px;
    font-weight: 600;
    color: #fff;
  }

  &__name {
    font-size: 13px;
    color: var(--color-text);
    font-weight: 500;
    letter-spacing: 0.5px;
  }
}

// ==================== 内容区 ====================
.layout-main {
  background: var(--color-bg);
  overflow-y: auto;
  padding: 0;
}

// ==================== 路由动画 ====================
.page-fade-enter-active {
  transition: opacity 0.25s ease, transform 0.25s ease;
}
.page-fade-leave-active {
  transition: opacity 0.15s ease;
}
.page-fade-enter-from {
  opacity: 0;
  transform: translateY(8px);
}
.page-fade-leave-to {
  opacity: 0;
}

// ==================== 文字淡入淡出 ====================
.fade-text-enter-active,
.fade-text-leave-active {
  transition: opacity 0.2s ease;
}
.fade-text-enter-from,
.fade-text-leave-to {
  opacity: 0;
}
</style>

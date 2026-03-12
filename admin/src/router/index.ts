// 某露营地 — 路由配置
import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import NProgress from 'nprogress'
import 'nprogress/nprogress.css'
import { getToken } from '@/utils/request'

NProgress.configure({ showSpinner: false })

// 公共路由
const publicRoutes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/login/index.vue'),
    meta: { title: '登录', public: true },
  },
]

// 管理后台路由
const adminRoutes: RouteRecordRaw[] = [
  {
    path: '/',
    component: () => import('@/layout/index.vue'),
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/dashboard/index.vue'),
        meta: { title: 'Dashboard', icon: 'DataAnalysis' },
      },
      {
        path: 'calendar',
        name: 'Calendar',
        component: () => import('@/views/calendar/index.vue'),
        meta: { title: '营地日历', icon: 'Calendar' },
      },
      // 商品管理
      {
        path: 'products',
        name: 'Products',
        component: () => import('@/views/products/index.vue'),
        meta: { title: '商品管理', icon: 'Goods' },
      },
      {
        path: 'products/create',
        name: 'ProductCreate',
        component: () => import('@/views/products/edit.vue'),
        meta: { title: '新增商品', hidden: true, activeMenu: '/products' },
      },
      {
        path: 'products/:id/edit',
        name: 'ProductEdit',
        component: () => import('@/views/products/edit.vue'),
        meta: { title: '编辑商品', hidden: true, activeMenu: '/products' },
      },
      // 订单管理
      {
        path: 'orders',
        name: 'Orders',
        component: () => import('@/views/orders/index.vue'),
        meta: { title: '订单管理', icon: 'List' },
      },
      {
        path: 'orders/:id',
        name: 'OrderDetail',
        component: () => import('@/views/orders/detail.vue'),
        meta: { title: '订单详情', hidden: true, activeMenu: '/orders' },
      },
      // 会员管理
      {
        path: 'members',
        name: 'Members',
        component: () => import('@/views/members/index.vue'),
        meta: { title: '会员管理', icon: 'User' },
      },
      {
        path: 'members/:id',
        name: 'MemberDetail',
        component: () => import('@/views/members/detail.vue'),
        meta: { title: '会员详情', hidden: true, activeMenu: '/members' },
      },
      {
        path: 'annual-cards',
        name: 'AnnualCards',
        component: () => import('@/views/members/annual-cards.vue'),
        meta: { title: '年卡管理', icon: 'Ticket', hidden: true, activeMenu: '/members' },
      },
      {
        path: 'times-cards',
        name: 'TimesCards',
        component: () => import('@/views/members/times-cards.vue'),
        meta: { title: '次数卡管理', icon: 'Ticket', hidden: true, activeMenu: '/members' },
      },
      // 财务管理
      {
        path: 'finance',
        name: 'Finance',
        component: () => import('@/views/finance/index.vue'),
        meta: { title: '财务管理', icon: 'Money', roles: ['admin', 'super_admin'] },
      },
      // 数据统计
      {
        path: 'reports',
        name: 'Reports',
        component: () => import('@/views/reports/index.vue'),
        meta: { title: '数据统计', icon: 'TrendCharts' },
      },
      // 内容管理
      {
        path: 'faq',
        name: 'FAQ',
        component: () => import('@/views/content/faq.vue'),
        meta: { title: 'FAQ管理', icon: 'ChatLineSquare' },
      },
      {
        path: 'pages',
        name: 'PageEdit',
        component: () => import('@/views/content/pages.vue'),
        meta: { title: '页面编辑', icon: 'Document' },
      },
      {
        path: 'notifications',
        name: 'Notifications',
        component: () => import('@/views/content/notifications.vue'),
        meta: { title: '消息管理', icon: 'Bell' },
      },
      // 系统设置
      {
        path: 'staff',
        name: 'Staff',
        component: () => import('@/views/system/staff.vue'),
        meta: { title: '员工管理', icon: 'UserFilled', roles: ['admin', 'super_admin'] },
      },
      {
        path: 'settings',
        name: 'Settings',
        component: () => import('@/views/system/settings.vue'),
        meta: { title: '系统设置', icon: 'Setting', roles: ['admin', 'super_admin'] },
      },
      {
        path: 'logs',
        name: 'Logs',
        component: () => import('@/views/system/logs.vue'),
        meta: { title: '操作日志', icon: 'Notebook' },
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes: [...publicRoutes, ...adminRoutes],
})

// 路由守卫
router.beforeEach((to, _from, next) => {
  NProgress.start()
  document.title = `${to.meta.title || '管理后台'} - 某露营地`

  const token = getToken()

  if (to.meta.public) {
    // 公共页面，已登录则跳Dashboard
    if (token && to.path === '/login') {
      next('/dashboard')
    } else {
      next()
    }
  } else {
    // 需要登录
    if (!token) {
      next(`/login?redirect=${to.path}`)
    } else {
      // 角色权限检查
      const requiredRoles = to.meta.roles as string[] | undefined
      if (requiredRoles) {
        const userInfo = JSON.parse(localStorage.getItem('user_info') || '{}')
        const userRole = userInfo?.role?.role_code
        if (userRole && requiredRoles.includes(userRole)) {
          next()
        } else {
          next('/dashboard')
        }
      } else {
        next()
      }
    }
  }
})

router.afterEach(() => {
  NProgress.done()
})

export default router

// 扩展 vue-router 的 RouteMeta 类型
declare module 'vue-router' {
  interface RouteMeta {
    title?: string
    icon?: string
    hidden?: boolean
    public?: boolean
    roles?: string[]
    activeMenu?: string
  }
}

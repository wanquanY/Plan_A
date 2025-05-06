import { createRouter, createWebHistory } from 'vue-router';
import Home from '../views/Home.vue';
import Login from '../views/Login.vue';
import Register from '../views/Register.vue';
import Test from '../views/Test.vue';
import UserProfile from '../views/UserProfile.vue';
import AgentManagement from '../views/AgentManagement.vue';
import GlobalLayout from '../components/GlobalLayout.vue';
import authService from '../services/auth';

const routes = [
  {
    path: '/',
    component: GlobalLayout,
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        name: 'Home',
        component: Home
      },
      {
        path: 'test',
        name: 'Test',
        component: Test
      },
      {
        path: 'user-profile',
        name: 'UserProfile',
        component: UserProfile
      },
      {
        path: 'agent-management',
        name: 'AgentManagement',
        component: AgentManagement
      }
    ]
  },
  {
    path: '/login',
    name: 'Login',
    component: Login,
    meta: { guest: true }
  },
  {
    path: '/register',
    name: 'Register',
    component: Register,
    meta: { guest: true }
  },
  // 路由重定向
  {
    path: '/:pathMatch(.*)*',
    redirect: '/'
  }
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

// 全局路由守卫
router.beforeEach((to, from, next) => {
  const isAuthenticated = authService.isAuthenticated();
  
  // 需要登录的路由
  if (to.matched.some(record => record.meta.requiresAuth)) {
    if (!isAuthenticated) {
      next({ name: 'Login' });
    } else {
      next();
    }
  } 
  // 游客路由（登录/注册）
  else if (to.matched.some(record => record.meta.guest)) {
    if (isAuthenticated) {
      next({ name: 'Home' });
    } else {
      next();
    }
  } else {
    next();
  }
});

export default router; 
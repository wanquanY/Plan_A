import { createRouter, createWebHistory } from 'vue-router';
import Home from '../views/Home.vue';
import Login from '../views/Login.vue';
import Register from '../views/Register.vue';
import Test from '../views/Test.vue';
import UserProfile from '../views/UserProfile.vue';
import CreateAgent from '../views/CreateAgent.vue';
import Settings from '../views/Settings.vue';
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
        path: 'latex-test',
        name: 'LatexTest',
        component: () => import('../components/editor/LatexTest.vue')
      },
      {
        path: 'user-profile',
        name: 'UserProfile',
        component: UserProfile
      },
      {
        path: 'agent/edit',
        name: 'EditAgent',
        component: CreateAgent
      },
      {
        path: 'settings',
        name: 'Settings',
        component: Settings
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
router.beforeEach(async (to, from, next) => {
  const isAuthenticated = authService.isAuthenticated();
  
  // 需要登录的路由
  if (to.matched.some(record => record.meta.requiresAuth)) {
    if (!isAuthenticated) {
      next({ name: 'Login' });
    } else {
      // 如果用户已登录且访问根路径，且没有指定笔记ID，则自动跳转到最新笔记
      if (to.name === 'Home' && !to.query.note && !to.query.sessionId) {
        try {
          // 动态导入noteService以避免循环依赖
          const { default: noteService } = await import('../services/note');
          const { notes } = await noteService.getNotes(1, 1); // 获取第一页的第一条笔记（最新的）
          
          if (notes && notes.length > 0) {
            const latestNote = notes[0];
            console.log('自动跳转到最新笔记:', latestNote.id);
            next({ name: 'Home', query: { note: latestNote.id } });
            return;
          }
        } catch (error) {
          console.error('获取最新笔记失败:', error);
          // 如果获取失败，继续正常导航
        }
      }
      next();
    }
  } 
  // 游客路由（登录/注册）
  else if (to.matched.some(record => record.meta.guest)) {
    if (isAuthenticated) {
      // 登录成功后，自动跳转到最新笔记
      try {
        const { default: noteService } = await import('../services/note');
        const { notes } = await noteService.getNotes(1, 1); // 获取第一页的第一条笔记（最新的）
        
        if (notes && notes.length > 0) {
          const latestNote = notes[0];
          console.log('登录后自动跳转到最新笔记:', latestNote.id);
          next({ name: 'Home', query: { note: latestNote.id } });
          return;
        }
      } catch (error) {
        console.error('获取最新笔记失败:', error);
      }
      next({ name: 'Home' });
    } else {
      next();
    }
  } else {
    next();
  }
});

export default router; 
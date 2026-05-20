import { createRouter, createWebHistory } from "vue-router";

const routes = [
  {
    path: "/login",
    name: "Login",
    component: () => import("../views/Login.vue"),
    meta: { guest: true },
  },
  {
    path: "/signup",
    name: "Signup",
    component: () => import("../views/Signup.vue"),
    meta: { guest: true },
  },
  {
    path: "/",
    name: "Home",
    component: () => import("../views/Home.vue"),
    meta: { requiresAuth: true },
  },
  {
    path: "/agent",
    name: "StockAgent",
    component: () => import("../views/StockAgent.vue"),
    meta: { requiresAuth: true },
  },
  {
    path: "/agent/:id",
    name: "StockAgentChat",
    component: () => import("../views/StockAgent.vue"),
    meta: { requiresAuth: true },
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem("access_token");

  if (to.meta.requiresAuth && !token) {
    next({ name: "Login", query: { redirect: to.fullPath } });
  } else if (to.meta.guest && token) {
    next({ name: "Home" });
  } else {
    next();
  }
});

export default router;

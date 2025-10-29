<!-- components/Navbar.vue -->
<template>
  <nav
    class="w-full px-6 py-4 flex justify-between items-center text-white bg-[#0d1117] flex-shrink-0"
  >
    <h1 class="text-2xl font-bold text-cyan-400">
      <span
        ><router-link to="/"
          >Jekk's Dashboard Automation Trading Bot</router-link
        ></span
      >
    </h1>
    <ul class="flex gap-6 font-medium">
      <li>
        <router-link to="/dashboard" class="hover:text-cyan-300"
          >Dashboard</router-link
        >
      </li>
    </ul>
  </nav>
</template>

<!-- components/Navbar.vue -->
<template>
  <nav
    class="w-full px-6 py-4 flex justify-between items-center text-white bg-[#0d1117] flex-shrink-0"
  >
    <h1 class="text-2xl font-bold text-cyan-400">
      <router-link to="/admin/dashboard" class="hover:text-cyan-300"
        >Jekk's Portfolio</router-link
      >
    </h1>
    <ul class="flex gap-6 font-medium">
      <li>
        <router-link to="/admin/projects" class="hover:text-cyan-300"
          >Projects</router-link
        >
      </li>
      <li>
        <router-link to="/about" class="hover:text-cyan-300">About</router-link>
      </li>
      <li>
        <router-link to="/contact" class="hover:text-cyan-300"
          >Contact</router-link
        >
      </li>
    </ul>
  </nav>
</template>

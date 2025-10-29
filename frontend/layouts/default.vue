<!-- layouts/default.vue -->
<template>
  <div class="bg-[#0d1117] text-white min-h-screen font-sans flex flex-col">
    <Navbar />
    <main class="flex-1">
      <Transition name="fade">
        <div
          v-if="flash"
          class="fixed top-4 left-1/2 -translate-x-1/2 z-50 bg-cyan-500 text-white px-4 py-2 rounded shadow-lg"
        >
          {{ flash }}
        </div>
      </Transition>
      <slot />
    </main>
  </div>
</template>

<script setup>
import Navbar from "@/components/Navbar.vue"
const { flash } = useFlash()
useHead({
  meta: [
    { charset: "utf-8" },
    { name: "viewport", content: "width=device-width, initial-scale=1" },
    { name: "theme-color", content: "#0d1117" },
  ],
  link: [{ rel: "icon", href: "/fvg.ico", type: "image/png/x-icon/svg" }],
})
</script>

<style scoped>
@import url("https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap");
</style>
<style scoped>
/* ✨ Fade transition */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.4s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>

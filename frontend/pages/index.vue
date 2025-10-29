<!-- pages/index.vue -->
<template>
  <section
    class="flex flex-col items-center justify-center text-center h-full px-4 py-8"
  >
    <NuxtImg
      src="/assets/hero-dark.png"
      alt="Hero Image"
      class="w-full h-[70vh] max-w-4xl mb-8 rounded-xl shadow-xl"
      format="webp"
      loading="lazy"
      quality="80"
    />
    <h1 class="text-4xl sm:text-5xl font-extrabold text-cyan-400">
      Welcome to My Portfolio
    </h1>
    <p class="mt-4 text-gray-400 text-lg max-w-xl">
      Developer. Creator. Dreamer. Dive into my projects and experience.
    </p>
    <div class="mt-6">
      <NuxtLink
        to="/projects"
        class="px-6 py-3 bg-cyan-500 text-black font-semibold rounded-xl hover:bg-cyan-400 transition"
      >
        View Projects
      </NuxtLink>
    </div>
  </section>
</template>

<script setup>
useMeta({
  title: "Home",
  description: "Web For Coffee Lovers",
})
</script>

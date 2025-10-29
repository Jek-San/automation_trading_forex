export default defineNuxtConfig({
  ssr: true,
  nitro: {
    preset: "static",
  },

  runtimeConfig: {
    public: {
      API_BASE_URL: process.env.NUXT_PUBLIC_API_BASE_URL,
    },
  },
  css: [
    "@vueup/vue-quill/dist/vue-quill.snow.css",
    "~/assets/css/main.css",
    "~/assets/css/quill-dark.css",
  ],
  modules: [
    "@nuxtjs/tailwindcss",
    "@nuxt/image",
    "@nuxt/eslint",
    "@nuxt/icon",
    "@nuxt/ui",
  ],
})

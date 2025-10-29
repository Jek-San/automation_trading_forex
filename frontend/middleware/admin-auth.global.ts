export default defineNuxtRouteMiddleware((to) => {
  const token = useCookie("token")

  // If going to /admin/* but not /admin/login and not logged in
  if (
    to.path.startsWith("/admin") &&
    to.path !== "/admin/login" &&
    !token.value
  ) {
    return navigateTo("/admin/login")
  }
})

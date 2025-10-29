// composables/useAuth.ts

export const useAuth = () => {
  const token = useCookie<string | null>("token") // universal (SSR + browser)

  const isLoggedIn = computed(() => !!token.value)

  const login = (jwt: string) => {
    token.value = jwt
  }

  const logout = () => {
    token.value = null
  }

  return {
    token,
    isLoggedIn,
    login,
    logout,
  }
}

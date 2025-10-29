export const useApi = async (
  path: string,
  options: any = {},
  withAuth: boolean = false // 👈 this decides whether to attach token
) => {
  const config = useRuntimeConfig()
  const url = `${config.public.API_BASE_URL}/${path}`
  console.log(url)
  if (withAuth) {
    const token = useCookie("token")
    options.headers = {
      ...(options.headers || {}),
      Authorization: token.value ? `Bearer ${token.value}` : undefined,
    }
  }

  return await $fetch(url, options)
}

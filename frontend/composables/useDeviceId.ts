import { v4 as uuidv4 } from "uuid"

export const useDeviceId = () => {
  const key = "device_id"

  const getDeviceId = () => {
    let id = localStorage.getItem(key)
    if (!id) {
      id = uuidv4()
      localStorage.setItem(key, id)
    }
    return id
  }

  return { getDeviceId }
}

import type { ManualLocationInput } from './types'

const LOCAL_PIN_KEY = 'forestguard.local-preview-pin.v1'

export function isValidLocalPin(value: unknown): value is ManualLocationInput {
  if (!value || typeof value !== 'object') return false
  const pin = value as Partial<ManualLocationInput>
  return typeof pin.lat === 'number' && Number.isFinite(pin.lat) &&
    typeof pin.lng === 'number' && Number.isFinite(pin.lng) &&
    pin.lat >= -90 && pin.lat <= 90 && pin.lng >= -180 && pin.lng <= 180
}

export function loadLocalPin(): ManualLocationInput | undefined {
  try {
    const stored: unknown = JSON.parse(window.localStorage.getItem(LOCAL_PIN_KEY) ?? 'null')
    return isValidLocalPin(stored) ? stored : undefined
  } catch {
    return undefined
  }
}

export function persistLocalPin(pin?: ManualLocationInput) {
  try {
    if (pin) {
      window.localStorage.setItem(LOCAL_PIN_KEY, JSON.stringify(pin))
    } else {
      window.localStorage.removeItem(LOCAL_PIN_KEY)
    }
  } catch {
    // ยังปักหมุดในหน้าปัจจุบันได้ แม้เบราว์เซอร์จะปิด localStorage
  }
}

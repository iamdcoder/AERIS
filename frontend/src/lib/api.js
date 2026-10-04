const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'

export async function getAirspace() {
  const response = await fetch(`${API_BASE}/airspace`)
  if (!response.ok) throw new Error('Failed to load airspace')
  return response.json()
}

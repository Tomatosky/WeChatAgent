import { withApiBase } from './base'

export interface Book {
  id: number
  title: string
  author?: string | null
  cover_url?: string | null
  file_name: string
  file_path: string
  status: string
  status_detail?: string | null
  ai_friend_id?: number | null
  reading_location?: string | null
  create_time: string
  update_time: string
  deleted: boolean
  file_size?: number | null
  format_type: string
}

async function parseError(response: Response, fallback: string): Promise<string> {
  try {
    const data = await response.json()
    if (typeof data?.detail === 'string' && data.detail.trim()) {
      return data.detail
    }
  } catch {
    // ignore json parse errors
  }
  return fallback
}

export async function getBooks(skip: number = 0, limit: number = 100): Promise<Book[]> {
  const params = new URLSearchParams({
    skip: skip.toString(),
    limit: limit.toString(),
  })
  const response = await fetch(withApiBase(`/api/books/?${params}`))
  if (!response.ok) {
    throw new Error(await parseError(response, '获取图书列表失败'))
  }
  return response.json()
}

export async function importBook(file: File): Promise<Book> {
  const formData = new FormData()
  formData.append('file', file)

  const response = await fetch(withApiBase('/api/books/import'), {
    method: 'POST',
    body: formData,
  })

  if (!response.ok) {
    throw new Error(await parseError(response, '导入图书失败'))
  }

  return response.json()
}

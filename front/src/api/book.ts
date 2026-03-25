import { withApiBase } from './base'

export type BookStatus = 'imported' | 'processing' | 'ready' | 'limited' | 'failed'

export interface Book {
  id: number
  title: string
  author?: string | null
  cover_url?: string | null
  file_name: string
  file_path: string
  status: BookStatus
  status_detail?: string | null
  ai_friend_id?: number | null
  reading_location?: string | null
  create_time: string
  update_time: string
  deleted: boolean
  file_size?: number | null
  format_type: string
  bound_friend_name?: string | null
  bound_friend_avatar?: string | null
  author_binding_status: 'unbound' | 'valid' | 'invalid'
  author_binding_message: string
}

export interface BookUpdatePayload {
  title?: string | null
  author?: string | null
  ai_friend_id?: number | null
}

export interface BookReadingLocationPayload {
  reading_location: string | null
  progress?: number
  display_label?: string | null
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

export async function updateBook(bookId: number, payload: BookUpdatePayload): Promise<Book> {
  const response = await fetch(withApiBase(`/api/books/${bookId}`), {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    throw new Error(await parseError(response, '更新图书失败'))
  }

  return response.json()
}

export async function updateBookReadingLocation(
  bookId: number,
  payload: BookReadingLocationPayload,
  options: {
    keepalive?: boolean
  } = {},
): Promise<Book> {
  const response = await fetch(withApiBase(`/api/books/${bookId}/reading-location`), {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
    keepalive: options.keepalive === true,
  })

  if (!response.ok) {
    throw new Error(await parseError(response, '更新阅读进度失败'))
  }

  return response.json()
}

export async function updateBookCover(bookId: number, file: File): Promise<Book> {
  const formData = new FormData()
  formData.append('file', file)

  const response = await fetch(withApiBase(`/api/books/${bookId}/cover`), {
    method: 'POST',
    body: formData,
  })

  if (!response.ok) {
    throw new Error(await parseError(response, '更新封面失败'))
  }

  return response.json()
}

export async function deleteBook(bookId: number): Promise<void> {
  const response = await fetch(withApiBase(`/api/books/${bookId}`), {
    method: 'DELETE',
  })

  if (!response.ok) {
    throw new Error(await parseError(response, '删除图书失败'))
  }
}

// Every call goes through /api. The dev proxy and the production proxy both strip that prefix.
const API_PREFIX = '/api'

export class ApiError extends Error {
  readonly status: number
  // Lines to show under the message, such as unbalanced totals or over-claimed items.
  readonly details: string[]

  constructor(status: number, message: string, details: string[] = []) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.details = details
  }
}

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
  body?: unknown
  form?: FormData
  headers?: Record<string, string>
}

export function hostHeaders(token: string): Record<string, string> {
  return { 'X-Host-Token': token }
}

export function memberHeaders(token: string): Record<string, string> {
  return { 'X-Member-Token': token }
}

// The backend and FastAPI put the reason in "detail", in three different shapes.
export function errorFromResponse(status: number, body: unknown): ApiError {
  const detail = (body as { detail?: unknown } | null)?.detail

  if (typeof detail === 'string') {
    return new ApiError(status, detail)
  }
  if (Array.isArray(detail)) {
    // FastAPI validation errors: a list of { msg, loc, ... }.
    const messages = detail
      .map((entry) => (typeof entry?.msg === 'string' ? entry.msg : ''))
      .filter(Boolean)
    return new ApiError(status, messages.join(' ') || 'Check the form and try again.')
  }
  if (detail && typeof detail === 'object') {
    // Conflicts such as "not ready" come with a message plus problems or item names.
    const { message, problems, items } = detail as Record<string, unknown>
    const details = [problems, items].flatMap((list) =>
      Array.isArray(list) ? list.map(String) : [],
    )
    return new ApiError(
      status,
      typeof message === 'string' ? message : 'The request failed.',
      details,
    )
  }
  return new ApiError(status, `The request failed (HTTP ${status}).`)
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = { ...options.headers }
  let body: BodyInit | undefined

  if (options.form) {
    // The browser sets the multipart boundary itself, so no Content-Type here.
    body = options.form
  } else if (options.body !== undefined) {
    headers['Content-Type'] = 'application/json'
    body = JSON.stringify(options.body)
  }

  let response: Response
  try {
    response = await fetch(API_PREFIX + path, {
      method: options.method ?? 'GET',
      headers,
      body,
    })
  } catch {
    throw new ApiError(0, 'Cannot reach the server. Check your connection and try again.')
  }

  const data = (await response.json().catch(() => null)) as unknown
  if (!response.ok) {
    throw errorFromResponse(response.status, data)
  }
  return data as T
}

export function messageOf(caught: unknown): string {
  return caught instanceof Error ? caught.message : 'Something went wrong. Try again.'
}

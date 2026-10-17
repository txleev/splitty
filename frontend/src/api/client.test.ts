import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError, errorFromResponse, request } from './client'

describe('errorFromResponse', () => {
  it('reads a plain detail message', () => {
    const error = errorFromResponse(404, { detail: 'This split does not exist or has expired.' })
    expect(error).toBeInstanceOf(ApiError)
    expect(error.status).toBe(404)
    expect(error.message).toBe('This split does not exist or has expired.')
    expect(error.details).toEqual([])
  })

  it('reads a conflict with its list of problems', () => {
    const error = errorFromResponse(409, {
      detail: {
        message: 'The split cannot be shared yet.',
        problems: ['Items sum to 40.00 but subtotal is 50.00'],
      },
    })
    expect(error.message).toBe('The split cannot be shared yet.')
    expect(error.details).toEqual(['Items sum to 40.00 but subtotal is 50.00'])
  })

  it('reads the names of over-claimed items', () => {
    const error = errorFromResponse(409, {
      detail: { message: 'Some of your claims no longer fit the bill.', items: ['Tea'] },
    })
    expect(error.details).toEqual(['Tea'])
  })

  it('joins the messages of FastAPI validation errors', () => {
    const error = errorFromResponse(422, {
      detail: [{ msg: 'Field required', loc: ['body', 'name'] }, { msg: 'Too long' }],
    })
    expect(error.message).toBe('Field required Too long')
  })

  it('falls back to the status code when there is no detail', () => {
    expect(errorFromResponse(502, null).message).toBe('The request failed (HTTP 502).')
  })
})

describe('request', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('calls the API under /api and returns the parsed body', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify({ status: 'ok' }), { status: 200 }))
    vi.stubGlobal('fetch', fetchMock)

    await expect(request<{ status: string }>('/health')).resolves.toEqual({ status: 'ok' })
    expect(fetchMock).toHaveBeenCalledWith('/api/health', expect.objectContaining({ method: 'GET' }))
  })

  it('throws an ApiError that carries the message from the server', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: 'Wrong host token' }), { status: 403 })),
    )
    await expect(request('/sessions/abc')).rejects.toMatchObject({
      status: 403,
      message: 'Wrong host token',
    })
  })

  it('explains a network failure instead of exposing the raw error', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))
    await expect(request('/health')).rejects.toMatchObject({
      status: 0,
      message: 'Cannot reach the server. Check your connection and try again.',
    })
  })
})

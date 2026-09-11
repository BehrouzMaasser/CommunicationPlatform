export class ApiError extends Error {
  status: number
  data: unknown

  constructor(status: number, message: string, data: unknown = null) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.data = data
  }
}

type JsonObject = Record<string, unknown>

type ApiBody =
  | JsonObject
  | FormData
  | null
  | undefined

type ApiRequestOptions = {
  method?: 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE'
  body?: ApiBody
}

const SAFE_METHODS = new Set([
  'GET',
  'HEAD',
  'OPTIONS',
  'TRACE',
])

function getCookie(name: string): string | null {
  const cookies = document.cookie
    .split(';')
    .map((cookie) => cookie.trim())

  const prefix = `${name}=`

  for (const cookie of cookies) {
    if (cookie.startsWith(prefix)) {
      return decodeURIComponent(
        cookie.slice(prefix.length),
      )
    }
  }

  return null
}

function getCsrfToken(): string {
  const token = getCookie('csrftoken')

  if (!token) {
    throw new Error(
      'CSRF token cookie is missing. Reload a Django page that sets the CSRF cookie, then try again.',
    )
  }

  return token
}

async function readResponseBody(
  response: Response,
): Promise<unknown> {
  if (response.status === 204) {
    return null
  }

  const contentType =
    response.headers.get('content-type') ?? ''

  if (contentType.includes('application/json')) {
    return response.json()
  }

  const text = await response.text()

  return text || null
}

function extractErrorMessage(
  data: unknown,
): string | null {
  if (typeof data === 'string') {
    return data || null
  }

  if (Array.isArray(data)) {
    for (const item of data) {
      const message = extractErrorMessage(item)

      if (message) {
        return message
      }
    }

    return null
  }

  if (
    typeof data === 'object' &&
    data !== null
  ) {
    const record =
      data as Record<string, unknown>

    if (
      typeof record.detail === 'string'
    ) {
      return record.detail
    }

    for (const [field, value] of Object.entries(record)) {
      const message =
        extractErrorMessage(value)

      if (message) {
        return `${field}: ${message}`
      }
    }
  }

  return null
}

function getErrorMessage(
  status: number,
  data: unknown,
): string {
  return (
    extractErrorMessage(data) ??
    `Request failed with status ${status}`
  )
}

export async function apiRequest<T>(
  url: string,
  options: ApiRequestOptions = {},
): Promise<T> {
  const method = options.method ?? 'GET'

  const headers = new Headers({
    Accept: 'application/json',
  })

  let body: BodyInit | undefined

  if (options.body instanceof FormData) {
    body = options.body
  } else if (options.body != null) {
    headers.set(
      'Content-Type',
      'application/json',
    )
    body = JSON.stringify(options.body)
  }

  if (!SAFE_METHODS.has(method)) {
    headers.set(
      'X-CSRFToken',
      getCsrfToken(),
    )
  }

  const response = await fetch(url, {
    method,
    body,
    headers,
    credentials: 'same-origin',
    mode: 'same-origin',
  })

  const data = await readResponseBody(response)

  if (!response.ok) {
    throw new ApiError(
      response.status,
      getErrorMessage(response.status, data),
      data,
    )
  }

  return data as T
}

export function apiGet<T>(
  url: string,
): Promise<T> {
  return apiRequest<T>(url)
}

export function apiPost<T>(
  url: string,
  body?: ApiBody,
): Promise<T> {
  return apiRequest<T>(url, {
    method: 'POST',
    body,
  })
}

export function apiPatch<T>(
  url: string,
  body?: ApiBody,
): Promise<T> {
  return apiRequest<T>(url, {
    method: 'PATCH',
    body,
  })
}

export function apiPut<T>(
  url: string,
  body?: ApiBody,
): Promise<T> {
  return apiRequest<T>(url, {
    method: 'PUT',
    body,
  })
}

export function apiDelete<T>(
  url: string,
  body?: ApiBody,
): Promise<T> {
  return apiRequest<T>(url, {
    method: 'DELETE',
    body,
  })
}

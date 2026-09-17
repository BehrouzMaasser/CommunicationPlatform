export class ApiError extends Error {
  status: number
  data: unknown

  constructor(
    status: number,
    message: string,
    data: unknown = null,
  ) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.data = data
  }
}


type JsonObject =
  Record<string, unknown>


type ApiBody =
  | JsonObject
  | FormData
  | null
  | undefined


type ApiRequestOptions = {
  method?:
    | 'GET'
    | 'POST'
    | 'PATCH'
    | 'PUT'
    | 'DELETE'

  body?: ApiBody
}


const SAFE_METHODS =
  new Set([
    'GET',
    'HEAD',
    'OPTIONS',
    'TRACE',
  ])


function getCookie(
  name: string,
): string | null {
  const cookies =
    document.cookie
      .split(';')
      .map(
        (cookie) =>
          cookie.trim(),
      )

  const prefix = `${name}=`

  for (const cookie of cookies) {
    if (
      cookie.startsWith(
        prefix,
      )
    ) {
      return decodeURIComponent(
        cookie.slice(
          prefix.length,
        ),
      )
    }
  }

  return null
}


function getCsrfToken(): string {
  const token =
    getCookie(
      'csrftoken',
    )

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
  if (
    response.status === 204
  ) {
    return null
  }

  const contentType =
    response.headers.get(
      'content-type',
    ) ?? ''

  if (
    contentType.includes(
      'application/json',
    )
  ) {
    return response.json()
  }

  /*
   * We may still read a non-JSON body for diagnostics in ApiError.data,
   * but it must never automatically become the user-facing message.
   *
   * In DEBUG mode Django can return an entire HTML traceback page for an
   * uncaught 500. That is useful in DevTools, not in application UI.
   */
  const text =
    await response.text()

  return text || null
}


function getJsonDetail(
  data: unknown,
): string | null {
  if (
    typeof data === 'object'
    &&
    data !== null
    &&
    'detail' in data
    &&
    typeof data.detail
      === 'string'
  ) {
    return data.detail
  }

  return null
}


function getErrorMessage(
  response: Response,
  data: unknown,
): string {
  /*
   * Unexpected server failures are opaque to the UI.
   *
   * Never render raw HTML/text returned by a 5xx response. In development
   * that could be Django's DEBUG traceback; in production it could be a
   * proxy/server error page.
   */
  if (
    response.status >= 500
  ) {
    return (
      'The server encountered an unexpected error. '
      + 'Please try again.'
    )
  }

  const detail =
    getJsonDetail(data)

  if (detail) {
    return detail
  }

  /*
   * Only structured API errors are considered safe for direct display.
   * Do not turn arbitrary non-JSON response bodies into UI copy.
   */
  if (
    response.status === 401
  ) {
    return (
      'Your session is not authenticated. '
      + 'Please sign in again.'
    )
  }

  if (
    response.status === 403
  ) {
    return (
      'You do not have permission '
      + 'to perform this action.'
    )
  }

  if (
    response.status === 404
  ) {
    return (
      'The requested resource '
      + 'was not found.'
    )
  }

  return (
    `Request failed with status `
    + response.status
  )
}


export async function apiRequest<T>(
  url: string,
  options:
    ApiRequestOptions = {},
): Promise<T> {
  const method =
    options.method ?? 'GET'

  const headers =
    new Headers({
      Accept:
        'application/json',
    })

  let body:
    BodyInit | undefined

  if (
    options.body
    instanceof FormData
  ) {
    body = options.body
  } else if (
    options.body != null
  ) {
    headers.set(
      'Content-Type',
      'application/json',
    )

    body =
      JSON.stringify(
        options.body,
      )
  }

  if (
    !SAFE_METHODS.has(
      method,
    )
  ) {
    headers.set(
      'X-CSRFToken',
      getCsrfToken(),
    )
  }

  const response =
    await fetch(
      url,
      {
        method,
        body,
        headers,
        credentials:
          'same-origin',
        mode:
          'same-origin',
      },
    )

  const data =
    await readResponseBody(
      response,
    )

  if (!response.ok) {
    throw new ApiError(
      response.status,
      getErrorMessage(
        response,
        data,
      ),
      data,
    )
  }

  return data as T
}


export function apiGet<T>(
  url: string,
): Promise<T> {
  return apiRequest<T>(
    url,
  )
}


export function apiPost<T>(
  url: string,
  body?: ApiBody,
): Promise<T> {
  return apiRequest<T>(
    url,
    {
      method: 'POST',
      body,
    },
  )
}


export function apiPatch<T>(
  url: string,
  body?: ApiBody,
): Promise<T> {
  return apiRequest<T>(
    url,
    {
      method: 'PATCH',
      body,
    },
  )
}


export function apiDelete<T>(
  url: string,
  body?: ApiBody,
): Promise<T> {
  return apiRequest<T>(
    url,
    {
      method: 'DELETE',
      body,
    },
  )
}


export async function apiGetBlob(
  url: string,
  signal?: AbortSignal,
): Promise<Blob> {
  const response =
    await fetch(
      url,
      {
        method: 'GET',
        headers: {
          Accept: '*/*',
        },
        credentials:
          'same-origin',
        mode:
          'same-origin',
        signal,
      },
    )

  if (!response.ok) {
    const data =
      await readResponseBody(
        response,
      )

    throw new ApiError(
      response.status,
      getErrorMessage(
        response,
        data,
      ),
      data,
    )
  }

  return response.blob()
}

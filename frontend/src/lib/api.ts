// HTTP client. Named calls for each feature are in endpoints.ts.
export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`/api${path}`, {
      ...init,
      credentials: 'same-origin',
      cache: 'no-store',
      headers: { 'Content-Type': 'application/json', ...init?.headers },
    });
  } catch {
    throw new ApiError(0, 'Não foi possível conectar. Confira sua conexão e tente novamente.');
  }
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    let message = typeof data.detail === 'string' ? data.detail : 'Não foi possível concluir a operação.';
    if (data.errors?.length)
      message += ` ${data.errors.map((e: { field: string; message: string }) => `${e.field}: ${e.message}`).join(' · ')}`;
    throw new ApiError(response.status, message);
  }
  return response.status === 204 ? (undefined as T) : response.json();
}

export function send<T>(path: string, body?: unknown, method = 'POST') {
  return api<T>(path, { method, body: body === undefined ? undefined : JSON.stringify(body) });
}

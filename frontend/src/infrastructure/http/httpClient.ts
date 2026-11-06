export class HttpClient {
  private static async request<T>(url: string, init?: RequestInit): Promise<T> {
    const res = await fetch(url, {
      headers: {
        'Accept': 'application/json',
        ...(init?.body ? { 'Content-Type': 'application/json' } : {}),
      },
      ...init,
    });
    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.detail || `HTTP error! status: ${res.status}`);
    }
    return res.json();
  }

  static async get<T>(url: string): Promise<T> {
    return HttpClient.request<T>(url);
  }

  static async post<T>(url: string, body: any): Promise<T> {
    return HttpClient.request<T>(url, {
      method: 'POST',
      body: JSON.stringify(body),
    });
  }

  static async patch<T>(url: string, body: any): Promise<T> {
    return HttpClient.request<T>(url, {
      method: 'PATCH',
      body: JSON.stringify(body),
    });
  }
}

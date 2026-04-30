export type Requester = {
  <T>(path: string, init?: RequestInit): Promise<T>;
  raw: (path: string, init?: RequestInit) => Promise<Response>;
};

import request from "@/utils/request";

export interface LoginParams {
  username: string;
  password: string;
}

export function login(data: LoginParams) {
  return request.post("/api/auth/login", data) as Promise<{
    access_token: string;
  }>;
}

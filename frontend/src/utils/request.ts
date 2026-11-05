import axios from "axios";
import { ElMessage } from "element-plus";

const request = axios.create({
  baseURL: "/",
  timeout: 15000,
});

// 请求拦截：附加 token
request.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// 响应拦截：统一错误提示
request.interceptors.response.use(
  (resp) => resp.data,
  (error) => {
    const status = error.response?.status;
    if (status === 401) {
      localStorage.removeItem("token");
      window.location.href = "/login";
    } else {
      ElMessage.error(error.response?.data?.detail || "请求失败");
    }
    return Promise.reject(error);
  }
);

export default request;

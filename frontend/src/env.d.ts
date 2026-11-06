/// <reference types="vite/client" />

declare module "*.vue" {
  import type { DefineComponent } from "vue";
  const component: DefineComponent<{}, {}, any>;
  export default component;
}

declare module "flv.js";

interface ImportMetaEnv {
  /** MediaMTX FLV 播放地址前缀（如 http://192.168.1.10:8080），默认 http://localhost:8080 */
  readonly VITE_MEDIAMTX_BASE?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

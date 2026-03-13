/// <reference types="vite/client" />

declare module '*.vue' {
  import { DefineComponent } from 'vue'
  const component: DefineComponent<object, object, unknown>
  export default component
}

interface ImportMetaEnv {
  readonly VITE_SITE_ID: string
  readonly VITE_SITE_CODE: string
  readonly VITE_SITE_NAME: string
  readonly VITE_API_BASE_URL: string
  readonly VITE_SERVER_BASE: string
  readonly VITE_WX_APPID: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

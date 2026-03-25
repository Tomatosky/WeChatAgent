export const mainTabs = ['chat', 'gallery', 'library'] as const

export type MainTab = (typeof mainTabs)[number]

export const MAIN_TAB_STORAGE_KEY = 'weagentchat:last-primary-tab'

export const isMainTab = (value: unknown): value is MainTab => {
  return typeof value === 'string' && mainTabs.includes(value as MainTab)
}

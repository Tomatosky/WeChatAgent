export interface FoliateViewRuntimeModule {
  ResponseError: typeof Error
  NotFoundError: typeof Error
  UnsupportedTypeError: typeof Error
}

export const loadFoliateViewModule = async (): Promise<FoliateViewRuntimeModule> => {
  return import('@/vendor/foliate-js/view.js')
}

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { cpSync, existsSync, mkdirSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath, URL } from 'node:url'

const foliatePdfAssetDirs = [
  {
    source: fileURLToPath(new URL('./src/vendor/foliate-js/vendor/pdfjs/cmaps', import.meta.url)),
    target: 'assets/vendor/pdfjs/cmaps',
  },
  {
    source: fileURLToPath(new URL('./src/vendor/foliate-js/vendor/pdfjs/standard_fonts', import.meta.url)),
    target: 'assets/vendor/pdfjs/standard_fonts',
  },
]

const foliatePdfAssetsPlugin = () => {
  let outDir = ''

  return {
    name: 'foliate-pdf-assets',
    apply: 'build',
    configResolved(config) {
      outDir = resolve(config.root, config.build.outDir)
    },
    closeBundle() {
      for (const assetDir of foliatePdfAssetDirs) {
        if (!existsSync(assetDir.source)) continue

        const destination = resolve(outDir, assetDir.target)
        mkdirSync(dirname(destination), { recursive: true })
        cpSync(assetDir.source, destination, { recursive: true, force: true })
      }
    },
  }
}

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    foliatePdfAssetsPlugin(),
  ],
  // 让打包后的资源使用相对路径，Electron file:// 协议下可正常加载
  base: './',
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      }
    }
  },
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  }
})

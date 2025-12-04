import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import eslintPlugin from 'vite-plugin-eslint'
import { viteMockServe } from 'vite-plugin-mock'

import path from 'path'
import proxy from './config/proxy'

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => ({
  plugins: [
    react(),
    eslintPlugin({
      include: ['src/**/*.js', 'src/**/*.ts', 'src/**/*.tsx', 'src/*.js', 'src/*.ts', 'src/*.tsx']
    }),
    viteMockServe({
      // default
      localEnabled: mode === 'mock',
      mockPath: './config/mock'
    })
  ],
  resolve: {
    extensions: ['.mjs', '.js', '.jsx', '.ts', '.tsx', '.json', '.sass', '.scss'], // 忽略输入的扩展名
    alias: [
      { find: /^~/, replacement: '' },
      { find: '@', replacement: path.resolve(__dirname, 'src') },
      { find: '~', replacement: path.resolve(__dirname, './node_modules') },
      {
        find: '@components',
        replacement: path.resolve(__dirname, 'src/components')
      },
      { find: '@config', replacement: path.resolve(__dirname, 'config') }
      // {
      //   find: '@antd/dist/reset.css',
      //   replacement: path.join(__dirname, 'node_modules/antd/dist/reset.css')
      // }
      // // { find: 'antd', replacement: path.join(__dirname, 'node_modules/antd/dist/antd.js') },
      // // {
      // //   find: '@ant-design/icons',
      // //   replacement: path.join(__dirname, 'node_modules/@ant-design/icons/dist/index.umd.js')
      // // }
    ]
  },
  css: {
    preprocessorOptions: {
      less: {
        // 支持内联 JavaScript
        javascriptEnabled: true
      }
    }
  },
  server: {
    allowedHosts: true, 
    port: 5050,
    proxy: {
      '/hyperrag': 'http://127.0.0.1:8090',
      '/db': 'http://127.0.0.1:8090',
      '/files': 'http://127.0.0.1:8090',
      '/settings': 'http://127.0.0.1:8090',
      '/process_message': 'http://127.0.0.1:8090',
      '/databases': 'http://127.0.0.1:8090',
      '/ws': {
        target: 'ws://127.0.0.1:8090',
        ws: true
      }
    }
  },
  build: {
    // 打包出map文件
    sourcemap: false
  }
}))

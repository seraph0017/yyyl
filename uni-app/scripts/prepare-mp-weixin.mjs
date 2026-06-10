import { cpSync, existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const rootDir = resolve(__dirname, '..')
const siteCode = process.argv[2]
const buildDir = join(rootDir, 'dist/build')
const sourceDir = join(buildDir, 'mp-weixin')
const projectConfigPath = join(rootDir, 'project.config.json')
const sourceProjectConfigPath = join(sourceDir, 'project.config.json')
const sourceAppJsonPath = join(sourceDir, 'app.json')

function readJson(path) {
  return JSON.parse(readFileSync(path, 'utf8'))
}

function writeJson(path, value) {
  writeFileSync(path, `${JSON.stringify(value, null, 2)}\n`)
}

function patchProjectConfig(outputDir) {
  const rootConfig = readJson(projectConfigPath)
  const outputConfigPath = join(outputDir, 'project.config.json')
  const outputConfig = readJson(outputConfigPath)

  if (rootConfig.libVersion) {
    outputConfig.libVersion = rootConfig.libVersion
  }

  writeJson(outputConfigPath, outputConfig)
}

function patchAppJson(outputDir) {
  const appJsonPath = join(outputDir, 'app.json')
  const appJson = readJson(appJsonPath)
  appJson.lazyCodeLoading = 'requiredComponents'
  writeJson(appJsonPath, appJson)
}

if (!existsSync(sourceProjectConfigPath)) {
  throw new Error(`未找到微信小程序构建产物：${sourceProjectConfigPath}`)
}

if (!existsSync(sourceAppJsonPath)) {
  throw new Error(`未找到微信小程序 app.json：${sourceAppJsonPath}`)
}

patchProjectConfig(sourceDir)
patchAppJson(sourceDir)

if (siteCode) {
  const targetDir = join(buildDir, `mp-weixin-${siteCode}`)
  mkdirSync(buildDir, { recursive: true })
  cpSync(sourceDir, targetDir, { recursive: true, force: true })
  patchProjectConfig(targetDir)
  patchAppJson(targetDir)
  console.log(`已准备微信小程序导入目录：${targetDir}`)
} else {
  console.log(`已更新微信小程序构建目录：${sourceDir}`)
}

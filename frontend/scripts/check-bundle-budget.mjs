import { readdir, stat } from 'node:fs/promises'
import path from 'node:path'

const distDir = path.resolve(process.cwd(), 'dist', 'assets')
const maxLargestJsBytes = 500 * 1024
const maxTotalJsBytes = 1500 * 1024

async function collectJavaScriptAssets(rootDir) {
  const entries = await readdir(rootDir, { withFileTypes: true })
  const files = []
  for (const entry of entries) {
    const absolutePath = path.join(rootDir, entry.name)
    if (entry.isDirectory()) {
      files.push(...(await collectJavaScriptAssets(absolutePath)))
      continue
    }
    if (entry.isFile() && absolutePath.endsWith('.js')) {
      const fileStat = await stat(absolutePath)
      files.push({
        file: path.relative(path.resolve(process.cwd(), 'dist'), absolutePath),
        size: fileStat.size,
      })
    }
  }
  return files
}

function formatBytes(bytes) {
  return `${(bytes / 1024).toFixed(1)} KiB`
}

async function main() {
  const jsAssets = await collectJavaScriptAssets(distDir)
  if (jsAssets.length === 0) {
    throw new Error(`No JavaScript assets were found under ${distDir}. Run npm run build first.`)
  }

  const largestAsset = jsAssets.reduce((currentLargest, asset) =>
    asset.size > currentLargest.size ? asset : currentLargest,
  )
  const totalBytes = jsAssets.reduce((sum, asset) => sum + asset.size, 0)

  if (largestAsset.size > maxLargestJsBytes) {
    throw new Error(
      `Largest JS asset ${largestAsset.file} is ${formatBytes(largestAsset.size)}, exceeding the ${formatBytes(maxLargestJsBytes)} budget.`,
    )
  }
  if (totalBytes > maxTotalJsBytes) {
    throw new Error(
      `Total JS bundle size is ${formatBytes(totalBytes)}, exceeding the ${formatBytes(maxTotalJsBytes)} budget.`,
    )
  }

  console.log(
    `Bundle budgets passed: largest=${largestAsset.file} (${formatBytes(largestAsset.size)}), total=${formatBytes(totalBytes)}.`,
  )
}

await main()

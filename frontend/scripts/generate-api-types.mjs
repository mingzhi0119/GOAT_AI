import { spawnSync } from 'node:child_process'
import {
  mkdirSync,
  mkdtempSync,
  readFileSync,
  rmSync,
  unlinkSync,
  writeFileSync,
} from 'node:fs'
import { tmpdir } from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const scriptDir = path.dirname(fileURLToPath(import.meta.url))
const frontendRoot = path.resolve(scriptDir, '..')
const repoRoot = path.resolve(frontendRoot, '..')
const inputPath = path.join(repoRoot, 'docs', 'openapi.json')
const outputPath = path.join(frontendRoot, 'src', 'api', 'generated', 'openapi.ts')
const cliPath = path.join(frontendRoot, 'node_modules', 'openapi-typescript', 'bin', 'cli.js')
const isCheckMode = process.argv.includes('--check')

function createGeneratorCompatibleSpec(tempInputPath) {
  const openApiObject = JSON.parse(readFileSync(inputPath, 'utf8'))
  if (openApiObject.openapi === '3.2.0') {
    openApiObject.openapi = '3.1.0'
  }
  writeFileSync(tempInputPath, `${JSON.stringify(openApiObject, null, 2)}\n`, 'utf8')
}

function generateOpenApiTypes(tempInputPath, tempOutputPath) {
  const result = spawnSync(
    process.execPath,
    [cliPath, tempInputPath, '-o', tempOutputPath],
    {
      cwd: frontendRoot,
      encoding: 'utf8',
      stdio: 'pipe',
    },
  )

  if (result.status !== 0 || result.error) {
    const stderr = result.stderr?.trim()
    const stdout = result.stdout?.trim()
    throw new Error(
      result.error?.message || stderr || stdout || 'openapi-typescript generation failed',
    )
  }

  return readFileSync(tempOutputPath, 'utf8')
}

function buildGeneratedFile(contents) {
  return [
    '/*',
    ' * This file is auto-generated from ../docs/openapi.json.',
    ' * Do not edit it manually; run `npm run contract:generate` instead.',
    ' */',
    '',
    contents.trimEnd(),
    '',
  ].join('\n')
}

const tempDir = mkdtempSync(path.join(tmpdir(), 'goat-openapi-'))
const tempInputPath = path.join(tempDir, 'openapi.compat.json')
const tempOutputPath = path.join(tempDir, 'openapi.ts')

try {
  createGeneratorCompatibleSpec(tempInputPath)
  const generated = buildGeneratedFile(generateOpenApiTypes(tempInputPath, tempOutputPath))

  if (isCheckMode) {
    const current = readFileSync(outputPath, 'utf8')
    if (current !== generated) {
      console.error(
        'Frontend API contract types are out of sync. Run `npm run contract:generate`.',
      )
      process.exit(1)
    }
    console.log('Frontend API contract types are in sync.')
    process.exit(0)
  }

  mkdirSync(path.dirname(outputPath), { recursive: true })
  writeFileSync(outputPath, generated, 'utf8')
  console.log(`Generated ${path.relative(frontendRoot, outputPath)}`)
} finally {
  unlinkSync(tempInputPath)
  rmSync(tempDir, { recursive: true, force: true })
}

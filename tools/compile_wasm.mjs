import assert from 'node:assert/strict'
import { dirname, join } from 'node:path'
import { spawnSync } from 'node:child_process'

// Invoke cc1 explicitly: the Android Clang driver cannot locate its own
// executable inside some Windows sandboxes. No downloads or native code run.
export function compileWasm(compiler, input, binary) {
  const object = binary + '.o'
  const commands = [
    [compiler, ['-cc1', '-triple', 'wasm32', '-emit-obj', '-O2', '-fno-builtin',
      '-std=c++17', '-x', 'c++', input, '-o', object]],
    [join(dirname(compiler), process.platform === 'win32' ? 'wasm-ld.exe' : 'wasm-ld'),
      ['-m', 'wasm32', '--no-entry', '--export-all', object, '-o', binary]],
  ]
  for (const [tool, args] of commands) {
    const result = spawnSync(tool, args, { encoding: 'utf8', timeout: 30000, maxBuffer: 4 * 1024 * 1024 })
    assert.equal(result.status, 0, result.error?.message || result.stderr)
  }
}

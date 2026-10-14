import test from 'node:test'
import assert from 'node:assert/strict'
import { formatReason, labelForState } from '../src/nodeStates.ts'

test('version 3 warnings and suspected fire have distinct labels while history stays readable', () => {
  assert.equal(labelForState('WARNING', 3), 'ความเสี่ยงสูง')
  assert.equal(labelForState('CRITICAL', 3), 'สงสัยมีไฟ')
  assert.equal(labelForState('CRITICAL', 2), 'วิกฤต')
  assert.match(formatReason('hot_dry_30_30'), /30°C/)
  assert.match(formatReason('sharp_particles_strong'), /Sharp/)
})

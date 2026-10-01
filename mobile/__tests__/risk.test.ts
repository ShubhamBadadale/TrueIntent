import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import {
  formatRiskIndex,
  formatScore,
  levelLabel,
  moduleLabel,
} from '../utils/risk';

describe('risk utils', () => {
  it('formats scores as N/100 and guards non-numbers', () => {
    assert.equal(formatScore(0.72), '72/100');
    assert.equal(formatScore(0), '0/100');
    assert.equal(formatScore(1), '100/100');
    assert.equal(formatScore(null), '—');
    assert.equal(formatScore(Number.NaN), '—');
  });

  it('clamps risk indexes', () => {
    assert.equal(formatRiskIndex(72), '72');
    assert.equal(formatRiskIndex(250), '100');
    assert.equal(formatRiskIndex(-3), '0');
    assert.equal(formatRiskIndex(undefined), '—');
  });

  it('labels levels in capitals and null as not analyzed', () => {
    assert.equal(levelLabel('Low'), 'LOW');
    assert.equal(levelLabel('Medium'), 'MEDIUM');
    assert.equal(levelLabel('High'), 'HIGH');
    assert.equal(levelLabel('Critical'), 'CRITICAL');
    assert.equal(levelLabel(null), 'NOT ANALYZED');
  });

  it('names modules for users, passing through unknowns', () => {
    assert.equal(moduleLabel('module_b'), 'Link check (Module B)');
    assert.equal(moduleLabel('module_c'), 'Message check (Module C)');
    assert.equal(moduleLabel('module_a'), 'Transaction benchmark (Module A)');
    assert.equal(moduleLabel('module_z'), 'module_z');
  });
});

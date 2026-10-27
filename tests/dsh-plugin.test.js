import assert from 'node:assert/strict';
import { readFile, access } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';
import * as plugin from '../dsh/index.js';

test('provider loads the canonical skill and resolves its supporting resources', async () => {
  let provider;
  plugin.apply({ skills: { registerProvider(factory) { provider = factory(); } } });
  const [candidate] = await provider.list();
  const definition = await provider.get(candidate);
  const original = await readFile(new URL('../SKILL.md', import.meta.url), 'utf8');
  assert.equal(candidate.name, 'paperwalk');
  assert.equal(candidate.description, JSON.parse(original.match(/^description: (.+)$/m)[1]));
  assert.equal(definition.content, original.replace(/^---\r?\n[\s\S]*?\r?\n---\r?\n/, ''));
  assert.deepEqual(definition.invocation, { modelInvocable: true, userInvocable: true });
  assert.equal(definition.path, fileURLToPath(new URL('../SKILL.md', import.meta.url)));
  for (const file of ['references/full-reading.md', 'references/segmentation.md',
    'references/teaching.md', 'references/session-state.md',
    'assets/session-template.json', 'scripts/check_readiness.py']) {
    await access(join(definition.resourceBase.path, file));
  }
});

test('real DSH registry loads, prioritizes local overrides and disposes the plugin', {
  skip: !process.env.DSH_TEST_RUNTIME && 'Set DSH_TEST_RUNTIME to a DSH installation package.json to run integration coverage.',
}, async () => {
  const require = createRequire(process.env.DSH_TEST_RUNTIME);
  const { Context } = require('@deepseek-ai/cordis');
  const { SkillRegistry, renderSkillContent } = require('@deepseek-ai/dsh-skill');
  const ctx = new Context();
  try {
    await ctx.plugin(SkillRegistry);
    const fork = ctx.plugin(plugin);
    await fork;
    assert.equal((await ctx.skills.list()).filter(s => s.name === 'paperwalk').length, 1);
    const skill = await ctx.skills.get('paperwalk');
    assert.match(renderSkillContent(skill), /先完整研读，后教学分段/);
    assert.ok(renderSkillContent(skill).includes(skill.resourceBase.path));
    const local = { ...skill, provider: 'local-test', source: 'user-dsh', content: 'local override' };
    const undoOverride = ctx.skills.registerProvider(() => ({
      name: 'local-test',
      async list() { return [{ ...local, rank: 400, locator: 'test-local' }]; },
      async get() { return local; },
    }));
    assert.equal((await ctx.skills.get('paperwalk')).content, 'local override');
    undoOverride();
    assert.match((await ctx.skills.get('paperwalk')).content, /先完整研读，后教学分段/);
    await fork.dispose();
    assert.equal(await ctx.skills.get('paperwalk'), undefined);
  } finally {
    await ctx.fiber.dispose();
  }
});

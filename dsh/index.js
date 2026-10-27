import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

export const name = 'paperwalk-skill';
export const inject = ['skills'];

const skillURL = new URL('../SKILL.md', import.meta.url);
const resourceBase = {
  kind: 'directory',
  path: fileURLToPath(new URL('../', import.meta.url)),
};

export function apply(ctx) {
  // Read the canonical skill, not a second copy maintained for this host.
  const source = readFileSync(skillURL, 'utf8').replace(/^\uFEFF/, '');
  const parts = /^---\r?\n([\s\S]*?)\r?\n---\r?\n([\s\S]*)$/.exec(source);
  // This package owns this format: plain kebab-case name and JSON-quoted,
  // single-line description. Fail visibly if an edit changes that contract.
  const skillName = parts?.[1].match(/^name: ([a-z0-9]+(?:-[a-z0-9]+)*)\s*$/m)?.[1];
  const descriptionLine = parts?.[1].match(/^description: ("[^\r\n]*")\s*$/m)?.[1];
  if (skillName !== 'paperwalk' || !descriptionLine) {
    throw new Error('PaperWalk SKILL.md requires name: paperwalk and a JSON-quoted one-line description.');
  }
  const description = JSON.parse(descriptionLine);
  if (typeof description !== 'string' || !description.trim() || !parts[2].trim()) {
    throw new Error('PaperWalk SKILL.md requires a non-empty description and body.');
  }
  const definition = {
    name: skillName,
    description,
    path: fileURLToPath(skillURL),
    invocation: { modelInvocable: true, userInvocable: true },
    provider: 'paperwalk',
    source: 'bundled',
    resourceBase,
    content: parts[2],
  };
  const { content, ...summary } = definition;
  const candidate = { ...summary, rank: 600, locator: definition.path };
  // DSH owns the registration's lifecycle and removes it on plugin disposal.
  ctx.skills.registerProvider(() => ({
    name: 'paperwalk',
    async list() { return [candidate]; },
    async get() { return definition; },
  }));
}

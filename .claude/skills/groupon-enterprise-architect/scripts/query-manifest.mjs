#!/usr/bin/env node
/**
 * query-manifest.mjs
 *
 * Zero-dependency CLI that loads data/architecture-manifest.json,
 * builds in-memory indexes, and dispatches query commands.
 * Outputs JSON to stdout; errors to stderr.
 *
 * Usage: node scripts/query-manifest.mjs <command> [argument]
 */
import { readFileSync, existsSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const repoRoot = resolve(__dirname, '..');
const manifestPath = resolve(repoRoot, 'data/architecture-manifest.json');

// ─── Load manifest ──────────────────────────────────────────────────────────
if (!existsSync(manifestPath)) {
  process.stderr.write(
    `Manifest not found: ${manifestPath}\n` +
    'Run: node scripts/generate-manifest.mjs\n'
  );
  process.exit(1);
}

const manifest = JSON.parse(readFileSync(manifestPath, 'utf8'));

// ─── Build indexes ──────────────────────────────────────────────────────────
const elementById = new Map();   // id → flat element record
const elementsByName = new Map(); // lowercase name → element[]

function indexElement(el, type, parentName, systemName) {
  const rec = {
    id: el.id,
    name: el.name,
    type,
    description: el.description || '',
    technology: el.technology || null,
    tags: el.tags || [],
    parentName: parentName || null,
    systemName: systemName || null,
  };
  elementById.set(el.id, rec);
  const key = el.name.toLowerCase();
  if (!elementsByName.has(key)) elementsByName.set(key, []);
  elementsByName.get(key).push(rec);
}

for (const p of manifest.people || []) {
  indexElement(p, 'Person', null, null);
}
for (const sys of manifest.softwareSystems || []) {
  indexElement(sys, 'SoftwareSystem', null, sys.name);
  for (const c of sys.containers || []) {
    indexElement(c, 'Container', sys.name, sys.name);
    for (const comp of c.components || []) {
      indexElement(comp, 'Component', c.name, sys.name);
    }
  }
}

// ─── Helpers ────────────────────────────────────────────────────────────────
function out(obj) {
  process.stdout.write(JSON.stringify(obj, null, 2) + '\n');
}

function truncate(list, limit, hint) {
  if (list.length <= limit) return list;
  const result = list.slice(0, limit);
  result.push({ truncated: true, showing: limit, total: list.length, hint: hint || 'Narrow your query for more results.' });
  return result;
}

function resolveElement(arg) {
  if (!arg) return { error: 'No element name or ID provided.' };

  // 1. Numeric → direct ID
  if (/^\d+$/.test(arg)) {
    const el = elementById.get(arg);
    if (el) return el;
    return { error: `No element with ID ${arg}.` };
  }

  const lower = arg.toLowerCase();

  // 2. Exact case-insensitive match
  if (elementsByName.has(lower)) {
    const matches = elementsByName.get(lower);
    if (matches.length === 1) return matches[0];
    // Multiple exact matches — return disambiguation
    return {
      disambiguation: matches.slice(0, 5).map(m => ({
        id: m.id, name: m.name, type: m.type, parentName: m.parentName,
      })),
      hint: `Multiple elements named "${arg}". Use an ID for precision.`,
    };
  }

  // 3. Substring match, prefer shorter names
  const candidates = [];
  for (const [key, elems] of elementsByName) {
    if (key.includes(lower)) {
      candidates.push(...elems);
    }
  }
  if (candidates.length === 1) return candidates[0];
  if (candidates.length > 1) {
    candidates.sort((a, b) => a.name.length - b.name.length);
    return {
      disambiguation: candidates.slice(0, 5).map(m => ({
        id: m.id, name: m.name, type: m.type, parentName: m.parentName,
      })),
      hint: `Multiple elements match "${arg}". Use an ID for precision.`,
    };
  }

  // 4. No match — suggest close names
  const suggestions = [];
  for (const [key] of elementsByName) {
    if (levenshteinClose(lower, key)) {
      suggestions.push(elementsByName.get(key)[0].name);
      if (suggestions.length >= 5) break;
    }
  }
  return { error: `No element matching "${arg}".`, suggestions };
}

function levenshteinClose(a, b) {
  // Quick heuristic: shared prefix ≥ 3 or one is a substring of the other
  if (a.length < 3 || b.length < 3) return false;
  if (b.includes(a) || a.includes(b)) return true;
  let shared = 0;
  for (let i = 0; i < Math.min(a.length, b.length); i++) {
    if (a[i] === b[i]) shared++; else break;
  }
  return shared >= 3;
}

function getRels(elementId) {
  const outbound = [];
  const inbound = [];
  for (const r of manifest.relationships || []) {
    if (r.sourceId === elementId) outbound.push(r);
    if (r.destinationId === elementId) inbound.push(r);
  }
  return { outbound, inbound };
}

function formatRel(r) {
  return {
    sourceId: r.sourceId,
    sourceName: r.sourceName,
    destinationId: r.destinationId,
    destinationName: r.destinationName,
    description: r.description,
    technology: r.technology || null,
  };
}

// ─── Commands ───────────────────────────────────────────────────────────────

const commands = {};

// overview
commands.overview = () => {
  const stats = manifest._meta.stats;
  const platforms = (manifest.softwareSystems || [])
    .filter(s => (s.tags || []).includes('Platform'))
    .map(s => ({ id: s.id, name: s.name, containers: (s.containers || []).length }));
  const topTags = Object.entries(manifest.tagIndex || {})
    .map(([tag, ids]) => ({ tag, count: ids.length }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 20);
  return { stats, generatedAt: manifest._meta.generatedAt, platforms, topTags };
};

// search
commands.search = (query) => {
  if (!query) return { error: 'Provide a search query.' };
  const lower = query.toLowerCase();
  const groups = { Person: [], SoftwareSystem: [], Container: [], Component: [] };
  for (const [, el] of elementById) {
    if (el.name.toLowerCase().includes(lower) || el.description.toLowerCase().includes(lower)) {
      if (groups[el.type]) groups[el.type].push({ id: el.id, name: el.name, type: el.type, description: el.description, parentName: el.parentName });
    }
  }
  const result = {};
  for (const [type, items] of Object.entries(groups)) {
    if (items.length > 0) result[type] = truncate(items, 25, `Narrow search to see more ${type} results.`);
  }
  if (Object.keys(result).length === 0) return { error: `No results for "${query}".`, suggestions: ['Try broader terms or check spelling.'] };
  return result;
};

// system
commands.system = (name) => {
  const el = resolveElement(name);
  if (el.error || el.disambiguation) return el;
  if (el.type !== 'SoftwareSystem') {
    // Try to find the system this element belongs to
    if (el.systemName) {
      const sysEl = resolveElement(el.systemName);
      if (!sysEl.error && !sysEl.disambiguation && sysEl.type === 'SoftwareSystem') {
        return buildSystemDetail(sysEl);
      }
    }
    return { error: `"${el.name}" is a ${el.type}, not a SoftwareSystem. System: ${el.systemName || 'unknown'}.` };
  }
  return buildSystemDetail(el);
};

function buildSystemDetail(el) {
  const sys = (manifest.softwareSystems || []).find(s => s.id === el.id);
  if (!sys) return { error: `System data not found for ID ${el.id}.` };
  const containers = (sys.containers || []).map(c => ({
    id: c.id,
    name: c.name,
    technology: c.technology || null,
    description: c.description || '',
    componentCount: (c.components || []).length,
    tags: c.tags || [],
  }));
  return {
    id: sys.id,
    name: sys.name,
    description: sys.description || '',
    location: sys.location,
    tags: sys.tags || [],
    group: sys.group,
    containerCount: containers.length,
    containers: truncate(containers, 75, 'Use "containers" command to explore further.'),
  };
}

// containers
commands.containers = (name) => {
  const el = resolveElement(name);
  if (el.error || el.disambiguation) return el;
  let sysName = el.type === 'SoftwareSystem' ? el.name : el.systemName;
  if (!sysName) return { error: `Cannot determine system for "${el.name}".` };
  const sys = (manifest.softwareSystems || []).find(s => s.name === sysName);
  if (!sys) return { error: `System "${sysName}" not found.` };
  const containers = (sys.containers || []).map(c => ({
    id: c.id,
    name: c.name,
    technology: c.technology || null,
    description: c.description || '',
    componentCount: (c.components || []).length,
  }));
  return {
    system: sys.name,
    systemId: sys.id,
    total: containers.length,
    containers: truncate(containers, 75, 'Too many containers. Search or filter by tag.'),
  };
};

// components
commands.components = (name) => {
  const el = resolveElement(name);
  if (el.error || el.disambiguation) return el;
  // Find the container
  let container = null;
  for (const sys of manifest.softwareSystems || []) {
    for (const c of sys.containers || []) {
      if (c.id === el.id || (el.type === 'Container' && c.name === el.name && sys.name === el.systemName)) {
        container = c;
        break;
      }
    }
    if (container) break;
  }
  if (!container && el.type !== 'Container') {
    return { error: `"${el.name}" is a ${el.type}, not a Container. Use containers command on its parent.` };
  }
  if (!container) return { error: `Container data not found for "${el.name}".` };
  const components = (container.components || []).map(comp => ({
    id: comp.id,
    name: comp.name,
    technology: comp.technology || null,
    description: comp.description || '',
    tags: comp.tags || [],
  }));
  return {
    container: container.name,
    containerId: container.id,
    system: el.systemName,
    total: components.length,
    components: truncate(components, 50, 'Too many components. Search or filter by tag.'),
  };
};

// relationships
commands.relationships = (name) => {
  const el = resolveElement(name);
  if (el.error || el.disambiguation) return el;
  const { outbound, inbound } = getRels(el.id);
  return {
    element: { id: el.id, name: el.name, type: el.type },
    outbound: truncate(outbound.map(formatRel), 40, 'Too many outbound relationships. Try depends-on for grouped view.'),
    inbound: truncate(inbound.map(formatRel), 40, 'Too many inbound relationships. Try depended-by for grouped view.'),
  };
};

// tag
commands.tag = (tagName) => {
  if (!tagName) return { error: 'Provide a tag name.' };
  // Case-insensitive tag lookup
  const tagKey = Object.keys(manifest.tagIndex || {}).find(t => t.toLowerCase() === tagName.toLowerCase());
  if (!tagKey) {
    const available = Object.keys(manifest.tagIndex || {}).filter(t => t.toLowerCase().includes(tagName.toLowerCase()));
    return { error: `Tag "${tagName}" not found.`, suggestions: available.slice(0, 10) };
  }
  const ids = manifest.tagIndex[tagKey] || [];
  const groups = { Person: [], SoftwareSystem: [], Container: [], Component: [] };
  for (const id of ids) {
    const el = elementById.get(id);
    if (el && groups[el.type]) {
      groups[el.type].push({ id: el.id, name: el.name, parentName: el.parentName });
    }
  }
  const result = { tag: tagKey, totalElements: ids.length };
  for (const [type, items] of Object.entries(groups)) {
    if (items.length > 0) result[type] = truncate(items, 50, `${items.length} total. Narrow with search.`);
  }
  return result;
};

// views
commands.views = (query) => {
  if (!query) return { error: 'Provide a search query for views.' };
  const lower = query.toLowerCase();
  const results = [];
  for (const [viewType, viewList] of Object.entries(manifest.views || {})) {
    for (const v of viewList) {
      if (
        (v.key && v.key.toLowerCase().includes(lower)) ||
        (v.title && v.title.toLowerCase().includes(lower)) ||
        (v.description && v.description.toLowerCase().includes(lower))
      ) {
        results.push({
          key: v.key,
          type: viewType,
          title: v.title || '',
          description: v.description || '',
          elementCount: (v.elementIds || []).length,
        });
      }
    }
  }
  if (results.length === 0) return { error: `No views matching "${query}".` };
  return { query, total: results.length, views: truncate(results, 30, 'Narrow your view search.') };
};

// view-detail
commands['view-detail'] = (key) => {
  if (!key) return { error: 'Provide a view key.' };
  const lowerKey = key.toLowerCase();
  for (const [viewType, viewList] of Object.entries(manifest.views || {})) {
    for (const v of viewList) {
      if (v.key && v.key.toLowerCase() === lowerKey) {
        const elements = (v.elementIds || []).map(id => {
          const el = elementById.get(id);
          return el ? { id, name: el.name, type: el.type, parentName: el.parentName } : { id, name: '(unknown)' };
        });
        return {
          key: v.key,
          type: viewType,
          title: v.title || '',
          description: v.description || '',
          scopeId: v.scopeId || null,
          baseViewKey: v.baseViewKey || null,
          environment: v.environment || null,
          elementCount: elements.length,
          elements: truncate(elements, 60, 'View has many elements. Cross-reference with relationships.'),
        };
      }
    }
  }
  return { error: `View "${key}" not found.` };
};

// people
commands.people = () => {
  const people = (manifest.people || []).map(p => {
    const { outbound, inbound } = getRels(p.id);
    return {
      id: p.id,
      name: p.name,
      description: p.description || '',
      tags: p.tags || [],
      interactions: truncate(
        [...outbound.map(r => ({ direction: 'uses', targetId: r.destinationId, targetName: r.destinationName, description: r.description })),
         ...inbound.map(r => ({ direction: 'used by', sourceId: r.sourceId, sourceName: r.sourceName, description: r.description }))],
        15, 'Use relationships command for full list.'
      ),
    };
  });
  return { total: people.length, people };
};

// depends-on (outbound grouped by target type)
commands['depends-on'] = (name) => {
  const el = resolveElement(name);
  if (el.error || el.disambiguation) return el;
  const { outbound } = getRels(el.id);
  const groups = {};
  for (const r of outbound) {
    const target = elementById.get(r.destinationId);
    const type = target ? target.type : 'Unknown';
    if (!groups[type]) groups[type] = [];
    groups[type].push(formatRel(r));
  }
  const result = { element: { id: el.id, name: el.name, type: el.type }, dependsOn: {} };
  for (const [type, rels] of Object.entries(groups)) {
    result.dependsOn[type] = truncate(rels, 30, `${rels.length} total ${type} dependencies.`);
  }
  return result;
};

// depended-by (inbound grouped by source type)
commands['depended-by'] = (name) => {
  const el = resolveElement(name);
  if (el.error || el.disambiguation) return el;
  const { inbound } = getRels(el.id);
  const groups = {};
  for (const r of inbound) {
    const source = elementById.get(r.sourceId);
    const type = source ? source.type : 'Unknown';
    if (!groups[type]) groups[type] = [];
    groups[type].push(formatRel(r));
  }
  const result = { element: { id: el.id, name: el.name, type: el.type }, dependedBy: {} };
  for (const [type, rels] of Object.entries(groups)) {
    result.dependedBy[type] = truncate(rels, 30, `${rels.length} total ${type} dependents.`);
  }
  return result;
};

// federation
commands.federation = () => {
  const services = (manifest.federatedServices || []).map(s => ({
    name: s.name,
    path: s.path,
    fileCount: s.fileCount,
    lineCount: s.lineCount,
  }));
  return {
    total: services.length,
    services: truncate(services, 100, 'Showing first 100 federated services.'),
  };
};

// element (direct ID lookup)
commands.element = (idOrName) => {
  const el = resolveElement(idOrName);
  if (el.error || el.disambiguation) return el;
  const { outbound, inbound } = getRels(el.id);
  return {
    ...el,
    outbound: truncate(outbound.map(formatRel), 25, 'Use depends-on for grouped view.'),
    inbound: truncate(inbound.map(formatRel), 25, 'Use depended-by for grouped view.'),
  };
};

// ─── Dispatch ───────────────────────────────────────────────────────────────
const USAGE = `Usage: node scripts/query-manifest.mjs <command> [argument]

Commands:
  overview                  Stats, platform summary, top tags
  search <query>            Fuzzy substring match across elements
  system <name>             System details + container summary
  containers <system>       Container list for a system
  components <container>    Component list for a container
  relationships <element>   Inbound + outbound relationships
  tag <tag-name>            Elements with that tag, grouped by type
  views <query>             Search views by key/title/description
  view-detail <view-key>    Full view with resolved element names
  people                    All people + their interactions
  depends-on <element>      Outbound dependencies grouped by type
  depended-by <element>     Inbound dependencies grouped by type
  federation                Federated service inventory
  element <id-or-name>      Direct lookup + relationships`;

const [command, ...rest] = process.argv.slice(2);
const arg = rest.join(' ');

if (!command || !commands[command]) {
  if (command) process.stderr.write(`Unknown command: ${command}\n\n`);
  process.stderr.write(USAGE + '\n');
  process.exit(1);
}

const result = commands[command](arg || undefined);
out(result);

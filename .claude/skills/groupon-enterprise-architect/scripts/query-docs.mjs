#!/usr/bin/env node
/**
 * query-docs.mjs
 *
 * Zero-dependency CLI for querying the docs catalog and reading
 * service documentation. Companion to query-manifest.mjs.
 *
 * Usage: node scripts/query-docs.mjs <command> [argument]
 */
import { readFileSync, existsSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const repoRoot = resolve(__dirname, '..');
const catalogPath = resolve(repoRoot, 'data/docs-catalog.json');
const importDir = resolve(repoRoot, 'data/import');

if (!existsSync(catalogPath)) {
  process.stderr.write(
    `Catalog not found: ${catalogPath}\n` +
    'Run: node scripts/build-docs-catalog.mjs\n'
  );
  process.exit(1);
}

const catalog = JSON.parse(readFileSync(catalogPath, 'utf8'));

function out(obj) {
  process.stdout.write(JSON.stringify(obj, null, 2) + '\n');
}

function truncate(list, limit, hint) {
  if (list.length <= limit) return list;
  const result = list.slice(0, limit);
  result.push({ truncated: true, showing: limit, total: list.length, hint: hint || 'Narrow your query.' });
  return result;
}

function findService(name) {
  const lower = name.toLowerCase();
  const exact = catalog.services.find(s => s.name.toLowerCase() === lower);
  if (exact) return [exact];

  const matches = catalog.services.filter(s =>
    s.name.toLowerCase().includes(lower) ||
    (s.description && s.description.toLowerCase().includes(lower)) ||
    (s.title && s.title.toLowerCase().includes(lower))
  );
  return matches;
}

function briefService(s) {
  return {
    name: s.name,
    description: s.description,
    platform: s.platform,
    domain: s.domain,
    team: s.team,
    language: s.techStack?.language || null,
    framework: s.techStack?.framework || null,
    docsCount: s.docsGenerated.length + s.docsManual.length,
    flowCount: s.flows.length,
    hasManualDocs: s.docsManual.length > 0,
  };
}

const commands = {};

commands.overview = () => {
  const stats = catalog._meta.stats;
  const topPlatforms = Object.entries(catalog.platforms)
    .map(([name, svcs]) => ({ name, count: svcs.length }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 10);
  const topDomains = Object.entries(catalog.domains)
    .map(([name, svcs]) => ({ name, count: svcs.length }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 15);
  return { stats, generatedAt: catalog._meta.generatedAt, topPlatforms, topDomains };
};

commands.service = (name) => {
  if (!name) return { error: 'Provide a service name.' };
  const matches = findService(name);
  if (matches.length === 0) return { error: `No service matching "${name}".` };
  if (matches.length > 1 && matches[0].name.toLowerCase() !== name.toLowerCase()) {
    return {
      disambiguation: truncate(matches.map(briefService), 10, 'Narrow your search.'),
      hint: `Multiple services match "${name}".`,
    };
  }
  const svc = matches[0];
  return {
    ...svc,
    docPaths: {
      generated: svc.docsGenerated.map(d => `data/import/${svc.name}/docs-generated/${d}.md`),
      manual: svc.docsManual.map(d => `data/import/${svc.name}/docs/${d}.md`),
    },
  };
};

commands.search = (query) => {
  if (!query) return { error: 'Provide a search query.' };
  const lower = query.toLowerCase();
  const results = catalog.services.filter(s =>
    s.name.toLowerCase().includes(lower) ||
    (s.description && s.description.toLowerCase().includes(lower)) ||
    (s.title && s.title.toLowerCase().includes(lower)) ||
    (s.domain && s.domain.toLowerCase().includes(lower)) ||
    (s.team && s.team.toLowerCase().includes(lower)) ||
    s.flows.some(f => f.toLowerCase().includes(lower))
  );
  if (results.length === 0) return { error: `No results for "${query}".` };
  return {
    query,
    total: results.length,
    services: truncate(results.map(briefService), 25, 'Too many results. Narrow search.'),
  };
};

commands.platform = (name) => {
  if (!name) return { error: 'Provide a platform name.', available: Object.keys(catalog.platforms) };
  const key = Object.keys(catalog.platforms).find(k => k.toLowerCase() === name.toLowerCase());
  if (!key) {
    return {
      error: `Platform "${name}" not found.`,
      available: Object.keys(catalog.platforms),
    };
  }
  const svcNames = catalog.platforms[key];
  const services = svcNames.map(n => catalog.services.find(s => s.name === n)).filter(Boolean);
  return {
    platform: key,
    total: services.length,
    services: truncate(services.map(briefService), 40, 'Many services. Use search to narrow.'),
  };
};

commands.domain = (name) => {
  if (!name) return { error: 'Provide a domain name.', available: Object.keys(catalog.domains).slice(0, 20) };
  const lower = name.toLowerCase();
  const matching = Object.entries(catalog.domains).filter(([k]) => k.toLowerCase().includes(lower));
  if (matching.length === 0) {
    const available = Object.keys(catalog.domains).filter(k => k.toLowerCase().includes(lower.split(' ')[0]));
    return { error: `No domain matching "${name}".`, suggestions: available.slice(0, 10) };
  }
  const results = {};
  for (const [key, svcNames] of matching) {
    const services = svcNames.map(n => catalog.services.find(s => s.name === n)).filter(Boolean);
    results[key] = truncate(services.map(briefService), 20, 'Use service command for details.');
  }
  return { query: name, domains: results };
};

commands.team = (name) => {
  if (!name) return { error: 'Provide a team name.', available: Object.keys(catalog.teams).slice(0, 20) };
  const lower = name.toLowerCase();
  const matching = Object.entries(catalog.teams).filter(([k]) => k.toLowerCase().includes(lower));
  if (matching.length === 0) {
    return { error: `No team matching "${name}".`, available: Object.keys(catalog.teams).slice(0, 20) };
  }
  const results = {};
  for (const [key, svcNames] of matching) {
    const services = svcNames.map(n => catalog.services.find(s => s.name === n)).filter(Boolean);
    results[key] = services.map(briefService);
  }
  return { query: name, teams: results };
};

commands.tech = (name) => {
  if (!name) return { error: 'Provide a technology name (e.g., Java, TypeScript, Rails, Go).' };
  const lower = name.toLowerCase();
  const results = catalog.services.filter(s => {
    if (!s.techStack) return false;
    return Object.values(s.techStack).some(v => v && v.toLowerCase().includes(lower));
  });
  if (results.length === 0) return { error: `No services using "${name}".` };
  return {
    technology: name,
    total: results.length,
    services: truncate(results.map(briefService), 30, 'Many results. Narrow search.'),
  };
};

commands.flows = (query) => {
  if (!query) return { error: 'Provide a search query for flows.' };
  const lower = query.toLowerCase();
  const results = [];
  for (const svc of catalog.services) {
    for (const flow of svc.flows) {
      if (flow.toLowerCase().includes(lower)) {
        results.push({
          service: svc.name,
          flow,
          path: `data/import/${svc.name}/docs-generated/flows/${flow}.md`,
          platform: svc.platform,
          domain: svc.domain,
        });
      }
    }
  }
  if (results.length === 0) return { error: `No flows matching "${query}".` };
  return {
    query,
    total: results.length,
    flows: truncate(results, 30, 'Many matching flows. Narrow search.'),
  };
};

commands.doc = (args) => {
  if (!args) return { error: 'Usage: doc <service> <doc-type>\nDoc types: overview, architecture-context, api-surface, events, data-stores, integrations, configuration, deployment, runbook, flows/<name>' };
  const parts = args.split(/\s+/);
  if (parts.length < 2) return { error: 'Provide both service name and doc type. Example: doc aidg overview' };
  const svcName = parts[0];
  const docType = parts.slice(1).join(' ');

  const matches = findService(svcName);
  if (matches.length === 0) return { error: `No service matching "${svcName}".` };
  const svc = matches[0];

  const genPath = resolve(importDir, svc.name, 'docs-generated', `${docType}.md`);
  const manPath = resolve(importDir, svc.name, 'docs', `${docType}.md`);

  const result = { service: svc.name, docType, sources: [] };

  if (existsSync(genPath)) {
    result.sources.push({
      type: 'generated',
      path: `data/import/${svc.name}/docs-generated/${docType}.md`,
      content: readFileSync(genPath, 'utf8'),
    });
  }
  if (existsSync(manPath)) {
    result.sources.push({
      type: 'manual',
      path: `data/import/${svc.name}/docs/${docType}.md`,
      content: readFileSync(manPath, 'utf8'),
    });
  }

  if (result.sources.length === 0) {
    return {
      error: `No "${docType}" doc found for ${svc.name}.`,
      available: {
        generated: svc.docsGenerated,
        manual: svc.docsManual,
      },
    };
  }
  return result;
};

const USAGE = `Usage: node scripts/query-docs.mjs <command> [argument]

Commands:
  overview                     Stats, top platforms, top domains
  service <name>               Service details + all available doc paths
  search <query>               Search services by name, description, domain, flows
  platform <name>              All services on a platform (Continuum, Encore, MBNXT)
  domain <name>                Services in a business domain
  team <name>                  Services owned by a team
  tech <technology>            Services using a technology (Java, TypeScript, Go, etc.)
  flows <query>                Search across all service flows
  doc <service> <doc-type>     Read a specific doc (overview, runbook, api-surface, etc.)`;

const [command, ...rest] = process.argv.slice(2);
const arg = rest.join(' ');

if (!command || !commands[command]) {
  if (command) process.stderr.write(`Unknown command: ${command}\n\n`);
  process.stderr.write(USAGE + '\n');
  process.exit(1);
}

const result = commands[command](arg || undefined);
out(result);

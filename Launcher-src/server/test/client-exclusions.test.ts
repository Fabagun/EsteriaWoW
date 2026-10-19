import assert from 'node:assert/strict';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';
import fs from 'fs-extra';
import { buildCache } from '../src/cache.js';
import { buildV2Manifest } from '../src/v2-manifest.js';
import { isExcludedClientPath } from '../src/client-exclusions.js';

test('both manifests exclude runtime files at every depth, ignoring case', async () => {
	const root = await fs.mkdtemp(path.join(os.tmpdir(), 'cdn-exclusions-'));
	try {
		const excluded = ['debug.log', 'Extensions/trace.LOG', 'Logs/state.txt',
			'Errors/crash.txt', 'Cache/data.bin', 'Extensions/lOgS/state.txt',
			'Extensions/ERRORS/crash.txt', 'Extensions/cache/data.bin'];
		for (const file of ['Wow.exe', 'Extensions/keep.dll', ...excluded]) {
			await fs.outputFile(path.join(root, file), 'fixture');
		}
		const v2 = await buildV2Manifest(root, 'live');
		assert.deepEqual(v2.files.map(file => file.path), ['Extensions/keep.dll', 'Wow.exe']);
		await buildCache(root);
		const legacy = await fs.readJSON(path.join(root, 'manifest.json'));
		const walk = (node: any, prefix = ''): string[] => (node.files || []).flatMap((child: any) => {
			const relative = prefix ? `${prefix}/${child.name}` : child.name;
			return child.type === 'file' ? [relative] : walk(child, relative);
		});
		assert.deepEqual(walk(legacy.root), ['Extensions/keep.dll', 'Wow.exe']);
		assert.equal(isExcludedClientPath('Extensions\\CACHE\\state.bin'), true);
		assert.equal(isExcludedClientPath('catalog.json'), false);
		assert.equal(isExcludedClientPath('Data/cache-index.bin'), false);
	} finally {
		await fs.remove(root);
	}
});

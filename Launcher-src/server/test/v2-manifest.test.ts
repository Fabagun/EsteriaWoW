import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';

import fs from 'fs-extra';

import { buildV2Manifest } from '../src/v2-manifest.js';

test('builds a flat SHA-256 client manifest and skips player-owned state', async () => {
	const root = await fs.mkdtemp(path.join(os.tmpdir(), 'esteria-v2-manifest-'));
	try {
		await fs.outputFile(path.join(root, 'Wow.exe'), 'wow-fixture');
		await fs.outputFile(path.join(root, 'Data', 'patch-E.mpq'), 'patch-fixture');
		await fs.outputFile(path.join(root, 'Data', 'patch-K.mpq', 'DBFilesClient', 'Example.dbc'), 'bundle-member');
		await fs.outputFile(path.join(root, 'Data', 'patch-K.mpq.zip'), 'bundle-transport');
		await fs.outputFile(path.join(root, 'Logs', 'connection.log'), 'private-log');
		await fs.outputFile(path.join(root, 'Eclipse', 'logs', 'eclipse.log'), 'rotating-log');
		await fs.outputFile(path.join(root, 'WTF', 'Account', 'Example', 'SavedVariables.lua'), 'private-state');

		const manifest = await buildV2Manifest(root, 'live');
		assert.equal(manifest.schemaVersion, 2);
		assert.equal(manifest.channel, 'live');
		assert.deepEqual(
			manifest.files.map(file => file.path),
			['Data/patch-E.mpq', 'Data/patch-K.mpq/DBFilesClient/Example.dbc', 'Wow.exe']
		);
		assert.equal(manifest.files.some(file => file.path === 'Data/patch-K.mpq.zip'), false);
		assert.equal(manifest.bundles?.length, 1);
		assert.equal(manifest.bundles?.[0]?.path, 'Data/patch-K.mpq');
		assert.equal(manifest.bundles?.[0]?.archive, 'Data/patch-K.mpq.zip');

		const wow = manifest.files.find(file => file.path === 'Wow.exe');
		assert.ok(wow);
		assert.equal(
			wow.sha256,
			crypto.createHash('sha256').update('wow-fixture').digest('hex')
		);
		assert.equal(wow.url, '/client/live/Wow.exe');
	} finally {
		await fs.remove(root);
	}
});

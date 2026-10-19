import crypto from 'node:crypto';
import fs from 'fs-extra';
import path from 'node:path';
import { isExcludedClientPath } from './client-exclusions.js';

export type V2ManifestFile = {
	path: string;
	sha256: string;
	size: number;
	url: string;
};

export type V2ManifestBundle = {
	path: string;
	archive: string;
	sha256: string;
	size: number;
	url: string;
};

export type V2Manifest = {
	schemaVersion: 2;
	channel: string;
	version: string;
	files: V2ManifestFile[];
	bundles?: V2ManifestBundle[];
};

type BundleConfig = {
	path: string;
	archive: string;
};

const DEFAULT_BUNDLES: BundleConfig[] = [
	{ path: 'Data/Patch-Housing.MPQ', archive: 'Data/Patch-Housing.MPQ.zip' },
	{ path: 'Data/patch-K.mpq', archive: 'Data/patch-K.mpq.zip' }
];

const SKIP_FILES = new Set([
	'manifest.json',
	'manifest.json.tmp',
	'manifest-v2.json',
	'manifest-v2.json.tmp',
	'.manifest-overrides.json',
	'.delivery-bundles.json',
	'.gitkeep'
]);

const SKIP_DIRS = new Set([
	'Cache',
	'WTF',
	'Errors',
	'Logs',
	'Eclipse/logs',
	'Screenshots',
	'WDB',
	'WTF/Account',
	'.launcher'
]);

const toPosix = (value: string) => value.split(path.sep).join('/');
const normalize = (value: string) => toPosix(value).replace(/^\.\//, '');

const shouldSkipDir = (relativePath: string) => SKIP_DIRS.has(normalize(relativePath));

const sha256File = (filePath: string): Promise<string> =>
	new Promise((resolve, reject) => {
		const hash = crypto.createHash('sha256');
		const stream = fs.createReadStream(filePath, { highWaterMark: 8 * 1024 * 1024 });
		stream.on('error', reject);
		stream.on('data', chunk => hash.update(chunk));
		stream.on('end', () => resolve(hash.digest('hex')));
	});

const encodeUrlPath = (relativePath: string) =>
	normalize(relativePath)
		.split('/')
		.map(encodeURIComponent)
		.join('/');

const loadBundleConfig = async (root: string): Promise<BundleConfig[]> => {
	const configPath = path.join(root, '.delivery-bundles.json');
	if (!(await fs.pathExists(configPath))) return DEFAULT_BUNDLES;
	try {
		const parsed = await fs.readJSON(configPath);
		if (!Array.isArray(parsed)) throw new Error('root must be an array');
		return parsed
			.filter(entry => entry && typeof entry.path === 'string' && typeof entry.archive === 'string')
			.map(entry => ({ path: normalize(entry.path), archive: normalize(entry.archive) }));
	} catch (error) {
		throw new Error(`Invalid ${configPath}: ${error instanceof Error ? error.message : String(error)}`);
	}
};

export const buildV2Manifest = async (
	sourceDir: string,
	channel: string,
	onProgress?: (done: number, total: number, currentFile: string) => void
): Promise<V2Manifest> => {
	const root = path.resolve(sourceDir);
	const bundleConfig = await loadBundleConfig(root);
	const activeBundleConfig: BundleConfig[] = [];
	for (const bundle of bundleConfig) {
		if (isExcludedClientPath(bundle.path) || isExcludedClientPath(bundle.archive)) continue;
		const target = path.join(root, ...normalize(bundle.path).split('/'));
		const archive = path.join(root, ...normalize(bundle.archive).split('/'));
		if ((await fs.pathExists(target)) && (await fs.pathExists(archive))) {
			activeBundleConfig.push(bundle);
		}
	}
	const bundleArchives = new Set(bundleConfig.map(bundle => normalize(bundle.archive).toLowerCase()));

	const candidates: { fullPath: string; relativePath: string; size: number }[] = [];
	const collect = async (dir: string, prefix = ''): Promise<void> => {
		const names = (await fs.readdir(dir)).sort();
		for (const name of names) {
			if (SKIP_FILES.has(name)) continue;
			const fullPath = path.join(dir, name);
			const relativePath = prefix ? path.join(prefix, name) : name;
			const relativePosix = normalize(relativePath);
			if (isExcludedClientPath(relativePosix)) continue;
			const stat = await fs.stat(fullPath);
			if (stat.isDirectory()) {
				if (!shouldSkipDir(relativePosix)) await collect(fullPath, relativePath);
				continue;
			}
			if (!stat.isFile()) continue;
			if (bundleArchives.has(relativePosix.toLowerCase())) continue;
			candidates.push({ fullPath, relativePath: relativePosix, size: stat.size });
		}
	};

	await collect(root);
	const totalWork = candidates.length + activeBundleConfig.length;
	const files: V2ManifestFile[] = [];
	const bundles: V2ManifestBundle[] = [];
	let done = 0;

	for (const candidate of candidates) {
		files.push({
			path: candidate.relativePath,
			sha256: await sha256File(candidate.fullPath),
			size: candidate.size,
			url: `/client/${encodeURIComponent(channel)}/${encodeUrlPath(candidate.relativePath)}`
		});
		done += 1;
		onProgress?.(done, totalWork, candidate.relativePath);
	}

	for (const config of activeBundleConfig) {
		const archive = normalize(config.archive);
		const archiveFull = path.join(root, ...archive.split('/'));
		const stat = await fs.stat(archiveFull);
		bundles.push({
			path: normalize(config.path),
			archive,
			sha256: await sha256File(archiveFull),
			size: stat.size,
			url: `/client/${encodeURIComponent(channel)}/${encodeUrlPath(archive)}`
		});
		done += 1;
		onProgress?.(done, totalWork, archive);
	}

	const version =
		process.env.CLIENT_BUILD_ID?.trim() ||
		`${channel}-${new Date().toISOString().replace(/[-:.TZ]/g, '').slice(0, 14)}`;

	return {
		schemaVersion: 2,
		channel,
		version,
		files,
		...(bundles.length ? { bundles } : {})
	};
};

export const writeV2Manifest = async (
	sourceDir: string,
	channel: string,
	onProgress?: (done: number, total: number, currentFile: string) => void
): Promise<V2Manifest> => {
	const manifest = await buildV2Manifest(sourceDir, channel, onProgress);
	const target = path.join(sourceDir, 'manifest-v2.json');
	const temp = `${target}.tmp`;
	await fs.writeJSON(temp, manifest, { spaces: 2 });
	await fs.move(temp, target, { overwrite: true });
	return manifest;
};

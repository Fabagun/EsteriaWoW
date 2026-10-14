import net from 'node:net';
import path from 'node:path';

import express from 'express';
import fs from 'fs-extra';
import { buildCache, type BuildProgress } from './cache.js';
import { getAddons, warmUp as warmUpAddons } from './addons-resolver.js';
import { writeV2Manifest } from './v2-manifest.js';
import { attachSocial } from './social/routes.js';

const SourceDir = process.env.SOURCE_DIR || './client';
const ClientRootDir = process.env.CLIENT_ROOT_DIR || '';
const LauncherUpdatesDir = process.env.LAUNCHER_UPDATES_DIR || './launcher-updates';
const AddonsDir = process.env.ADDONS_DIR || './addons';
const DefaultChannel = process.env.CLIENT_CHANNEL || 'live';
const ConfiguredChannels = (process.env.CLIENT_CHANNELS || 'live,ptr')
	.split(',')
	.map(value => value.trim())
	.filter(Boolean);
const NewsFile = process.env.NEWS_FILE || './news.json';
const StatusFile = process.env.STATUS_FILE || './status.json';
const SocialFile = process.env.SOCIAL_FILE || './social.json';
const ArmoryFile = process.env.ARMORY_FILE || './armory.json';
const DatabaseFile = process.env.DATABASE_FILE || './database-index.json';
const RealmHost = process.env.REALM_HOST || '127.0.0.1';
const RealmPort = Number.parseInt(process.env.REALM_PORT || '3724', 10) || 3724;
const SocialDataDir = process.env.SOCIAL_DATA_DIR || './social-data';
const SocialPublicBaseUrl = (process.env.SOCIAL_PUBLIC_BASE_URL || '').replace(/\/+$/, '');

const app = express();
const port = Number.parseInt(process.env.PORT || '7384', 10) || 7384;

app.use('/launcher-updates', express.static(LauncherUpdatesDir));
app.use('/addons', express.static(AddonsDir));

const freshProgress = (): BuildProgress => ({
	state: 'idle',
	done: 0,
	total: 0,
	currentFile: '',
	startedAt: null,
	finishedAt: null,
	error: null
});

const validChannel = (channel: string) => /^[A-Za-z0-9._-]+$/.test(channel);

const resolveChannelDir = (channel: string): string | null => {
	if (!validChannel(channel)) return null;
	if (ClientRootDir) return path.join(ClientRootDir, channel);

	const source = path.resolve(SourceDir);
	const sourceName = path.basename(source).toLowerCase();
	if (sourceName === DefaultChannel.toLowerCase()) {
		return channel.toLowerCase() === DefaultChannel.toLowerCase()
			? source
			: path.join(path.dirname(source), channel);
	}

	const defaultChild = path.join(source, DefaultChannel);
	if (fs.existsSync(defaultChild)) return path.join(source, channel);
	return channel.toLowerCase() === DefaultChannel.toLowerCase() ? source : null;
};

const requireChannelDir = async (channel: string): Promise<string | null> => {
	const dir = resolveChannelDir(channel);
	if (!dir || !(await fs.pathExists(dir))) return null;
	const stat = await fs.stat(dir);
	if (!stat.isDirectory()) return null;
	// A channel without Wow.exe is an empty or half-staged tree. Publishing a manifest
	// for it would advertise a client the launcher can never start.
	if (!(await fs.pathExists(path.join(dir, 'Wow.exe')))) return null;
	return dir;
};

/** An unreadable or empty manifest is a leftover from a channel with no staged client. */
const manifestHasFiles = async (file: string): Promise<boolean> => {
	try {
		const value = await fs.readJSON(file);
		return Array.isArray(value?.files) && value.files.length > 0;
	} catch {
		return false;
	}
};

const legacyProgress = new Map<string, BuildProgress>();
const legacyInFlight = new Map<string, Promise<void>>();
const v2Progress = new Map<string, BuildProgress>();
const v2InFlight = new Map<string, Promise<void>>();

const progressFor = (collection: Map<string, BuildProgress>, channel: string): BuildProgress => {
	let progress = collection.get(channel);
	if (!progress) {
		progress = freshProgress();
		collection.set(channel, progress);
	}
	return progress;
};

const ensureLegacyManifestBuilt = async (channel: string): Promise<void> => {
	const existing = legacyInFlight.get(channel);
	if (existing) return existing;
	const dir = await requireChannelDir(channel);
	if (!dir) throw new Error(`Client channel does not exist: ${channel}`);
	const progress = progressFor(legacyProgress, channel);
	progress.state = 'building';
	progress.done = 0;
	progress.total = 0;
	progress.currentFile = '';
	progress.startedAt = Date.now();
	progress.finishedAt = null;
	progress.error = null;

	const promise = buildCache(dir, update => {
		progress.done = update.done;
		progress.total = update.total;
		progress.currentFile = update.currentFile;
	})
		.then(() => {
			progress.state = 'ready';
			progress.finishedAt = Date.now();
		})
		.catch(error => {
			progress.state = 'failed';
			progress.error = error instanceof Error ? error.message : String(error);
			progress.finishedAt = Date.now();
			throw error;
		})
		.finally(() => legacyInFlight.delete(channel));
	legacyInFlight.set(channel, promise);
	return promise;
};

const ensureV2ManifestBuilt = async (channel: string): Promise<void> => {
	const existing = v2InFlight.get(channel);
	if (existing) return existing;
	const dir = await requireChannelDir(channel);
	if (!dir) throw new Error(`Client channel does not exist: ${channel}`);
	const progress = progressFor(v2Progress, channel);
	progress.state = 'building';
	progress.done = 0;
	progress.total = 0;
	progress.currentFile = '';
	progress.startedAt = Date.now();
	progress.finishedAt = null;
	progress.error = null;

	const promise = writeV2Manifest(dir, channel, (done, total, currentFile) => {
		progress.done = done;
		progress.total = total;
		progress.currentFile = currentFile;
	})
		.then(() => {
			progress.state = 'ready';
			progress.finishedAt = Date.now();
		})
		.catch(error => {
			progress.state = 'failed';
			progress.error = error instanceof Error ? error.message : String(error);
			progress.finishedAt = Date.now();
			throw error;
		})
		.finally(() => v2InFlight.delete(channel));
	v2InFlight.set(channel, promise);
	return promise;
};

app.get('/api/build-status', (req, res) => {
	const channel = typeof req.query.channel === 'string' ? req.query.channel : DefaultChannel;
	res.json(progressFor(legacyProgress, channel));
});

app.get('/api/v2/build-status', (req, res) => {
	const channel = typeof req.query.channel === 'string' ? req.query.channel : DefaultChannel;
	res.json(progressFor(v2Progress, channel));
});

app.get('/api/v2/client/:version/manifest.json', async (req, res) => {
	const channel = req.params.version;
	const dir = await requireChannelDir(channel);
	if (!dir) {
		res.status(404).json({ error: 'unknown_channel' });
		return;
	}
	const manifestPath = path.join(dir, 'manifest-v2.json');
	if (await manifestHasFiles(manifestPath)) {
		res.json(await fs.readJSON(manifestPath));
		return;
	}
	void ensureV2ManifestBuilt(channel).catch(() => {});
	res.setHeader('Retry-After', '5');
	res.status(503).json({
		error: 'manifest_building',
		message: 'The SHA-256 client manifest is being built.',
		buildProgress: progressFor(v2Progress, channel)
	});
});

app.get('/api/file/:version/manifest.json', async (req, res) => {
	const channel = req.params.version;
	const dir = await requireChannelDir(channel);
	if (!dir) {
		res.status(404).json({ error: 'unknown_channel' });
		return;
	}
	const manifestPath = path.join(dir, 'manifest.json');
	if (await manifestHasFiles(manifestPath)) {
		res.json(await fs.readJSON(manifestPath));
		return;
	}
	void ensureLegacyManifestBuilt(channel).catch(() => {});
	res.setHeader('Retry-After', '5');
	res.status(503).json({
		error: 'manifest_building',
		message: 'Manifest is being built for the first time on this server.',
		buildProgress: progressFor(legacyProgress, channel)
	});
});

app.get('/client/:version/*', async (req: express.Request<{ version: string; 0: string }>, res) => {
	const rootDir = await requireChannelDir(req.params.version);
	if (!rootDir) {
		res.status(404).end();
		return;
	}
	const root = path.resolve(rootDir);
	const target = path.resolve(rootDir, req.params[0]);
	if (target !== root && !target.startsWith(root + path.sep)) {
		res.status(403).end();
		return;
	}
	res.sendFile(target);
});

app.get('/api/v2/addons/catalog.json', async (_req, res) => {
	const catalogPath = path.join(AddonsDir, 'catalog.json');
	if (!(await fs.pathExists(catalogPath))) {
		res.json({ schemaVersion: 1, addons: [] });
		return;
	}
	try {
		res.json(await fs.readJSON(catalogPath));
	} catch (error) {
		console.error('Failed to read addon catalog:', error);
		res.status(500).json({ error: 'invalid_addon_catalog' });
	}
});

app.get('/api/addons.json', async (req, res) => {
	try {
		const force = req.query.refresh === '1';
		res.json(await getAddons(force));
	} catch (error) {
		console.error('Failed to resolve addons:', error);
		res.status(500).json({ error: 'Failed to resolve addons' });
	}
});

app.get('/api/v2/news.json', async (_req, res) => {
	if (!(await fs.pathExists(NewsFile))) {
		res.json({ schemaVersion: 1, items: [] });
		return;
	}
	try {
		const value = await fs.readJSON(NewsFile);
		res.json(Array.isArray(value) ? { schemaVersion: 1, items: value } : value);
	} catch (error) {
		console.error('Failed to read news feed:', error);
		res.status(500).json({ error: 'invalid_news_feed' });
	}
});

const serveSnapshot = async (
	file: string,
	fallback: Record<string, unknown>,
	res: express.Response,
	errorCode: string
) => {
	if (!(await fs.pathExists(file))) {
		res.json(fallback);
		return;
	}
	try {
		res.json(await fs.readJSON(file));
	} catch (error) {
		console.error(`Failed to read ${file}:`, error);
		res.status(500).json({ error: errorCode });
	}
};

app.get('/api/v2/social.json', async (_req, res) => {
	if (await fs.pathExists(SocialFile)) {
		await serveSnapshot(SocialFile, { schemaVersion: 1, players: [] }, res, 'invalid_social_snapshot');
		return;
	}
	try {
		const status = (await fs.pathExists(StatusFile)) ? await fs.readJSON(StatusFile) : {};
		const onlineCharacters = Array.isArray(status?.onlineCharacters) ? status.onlineCharacters : [];
		res.json({
			schemaVersion: 1,
			players: onlineCharacters.map((character: Record<string, unknown>) => ({
				name: character.name,
				displayName: character.name,
				presence: character.away ? 'away' : 'online',
				character
			}))
		});
	} catch (error) {
		console.error('Failed to derive social presence snapshot:', error);
		res.json({ schemaVersion: 1, players: [] });
	}
});

app.get('/api/v2/armory/characters.json', async (req, res) => {
	if (!(await fs.pathExists(ArmoryFile))) {
		res.json({ schemaVersion: 1, characters: [] });
		return;
	}
	try {
		const snapshot = await fs.readJSON(ArmoryFile);
		const source = Array.isArray(snapshot) ? snapshot : Array.isArray(snapshot?.characters) ? snapshot.characters : [];
		const q = typeof req.query.q === 'string' ? req.query.q.trim().toLowerCase() : '';
		const characters = q
			? source.filter((character: Record<string, unknown>) =>
				[
					character.name,
					character.guild,
					character.race,
					character.className,
					character.class,
					character.spec,
					character.zone
				]
					.filter(Boolean)
					.join(' ')
					.toLowerCase()
					.includes(q)
			)
			: source;
		res.json({ schemaVersion: 1, characters: characters.slice(0, q ? 100 : 250) });
	} catch (error) {
		console.error('Failed to read armory snapshot:', error);
		res.status(500).json({ error: 'invalid_armory_snapshot' });
	}
});

app.get('/api/v2/database/index.json', async (req, res) => {
	if (!(await fs.pathExists(DatabaseFile))) {
		res.json({ schemaVersion: 1, entries: [] });
		return;
	}
	try {
		const snapshot = await fs.readJSON(DatabaseFile);
		const source = Array.isArray(snapshot) ? snapshot : Array.isArray(snapshot?.entries) ? snapshot.entries : [];
		const q = typeof req.query.q === 'string' ? req.query.q.trim().toLowerCase() : '';
		const type = typeof req.query.type === 'string' ? req.query.type.trim().toLowerCase() : '';
		const entries = source.filter((entry: Record<string, unknown>) => {
			if (type && type !== 'all' && String(entry.type || '').toLowerCase() !== type) return false;
			if (!q) return true;
			return String(entry.id ?? '').includes(q) || [entry.name, entry.subtitle, entry.description, entry.type]
				.filter(Boolean)
				.join(' ')
				.toLowerCase()
				.includes(q);
		});
		res.json({ schemaVersion: 1, entries: entries.slice(0, q ? 200 : 300) });
	} catch (error) {
		console.error('Failed to read database snapshot:', error);
		res.status(500).json({ error: 'invalid_database_snapshot' });
	}
});

const checkRealm = () =>
	new Promise<boolean>(resolve => {
		const socket = net.createConnection({ host: RealmHost, port: RealmPort });
		const done = (online: boolean) => {
			socket.destroy();
			resolve(online);
		};
		socket.setTimeout(1500);
		socket.once('connect', () => done(true));
		socket.once('timeout', () => done(false));
		socket.once('error', () => done(false));
	});

app.get('/api/v2/status', async (_req, res) => {
	let published: Record<string, unknown> = {};
	if (await fs.pathExists(StatusFile)) {
		try {
			const value = await fs.readJSON(StatusFile);
			if (value && typeof value === 'object' && !Array.isArray(value)) published = value;
		} catch (error) {
			console.error('Failed to read status file:', error);
		}
	}

	const channels: Record<string, unknown> = {};
	for (const channel of [...new Set([...ConfiguredChannels, DefaultChannel])]) {
		const dir = await requireChannelDir(channel);
		if (!dir) {
			channels[channel] = { available: false };
			continue;
		}
		let version: string | null = null;
		const manifestPath = path.join(dir, 'manifest-v2.json');
		if (await fs.pathExists(manifestPath)) {
			try {
				version = String((await fs.readJSON(manifestPath)).version || '') || null;
			} catch {}
		}
		channels[channel] = {
			available: true,
			version,
			build: progressFor(v2Progress, channel).state
		};
	}

	res.json({
		...published,
		realm: { online: await checkRealm(), host: RealmHost, port: RealmPort },
		channels,
		serverTime: new Date().toISOString()
	});
});

app.get('/health', (_req, res) => {
	res.json({ ok: true, channels: [...new Set([...ConfiguredChannels, DefaultChannel])] });
});

const newestSourceMtime = async (dir: string): Promise<number> => {
	let newest = 0;
	const entries = await fs.readdir(dir);
	for (const name of entries) {
		if (
			name === 'manifest.json' ||
			name === 'manifest.json.tmp' ||
			name === 'manifest-v2.json' ||
			name === 'manifest-v2.json.tmp'
		)
			continue;
		const full = path.join(dir, name);
		const stat = await fs.stat(full);
		if (stat.isDirectory()) {
			const inner = await newestSourceMtime(full);
			if (inner > newest) newest = inner;
		} else if (stat.mtimeMs > newest) {
			newest = stat.mtimeMs;
		}
	}
	return newest;
};

const prewarmChannel = async (channel: string) => {
	const dir = await requireChannelDir(channel);
	if (!dir) return;

	const legacyManifest = path.join(dir, 'manifest.json');
	try {
		if (!(await manifestHasFiles(legacyManifest))) {
			await ensureLegacyManifestBuilt(channel);
		} else {
			const manifestStat = await fs.stat(legacyManifest);
			if ((await newestSourceMtime(dir)) > manifestStat.mtimeMs) await ensureLegacyManifestBuilt(channel);
			else {
				const progress = progressFor(legacyProgress, channel);
				progress.state = 'ready';
				progress.finishedAt = Date.now();
			}
		}
	} catch (error) {
		console.error(`Legacy manifest pre-warm failed for ${channel}:`, error);
	}

	const v2Manifest = path.join(dir, 'manifest-v2.json');
	try {
		if (!(await manifestHasFiles(v2Manifest))) {
			await ensureV2ManifestBuilt(channel);
		} else {
			const manifestStat = await fs.stat(v2Manifest);
			if ((await newestSourceMtime(dir)) > manifestStat.mtimeMs) await ensureV2ManifestBuilt(channel);
			else {
				const progress = progressFor(v2Progress, channel);
				progress.state = 'ready';
				progress.finishedAt = Date.now();
			}
		}
	} catch (error) {
		const progress = progressFor(v2Progress, channel);
		progress.state = 'failed';
		progress.error = error instanceof Error ? error.message : String(error);
		console.error(`SHA-256 manifest pre-warm failed for ${channel}:`, error);
	}
};

try {
	const privateRoot = path.resolve(SocialDataDir);
	for (const publicRoot of [SourceDir, ClientRootDir, LauncherUpdatesDir, AddonsDir].filter(Boolean)) {
		const relative = path.relative(path.resolve(publicRoot), privateRoot);
		if (!relative || (!relative.startsWith(`..${path.sep}`) && relative !== '..' && !path.isAbsolute(relative)))
			throw new Error('SOCIAL_DATA_DIR must be outside client, addon, and updater static roots.');
	}
	await attachSocial(app, { dataDir: SocialDataDir, publicBaseUrl: SocialPublicBaseUrl });
} catch (error) {
	console.error('Social API disabled - could not open its data directory:', error);
}

app.listen(port, () => {
	console.log(`Server listening on port ${port}`);
	warmUpAddons();
	for (const channel of [...new Set([...ConfiguredChannels, DefaultChannel])]) {
		void prewarmChannel(channel);
	}
});

import path from 'node:path';

import express from 'express';

import { ApiError, SocialService } from './service.js';
import { mediaTypes, Store, sniffMediaType } from './store.js';
import type { MediaExt, MediaKind } from './store.js';
import { ChatService } from './chat.js';
import { dmWire, mountChat } from './chat-routes.js';

export interface SocialOptions {
	/** Directory holding accounts.json, social.json, and the avatar files. */
	dataDir: string;
	/** Absolute origin used in avatar URLs; leave empty to return relative URLs. */
	publicBaseUrl?: string;
}

const wrap =
	(handler: (req: express.Request, res: express.Response) => Promise<void>) =>
	(req: express.Request, res: express.Response, next: express.NextFunction) => {
		handler(req, res).catch(next);
	};

const body = (req: express.Request): Record<string, unknown> =>
	req.body && typeof req.body === 'object' ? (req.body as Record<string, unknown>) : {};

const str = (value: unknown): string => (typeof value === 'string' ? value : '');

export const createSocialRouter = (service: SocialService, store: Store): express.Router => {
	const router = express.Router();
	const chat = service.chat ??= new ChatService(store, service);
	router.use((_req, _res, next) => { try { store.assertHealthy(); next(); } catch (error) { next(error); } });

	const isApiRequest = (path: string) =>
		path.startsWith('/api/v2/account') || path.startsWith('/api/v2/social') || path.startsWith('/avatars');

	// The launcher webview is a different origin, so only the account routes need CORS.
	router.use((req, res, next) => {
		if (isApiRequest(req.path)) {
			res.setHeader('Access-Control-Allow-Origin', '*');
			res.setHeader('Access-Control-Allow-Headers', 'authorization, content-type, x-chat-helper');
			res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
			if (req.method === 'OPTIONS') {
				res.status(204).end();
				return;
			}
		}
		next();
	});
	// Uploads ride in base64 JSON, so every media route skips the small parser and reads
	// its body only after authentication. Limits stay above the decoded caps: 16 MB
	// headers and 32 MB clips are roughly 22 and 43 MB once base64 encoded.
	const mediaRoutes = new Set([
		'/api/v2/account/avatar',
		'/api/v2/account/header',
		'/api/v2/social/posts'
	]);
	const jsonMedia = express.json({ limit: '48mb' });
	router.use((req, res, next) => {
		if (mediaRoutes.has(req.path) || req.path === '/api/v2/social/chat/attachments') {
			next();
			return;
		}
		express.json({ limit: '1mb' })(req, res, next);
	});

	const requireAuth: express.RequestHandler = (req, res, next) => {
		const header = req.get('authorization') ?? '';
		const token = header.toLowerCase().startsWith('bearer ') ? header.slice(7).trim() : '';
		service
			.authenticate(token)
			.then(account => {
				if (!account) {
					res.status(401).json({ error: 'unauthorized', message: 'Sign in to continue.' });
					return;
				}
				res.locals.account = account;
				res.locals.token = token;
				next();
			})
			.catch(next);
	};

	// ---- accounts -------------------------------------------------------
	mountChat(router, chat, requireAuth);

	router.post(
		'/api/v2/account/register',
		wrap(async (req, res) => {
			const payload = body(req);
			const result = await service.register(str(payload.username), str(payload.password), str(payload.displayName));
			res.status(201).json(result);
		})
	);

	router.post(
		'/api/v2/account/login',
		wrap(async (req, res) => {
			const payload = body(req);
			res.json(await service.login(str(payload.username), str(payload.password), req.ip ?? 'unknown'));
		})
	);

	router.post(
		'/api/v2/account/logout',
		requireAuth,
		wrap(async (_req, res) => {
			await service.logout(String(res.locals.token));
			res.json({ ok: true });
		})
	);

	router.get(
		'/api/v2/account/me',
		requireAuth,
		wrap(async (_req, res) => {
			res.json({ account: await service.updateProfile(res.locals.account, {}) });
		})
	);

	router.post(
		'/api/v2/account/profile',
		requireAuth,
		wrap(async (req, res) => {
			res.json({ account: await service.updateProfile(res.locals.account, body(req)) });
		})
	);

	router.put(
		'/api/v2/account/avatar',
		requireAuth,
		jsonMedia,
		wrap(async (req, res) => {
			const payload = body(req);
			res.json({ account: await service.setAvatar(res.locals.account, str(payload.dataBase64), str(payload.mimeType)) });
		})
	);

	router.delete(
		'/api/v2/account/avatar',
		requireAuth,
		wrap(async (_req, res) => {
			res.json({ account: await service.clearAvatar(res.locals.account) });
		})
	);

	const serveUpload = (dir: string, pattern: RegExp, maxAge: number) =>
		wrap(async (req, res) => {
			const file = path.basename(req.params.file ?? '');
			if (!pattern.test(file)) {
				res.status(404).end();
				return;
			}
			res.setHeader('Cache-Control', `public, max-age=${maxAge}`);
			res.sendFile(path.join(dir, file), error => {
				if (error) res.status(404).end();
			});
		});

	router.get('/avatars/:file', serveUpload(store.avatarsDir, /^\d+\.(png|jpg|webp|gif)$/, 300));
	router.get('/headers/:file', serveUpload(store.headersDir, /^\d+\.(png|jpg|webp|gif)$/, 60));
	router.get('/media/:file', serveUpload(store.mediaDir, /^\d+\.(png|jpg|webp|gif|mp4|webm)$/, 600));

	// ---- social graph ---------------------------------------------------

	router.get(
		'/api/v2/social/feed',
		requireAuth,
		wrap(async (_req, res) => {
			res.json(await service.feed(res.locals.account));
		})
	);

	router.post(
		'/api/v2/social/heartbeat',
		requireAuth,
		wrap(async (req, res) => {
			const payload = body(req);
			if (payload.presence !== undefined || payload.statusMessage !== undefined)
				await service.updateProfile(res.locals.account, payload);
			res.json(await service.feed(res.locals.account));
		})
	);

	router.get(
		'/api/v2/social/discover',
		requireAuth,
		wrap(async (req, res) => {
			const query = typeof req.query.q === 'string' ? req.query.q : '';
			res.json({ players: await service.discover(res.locals.account, query) });
		})
	);

	router.post(
		'/api/v2/social/friends',
		requireAuth,
		wrap(async (req, res) => {
			res.json(await service.requestFriend(res.locals.account, str(body(req).username)));
		})
	);

	router.post(
		'/api/v2/social/friends/accept',
		requireAuth,
		wrap(async (req, res) => {
			res.json(await service.acceptFriend(res.locals.account, str(body(req).username)));
		})
	);

	router.delete(
		'/api/v2/social/friends/:username',
		requireAuth,
		wrap(async (req, res) => {
			res.json(await service.removeFriend(res.locals.account, req.params.username ?? ''));
		})
	);

	router.get(
		'/api/v2/social/messages',
		requireAuth,
		wrap(async (req, res) => {
			const withPlayer = typeof req.query.with === 'string' ? req.query.with : '';
			const since = Number.parseInt(typeof req.query.since === 'string' ? req.query.since : '0', 10) || 0;
			const before = req.query.before === undefined ? Infinity : Number(req.query.before);
			const messages = await service.messagesWith(res.locals.account, withPlayer, since, before);
			res.json({
				messages: messages.map(message => ({
					attachments: chat.attachments(message.attachments),
					id: message.id,
					from: service.accountFor(message.from)?.username ?? '',
					to: service.accountFor(message.to)?.username ?? '',
					body: message.body,
					createdAt: new Date(message.createdAt).toISOString(),
					read: message.readAt !== null
				}))
			});
		})
	);

	router.post(
		'/api/v2/social/messages',
		requireAuth,
		wrap(async (req, res) => {
			const payload = body(req);
			const message = await service.sendMessage(res.locals.account, str(payload.to), str(payload.body), payload.attachments, str(payload.requestId));
			res.status(201).json({
				message: {
					attachments: chat.attachments(message.attachments),
					id: message.id,
					from: service.accountFor(message.from)?.username ?? '',
					to: service.accountFor(message.to)?.username ?? '',
					body: message.body,
					createdAt: new Date(message.createdAt).toISOString(),
					read: false
				}
			});
		})
	);

	router.put(
		'/api/v2/account/header',
		requireAuth,
		jsonMedia,
		wrap(async (req, res) => {
			const payload = body(req);
			res.json({ account: await service.setHeader(res.locals.account, str(payload.dataBase64), str(payload.mimeType)) });
		})
	);

	router.delete(
		'/api/v2/account/header',
		requireAuth,
		wrap(async (_req, res) => {
			res.json({ account: await service.clearHeader(res.locals.account) });
		})
	);

	router.get(
		'/api/v2/social/profiles/:username',
		requireAuth,
		wrap(async (req, res) => {
			const profile = await service.profileFor(res.locals.account, req.params.username ?? '');
			if (!profile) {
				res.status(404).json({ error: 'unknown_player', message: 'No Esteria account with that name.' });
				return;
			}
			res.json({ profile });
		})
	);

	router.post(
		'/api/v2/social/friends/:username',
		requireAuth,
		wrap(async (req, res) => {
			res.json(await service.setFriendMeta(res.locals.account, req.params.username ?? '', body(req)));
		})
	);

	router.get(
		'/api/v2/social/groups',
		requireAuth,
		wrap(async (_req, res) => {
			res.json({ groups: service.myGroups(res.locals.account) });
		})
	);

	router.post(
		'/api/v2/social/groups',
		requireAuth,
		wrap(async (req, res) => {
			const payload = body(req);
			const members = Array.isArray(payload.members)
				? payload.members.filter((value): value is string => typeof value === 'string')
				: [];
			res.status(201).json({ group: await service.createGroup(res.locals.account, str(payload.name), members) });
		})
	);

	router.get(
		'/api/v2/social/groups/:id/messages',
		requireAuth,
		wrap(async (req, res) => {
			const since = Number.parseInt(typeof req.query.since === 'string' ? req.query.since : '0', 10) || 0;
			const id = Number.parseInt(req.params.id ?? '0', 10) || 0;
			res.json({ messages: await service.groupMessages(res.locals.account, id, since, req.query.before === undefined ? Infinity : Number(req.query.before)) });
		})
	);

	router.post(
		'/api/v2/social/groups/:id/messages',
		requireAuth,
		wrap(async (req, res) => {
			const id = Number.parseInt(req.params.id ?? '0', 10) || 0;
			const payload = body(req);
			const message = await service.sendGroupMessage(res.locals.account, id, str(payload.body), payload.attachments, str(payload.requestId));
			res.status(201).json({ message });
		})
	);

	router.delete(
		'/api/v2/social/groups/:id',
		requireAuth,
		wrap(async (req, res) => {
			await service.leaveGroup(res.locals.account, Number.parseInt(req.params.id ?? '0', 10) || 0);
			res.json({ ok: true });
		})
	);

	router.get(
		'/api/v2/social/posts',
		requireAuth,
		wrap(async (req, res) => {
			const since = Number.parseInt(typeof req.query.since === 'string' ? req.query.since : '0', 10) || 0;
			res.json({ posts: await service.feedPosts(res.locals.account, since) });
		})
	);

	router.post(
		'/api/v2/social/posts',
		requireAuth,
		jsonMedia,
		wrap(async (req, res) => {
			const payload = body(req);
			const encoded = str(payload.dataBase64);
			let media: { data: Buffer; ext: MediaExt; kind: MediaKind } | null = null;
			if (encoded) {
				const declared = str(payload.mimeType).toLowerCase();
				const allowed = mediaTypes[declared];
				if (!allowed) throw new ApiError(415, 'unsupported_media', 'Posts accept PNG, JPEG, WebP, GIF, MP4, or WebM files.');
				const data = Buffer.from(encoded, 'base64');
				if (!data.length) throw new ApiError(400, 'empty_media', 'That file could not be read.');
				if (data.length > allowed.limit)
					throw new ApiError(413, 'media_too_large', `That file must be ${Math.round(allowed.limit / (1024 * 1024))} MB or smaller.`);
				const sniffed = sniffMediaType(data, declared);
				if (!sniffed || sniffed.kind !== allowed.kind)
					throw new ApiError(415, 'invalid_media', 'That file is not a valid image or video.');
				media = { data, ext: sniffed.ext, kind: sniffed.kind };
			}
			res.status(201).json({ post: await service.createPost(res.locals.account, str(payload.body), media) });
		})
	);

	router.delete(
		'/api/v2/social/posts/:id',
		requireAuth,
		wrap(async (req, res) => {
			await service.deletePost(res.locals.account, Number.parseInt(req.params.id ?? '0', 10) || 0);
			res.json({ ok: true });
		})
	);

	router.use((error: unknown, _req: express.Request, res: express.Response, _next: express.NextFunction) => {
		if (error instanceof ApiError) {
			res.status(error.status).json({ error: error.code, message: error.message });
			return;
		}
		if (typeof error === 'object' && error && (error as { type?: string }).type === 'entity.too.large') {
			res.status(413).json({
				error: 'payload_too_large',
				message: 'That upload is too large for this endpoint.'
			});
			return;
		}
		console.error('Social API processing failed; check storage permissions and decoder health.');
		res.status(500).json({ error: 'social_api_error', message: 'The social service hit an unexpected error.' });
	});

	return router;
};

/** Loads the store and mounts the social API on an existing express app. */
export const attachSocial = async (app: express.Express, options: SocialOptions): Promise<SocialService> => {
	const store = new Store(options.dataDir);
	await store.load();
	const service = new SocialService(store, options.publicBaseUrl ?? '');
	service.chat = new ChatService(store, service);
	await service.chat.start();
	app.use(createSocialRouter(service, store));
	return service;
};

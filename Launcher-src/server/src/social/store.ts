import { randomBytes, scryptSync, timingSafeEqual } from 'node:crypto';
import fs from 'node:fs/promises';
import path from 'node:path';
import { DatabaseSync } from 'node:sqlite';
import type { ChatState } from './chat.js';

export type Presence = 'online' | 'away' | 'dnd' | 'offline';
export type ImageExt = 'png' | 'jpg' | 'webp' | 'gif';
export type MediaExt = ImageExt | 'mp4' | 'webm';
export type MediaKind = 'image' | 'video';

export interface Avatar {
	ext: ImageExt;
	version: number;
}

export interface Account {
	shareCharacterPresence?: boolean;
	id: number;
	username: string;
	displayName: string;
	createdAt: number;
	passwordSalt: string;
	passwordHash: string;
	statusMessage: string;
	bio: string;
	presence: Presence;
	avatar: Avatar | null;
	header: Avatar | null;
	gameAccount: string | null;
}

export interface SessionRecord {
	token: string;
	accountId: number;
	createdAt: number;
	expiresAt: number;
}

export interface FriendLink {
	a: number;
	b: number;
	note: string;
	favorite: boolean;
	createdAt: number;
}

export interface FriendRequest {
	from: number;
	to: number;
	createdAt: number;
}

export interface ChatMessage {
	attachments?: string[];
	requestId?: string;
	id: number;
	from: number;
	to: number;
	body: string;
	createdAt: number;
	readAt: number | null;
}

export interface Group {
	id: number;
	name: string;
	ownerId: number;
	members: number[];
	createdAt: number;
}

export interface GroupMessage {
	attachments?: string[];
	requestId?: string;
	id: number;
	groupId: number;
	from: number;
	body: string;
	createdAt: number;
}

export interface Post {
	id: number;
	authorId: number;
	body: string;
	mediaKind: MediaKind | null;
	mediaExt: MediaExt | null;
	createdAt: number;
}

export interface AccountsFile {
	schemaVersion: 1;
	accounts: Account[];
	sessions: SessionRecord[];
}

export interface SocialFile {
	chat?: ChatState;
	schemaVersion: 1;
	friends: FriendLink[];
	requests: FriendRequest[];
	messages: ChatMessage[];
	groups: Group[];
	groupMessages: GroupMessage[];
	posts: Post[];
	nextMessageId: number;
	nextGroupId: number;
	nextGroupMessageId: number;
	nextPostId: number;
}

export const emptyAccounts = (): AccountsFile => ({ schemaVersion: 1, accounts: [], sessions: [] });
export const emptySocial = (): SocialFile => ({
	schemaVersion: 1,
	friends: [],
	requests: [],
	messages: [],
	groups: [],
	groupMessages: [],
	posts: [],
	nextMessageId: 1,
	nextGroupId: 1,
	nextGroupMessageId: 1,
	nextPostId: 1
});

const readJson = async <T>(file: string, fallback: T): Promise<T> => {
	try {
		return JSON.parse(await fs.readFile(file, 'utf8')) as T;
	} catch (error) {
		if ((error as NodeJS.ErrnoException).code === 'ENOENT') return fallback;
		throw error;
	}
};

const writeJson = async (file: string, value: unknown): Promise<void> => {
	await fs.mkdir(path.dirname(file), { recursive: true });
	const tmp = `${file}.tmp`;
	await fs.writeFile(tmp, `${JSON.stringify(value, null, '\t')}\n`, 'utf8');
	await fs.rename(tmp, file);
};

export const hashPassword = (password: string): { salt: string; hash: string } => {
	const salt = randomBytes(16).toString('hex');
	return { salt, hash: scryptSync(password, salt, 64).toString('hex') };
};

export const verifyPassword = (password: string, salt: string, hash: string): boolean => {
	const expected = Buffer.from(hash, 'hex');
	const candidate = scryptSync(password, salt, 64);
	return expected.length === candidate.length && timingSafeEqual(expected, candidate);
};

export const newToken = (): string => randomBytes(32).toString('base64url');

export const avatarExtensions: Record<string, ImageExt> = {
	'image/png': 'png',
	'image/jpeg': 'jpg',
	'image/webp': 'webp',
	'image/gif': 'gif'
};

/** Media accepted for community posts. */
export const mediaTypes: Record<string, { ext: MediaExt; kind: MediaKind; limit: number }> = {
	'image/png': { ext: 'png', kind: 'image', limit: 8 * 1024 * 1024 },
	'image/jpeg': { ext: 'jpg', kind: 'image', limit: 8 * 1024 * 1024 },
	'image/webp': { ext: 'webp', kind: 'image', limit: 8 * 1024 * 1024 },
	'image/gif': { ext: 'gif', kind: 'image', limit: 8 * 1024 * 1024 },
	'video/mp4': { ext: 'mp4', kind: 'video', limit: 32 * 1024 * 1024 },
	'video/webm': { ext: 'webm', kind: 'video', limit: 32 * 1024 * 1024 }
};

// Magic-byte sniff so a renamed .exe cannot land in an image directory.
export const sniffImageType = (bytes: Buffer): ImageExt | null => {
	if (bytes.length > 8 && bytes.subarray(0, 8).equals(Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a])))
		return 'png';
	if (bytes.length > 3 && bytes[0] === 0xff && bytes[1] === 0xd8 && bytes[2] === 0xff) return 'jpg';
	if (
		bytes.length > 12 &&
		bytes.subarray(0, 4).toString('ascii') === 'RIFF' &&
		bytes.subarray(8, 12).toString('ascii') === 'WEBP'
	)
		return 'webp';
	const head = bytes.subarray(0, 6).toString('ascii');
	if (head === 'GIF87a' || head === 'GIF89a') return 'gif';
	return null;
};

/** Container sniff for post media: images by magic bytes, video by ftyp/webm boxes. */
export const sniffMediaType = (bytes: Buffer, declared: string): { ext: MediaExt; kind: MediaKind } | null => {
	const image = sniffImageType(bytes);
	if (image) return { ext: image, kind: 'image' };
	if (bytes.length > 12 && bytes.subarray(4, 8).toString('ascii') === 'ftyp') {
		const brand = bytes.subarray(8, 12).toString('ascii');
		return brand === 'qt  ' ? null : { ext: 'mp4', kind: 'video' };
	}
	if (bytes.length > 4 && bytes.subarray(0, 4).equals(Buffer.from([0x1a, 0x45, 0xdf, 0xa3]))) {
		return { ext: 'webm', kind: 'video' };
	}
	const fallback = mediaTypes[declared.toLowerCase()];
	return fallback ? { ext: fallback.ext, kind: fallback.kind } : null;
};

/**
 * Transactional SQLite snapshots; legacy JSON is imported once and left intact.
 */
export class Store {
	readonly accountsPath: string;
	readonly socialPath: string;
	readonly avatarsDir: string;
	readonly headersDir: string;
	readonly mediaDir: string;
	accountData: AccountsFile = emptyAccounts();
	socialData: SocialFile = emptySocial();
	private database?: DatabaseSync;
	private revision = 0;
	private failed = false;

	constructor(readonly dataDir: string) {
		this.accountsPath = path.join(dataDir, 'accounts.json');
		this.socialPath = path.join(dataDir, 'social.json');
		this.avatarsDir = path.join(dataDir, 'avatars');
		this.headersDir = path.join(dataDir, 'headers');
		this.mediaDir = path.join(dataDir, 'media');
	}

	async load(): Promise<void> {
		try {
		await fs.mkdir(this.dataDir, { recursive: true });
		this.database = new DatabaseSync(path.join(this.dataDir, 'social.sqlite'));
		this.database.exec('PRAGMA journal_mode=WAL; PRAGMA synchronous=FULL; CREATE TABLE IF NOT EXISTS state (id INTEGER PRIMARY KEY CHECK(id=1), revision INTEGER NOT NULL, accounts TEXT NOT NULL, social TEXT NOT NULL)');
		const row = this.database.prepare('SELECT * FROM state WHERE id=1').get();
		this.revision = Number(row?.revision ?? 0);
		const accounts = row ? JSON.parse(String(row.accounts)) as AccountsFile : await readJson<AccountsFile>(this.accountsPath, emptyAccounts());
		if (accounts.schemaVersion !== 1 || !Array.isArray(accounts.accounts) || !Array.isArray(accounts.sessions))
			throw new Error('Unsupported or corrupt accounts.json; restore a valid backup before migration.');
		this.accountData = {
			schemaVersion: 1,
			accounts: (Array.isArray(accounts.accounts) ? accounts.accounts : []).map(account => ({
				...account,
				bio: typeof account.bio === 'string' ? account.bio : '',
				header: account.header ?? null
			})),
			sessions: Array.isArray(accounts.sessions) ? accounts.sessions : []
		};
		const social = row ? JSON.parse(String(row.social)) as SocialFile : await readJson<SocialFile>(this.socialPath, emptySocial());
		if (social.schemaVersion !== 1 || !['friends', 'requests', 'messages', 'groups', 'groupMessages', 'posts'].every(key => Array.isArray((social as unknown as Record<string, unknown>)[key])))
			throw new Error('Unsupported or corrupt social.json; restore a valid backup before migration.');
		const integer = (value: unknown, fallback: number) => (Number.isInteger(value) ? (value as number) : fallback);
		this.socialData = {
			chat: social.chat,
			schemaVersion: 1,
			friends: (Array.isArray(social.friends) ? social.friends : []).map(link => ({
				...link,
				note: typeof link.note === 'string' ? link.note : '',
				favorite: link.favorite === true
			})),
			requests: Array.isArray(social.requests) ? social.requests : [],
			messages: Array.isArray(social.messages) ? social.messages : [],
			groups: Array.isArray(social.groups) ? social.groups : [],
			groupMessages: Array.isArray(social.groupMessages) ? social.groupMessages : [],
			posts: Array.isArray(social.posts) ? social.posts : [],
			nextMessageId: integer(social.nextMessageId, 1),
			nextGroupId: integer(social.nextGroupId, 1),
			nextGroupMessageId: integer(social.nextGroupMessageId, 1),
			nextPostId: integer(social.nextPostId, 1)
		};
		await fs.mkdir(this.avatarsDir, { recursive: true });
		await fs.mkdir(this.headersDir, { recursive: true });
		await fs.mkdir(this.mediaDir, { recursive: true });
		if (!row) {
			this.database.prepare('INSERT INTO state VALUES (1, 0, ?, ?)').run(JSON.stringify(this.accountData), JSON.stringify(this.socialData));
		}
		} catch (error) { this.close(); throw error; }
	}

	saveAccounts(): Promise<void> {
		return this.save();
	}

	saveSocial(): Promise<void> {
		return this.save();
	}

	// shortcut: bounded single-process snapshot storage; normalize tables before large message histories.
	private async save(): Promise<void> {
		this.assertHealthy();
		if (!this.database) throw new Error('Store is not loaded.');
		try {
			const result = this.database.prepare('UPDATE state SET revision=revision+1, accounts=?, social=? WHERE id=1 AND revision=?')
				.run(JSON.stringify(this.accountData), JSON.stringify(this.socialData), this.revision);
			if (result.changes !== 1) throw new Error('Concurrent social service writer detected; stop the second process and restart.');
			this.revision++;
		} catch (error) { this.failed = true; throw error; }
	}

	assertHealthy(): void { if (this.failed) throw new Error('Social persistence failed; restart after fixing storage.'); }

	close(): void { if (this.database?.isOpen) this.database.close(); }

	async exportLegacy(): Promise<void> {
		const accounts = structuredClone(this.accountData), social = structuredClone(this.socialData);
		await writeJson(this.accountsPath, accounts);
		await writeJson(this.socialPath, social);
	}

	avatarPath(id: number, ext: ImageExt): string {
		return path.join(this.avatarsDir, `${id}.${ext}`);
	}

	headerPath(id: number, ext: ImageExt): string {
		return path.join(this.headersDir, `${id}.${ext}`);
	}

	mediaPath(id: number, ext: MediaExt): string {
		return path.join(this.mediaDir, `${id}.${ext}`);
	}
}

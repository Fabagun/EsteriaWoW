import fs from 'node:fs/promises';
import type { ChatService } from './chat.js';

import { avatarExtensions, hashPassword, newToken, sniffImageType, verifyPassword } from './store.js';
import type {
	Account,
	ChatMessage,
	Group,
	GroupMessage,
	ImageExt,
	MediaExt,
	MediaKind,
	Post,
	Presence,
	Store
} from './store.js';

export class ApiError extends Error {
	constructor(readonly status: number, readonly code: string, message: string) {
		super(message);
	}
}

export interface WireAccount {
	shareCharacterPresence?: boolean;
	gamePresence?: { characterName: string; realmId: string; serverId: string };
	username: string;
	displayName: string;
	statusMessage: string;
	bio: string;
	presence: Presence;
	explicitPresence: Presence;
	avatarUrl: string | null;
	headerUrl: string | null;
	createdAt: string;
	lastSeen: string | null;
	gameAccount?: string | null;
}

export interface FriendWire extends WireAccount {
	note: string;
	favorite: boolean;
	unread: number;
	since: string;
}

export interface GroupWire {
	unread?: number;
	id: number;
	name: string;
	owner: string;
	members: string[];
	createdAt: string;
}

export interface GroupMessageWire {
	attachments?: unknown[];
	id: number;
	groupId: number;
	from: string;
	body: string;
	createdAt: string;
}

export interface PostWire {
	id: number;
	author: WireAccount;
	body: string;
	mediaKind: MediaKind | null;
	mediaUrl: string | null;
	createdAt: string;
}

export interface Feed {
	me: WireAccount;
	friends: FriendWire[];
	incoming: WireAccount[];
	outgoing: string[];
	unread: number;
	serverTime: string;
}

const SESSION_TTL_MS = 30 * 24 * 60 * 60 * 1000;
const ONLINE_TTL_MS = 70_000;
const AWAY_TTL_MS = 5 * 60 * 1000;
const MAX_AVATAR_BYTES = 8 * 1024 * 1024;
const MAX_HEADER_BYTES = 16 * 1024 * 1024;
const MESSAGE_LIMIT = 200;
const USERNAME_PATTERN = /^[A-Za-z0-9][A-Za-z0-9_.-]{2,19}$/;

const asPresence = (value: unknown): Presence | null =>
	value === 'online' || value === 'away' || value === 'dnd' || value === 'offline' ? value : null;

const text = (value: unknown, max: number): string => (typeof value === 'string' ? value.trim().slice(0, max) : '');

export class SocialService {
	chat?: ChatService;
	private readonly lastSeen = new Map<number, number>();
	private readonly failedLogins = new Map<string, { count: number; until: number }>();

	constructor(private readonly store: Store, private readonly publicBaseUrl = '') {}

	// ---- accounts -------------------------------------------------------

	async register(username: string, password: string, displayName: string): Promise<{ account: WireAccount; token: string }> {
		const clean = username.trim();
		if (!USERNAME_PATTERN.test(clean))
			throw new ApiError(400, 'invalid_username', 'Account names must be 3-20 characters: letters, numbers, dot, dash, underscore.');
		if (password.length < 6 || password.length > 128)
			throw new ApiError(400, 'invalid_password', 'Passwords must be at least 6 characters.');
		if (this.findByUsername(clean)) throw new ApiError(409, 'username_taken', 'That account name is already taken.');

		const { salt, hash } = hashPassword(password);
		const account: Account = {
			id: this.store.accountData.accounts.reduce((max, entry) => Math.max(max, entry.id), 0) + 1,
			username: clean.toLowerCase(),
			displayName: text(displayName, 32) || clean,
			createdAt: Date.now(),
			passwordSalt: salt,
			passwordHash: hash,
			statusMessage: '',
			bio: '',
			presence: 'online',
			avatar: null,
			header: null,
			gameAccount: null
		};
		this.store.accountData.accounts.push(account);
		await this.store.saveAccounts();
		this.lastSeen.set(account.id, Date.now());
		const token = await this.createSession(account);
		return { account: this.wire(account, true), token };
	}

	async login(username: string, password: string, clientKey = 'unknown'): Promise<{ account: WireAccount; token: string }> {
		const gate = this.failedLogins.get(clientKey);
		if (gate && gate.count >= 8 && gate.until > Date.now())
			throw new ApiError(429, 'rate_limited', 'Too many failed sign-in attempts. Wait a few minutes and try again.');

		const account = this.findByUsername(username.trim());
		if (!account || !verifyPassword(password, account.passwordSalt, account.passwordHash)) {
			const next = { count: (gate?.count ?? 0) + 1, until: Date.now() + 5 * 60 * 1000 };
			this.failedLogins.set(clientKey, next);
			throw new ApiError(401, 'invalid_credentials', 'Account name or password is incorrect.');
		}
		this.failedLogins.delete(clientKey);
		this.lastSeen.set(account.id, Date.now());
		const token = await this.createSession(account);
		return { account: this.wire(account, true), token };
	}

	async logout(token: string): Promise<void> {
		this.chat?.endSession(`launcher:${token}`);
		const sessions = this.store.accountData.sessions;
		const index = sessions.findIndex(session => session.token === token);
		if (index >= 0) {
			sessions.splice(index, 1);
			await this.store.saveAccounts();
		}
	}

	async authenticate(token: string | null): Promise<Account | null> {
		if (!token) return null;
		const session = this.store.accountData.sessions.find(entry => entry.token === token);
		if (!session) return null;
		if (session.expiresAt <= Date.now()) {
			await this.logout(token);
			return null;
		}
		const account = this.store.accountData.accounts.find(entry => entry.id === session.accountId) ?? null;
		if (account) {
			this.lastSeen.set(account.id, Date.now());
			this.chat?.touch(account, `launcher:${token}`);
		}
		return account;
	}

	async updateProfile(
		account: Account,
		patch: { displayName?: unknown; statusMessage?: unknown; presence?: unknown; bio?: unknown; shareCharacterPresence?: unknown }
	): Promise<WireAccount> {
		let changed = false;
		if (patch.shareCharacterPresence !== undefined) {
			const share = patch.shareCharacterPresence === true && this.chat?.config.features.characterPresence === true;
			changed = changed || account.shareCharacterPresence !== share;
			account.shareCharacterPresence = share;
		}
		if (patch.displayName !== undefined) {
			const displayName = text(patch.displayName, 32);
			if (!displayName) throw new ApiError(400, 'invalid_display_name', 'Display name cannot be empty.');
			changed = changed || displayName !== account.displayName;
			account.displayName = displayName;
		}
		if (patch.statusMessage !== undefined) {
			const statusMessage = text(patch.statusMessage, 120);
			changed = changed || statusMessage !== account.statusMessage;
			account.statusMessage = statusMessage;
		}
		if (patch.bio !== undefined) {
			const bio = text(patch.bio, 400);
			changed = changed || bio !== account.bio;
			account.bio = bio;
		}
		if (patch.presence !== undefined) {
			const presence = asPresence(patch.presence);
			if (!presence) throw new ApiError(400, 'invalid_presence', 'Presence must be online, away, dnd, or offline.');
			changed = changed || presence !== account.presence;
			account.presence = presence;
		}
		this.lastSeen.set(account.id, Date.now());
		// Heartbeats repeat unchanged values; only touch the file when something moved.
		if (changed) await this.store.saveAccounts();
		return this.wire(account, true);
	}

	async setAvatar(account: Account, base64: string, mimeType: string): Promise<WireAccount> {
		const image = this.decodeImage(base64, mimeType, MAX_AVATAR_BYTES, 'Profile pictures');
		const previous = account.avatar;
		await fs.writeFile(this.store.avatarPath(account.id, image.ext), image.data);
		if (previous && previous.ext !== image.ext) {
			await fs.rm(this.store.avatarPath(account.id, previous.ext), { force: true });
		}
		account.avatar = { ext: image.ext, version: (previous?.version ?? 0) + 1 };
		await this.store.saveAccounts();
		return this.wire(account, true);
	}

	async clearAvatar(account: Account): Promise<WireAccount> {
		if (account.avatar) {
			await fs.rm(this.store.avatarPath(account.id, account.avatar.ext), { force: true });
			account.avatar = null;
			await this.store.saveAccounts();
		}
		return this.wire(account, true);
	}

	// ---- social graph ---------------------------------------------------

	async feed(account: Account): Promise<Feed> {
		this.lastSeen.set(account.id, Date.now());
		const friends = this.store.socialData.friends
			.filter(link => link.a === account.id || link.b === account.id)
			.map(link => (link.a === account.id ? link.b : link.a))
			.map(id => this.store.accountData.accounts.find(entry => entry.id === id))
			.filter((entry): entry is Account => Boolean(entry))
			.map(entry => {
				const link = this.linkBetween(account.id, entry.id);
				return {
					...this.wire(entry),
					note: link?.note ?? '',
					favorite: link?.favorite === true,
					unread: this.unreadFrom(account.id, entry.id),
					since: new Date(entry.createdAt).toISOString()
				};
			})
			.sort((left, right) => {
				const rank = (value: WireAccount) => (value.presence === 'offline' ? 1 : 0);
				return rank(left) - rank(right) || left.displayName.localeCompare(right.displayName);
			});
		const incoming = this.store.socialData.requests
			.filter(request => request.to === account.id)
			.map(request => this.store.accountData.accounts.find(entry => entry.id === request.from))
			.filter((entry): entry is Account => Boolean(entry))
			.map(entry => this.wire(entry));
		const outgoing = this.store.socialData.requests
			.filter(request => request.from === account.id)
			.map(request => this.store.accountData.accounts.find(entry => entry.id === request.to)?.username)
			.filter((value): value is string => Boolean(value));
		return {
			me: this.wire(account, true),
			friends,
			incoming,
			outgoing,
			unread: friends.reduce((total, friend) => total + friend.unread, 0),
			serverTime: new Date().toISOString()
		};
	}

	async discover(account: Account, query: string): Promise<Array<WireAccount & { relation: string }>> {
		const needle = query.trim().toLowerCase();
		return this.store.accountData.accounts
			.filter(entry => entry.id !== account.id)
			.filter(entry => !needle || entry.username.includes(needle) || entry.displayName.toLowerCase().includes(needle))
			.sort((left, right) => left.displayName.localeCompare(right.displayName))
			.slice(0, 25)
			.map(entry => ({ ...this.wire(entry), relation: this.relation(account.id, entry.id) }));
	}

	async requestFriend(account: Account, username: string): Promise<Feed> {
		if (this.chat && !this.chat.config.features.friends) throw new ApiError(403, 'disabled', 'Friends are disabled.');
		const target = this.findByUsername(username);
		if (!target) throw new ApiError(404, 'unknown_player', 'No Esteria account with that name.');
		if (target.id === account.id) throw new ApiError(400, 'self_friend', 'You cannot add yourself.');
		if (this.chat?.blocked(account.id, target.id)) throw new ApiError(403, 'blocked', 'Player unavailable.');
		if (this.relation(account.id, target.id) === 'friend') throw new ApiError(409, 'already_friends', `${target.displayName} is already a friend.`);
		if (this.store.socialData.requests.some(request => request.from === target.id && request.to === account.id))
			return this.acceptFriend(account, target.username);
		if (!this.store.socialData.requests.some(request => request.from === account.id && request.to === target.id)) {
			this.store.socialData.requests.push({ from: account.id, to: target.id, createdAt: Date.now() });
			await this.store.saveSocial();
		}
		return this.feed(account);
	}

	async acceptFriend(account: Account, username: string): Promise<Feed> {
		if (this.chat && !this.chat.config.features.friends) throw new ApiError(403, 'disabled', 'Friends are disabled.');
		const target = this.findByUsername(username);
		if (!target) throw new ApiError(404, 'unknown_player', 'No Esteria account with that name.');
		const index = this.store.socialData.requests.findIndex(
			request => request.from === target.id && request.to === account.id
		);
		if (index < 0) throw new ApiError(404, 'no_request', 'That friend request no longer exists.');
		if (this.chat?.blocked(account.id, target.id)) throw new ApiError(403, 'blocked', 'Player unavailable.');
		this.store.socialData.requests.splice(index, 1);
		this.store.socialData.requests = this.store.socialData.requests.filter(
			request =>
				!(
					(request.from === account.id && request.to === target.id) ||
					(request.from === target.id && request.to === account.id)
				)
		);
		this.link(account.id, target.id);
		await this.store.saveSocial();
		return this.feed(account);
	}

	async removeFriend(account: Account, username: string): Promise<Feed> {
		const target = this.findByUsername(username);
		if (!target) throw new ApiError(404, 'unknown_player', 'No Esteria account with that name.');
		const low = Math.min(account.id, target.id);
		const high = Math.max(account.id, target.id);
		this.store.socialData.friends = this.store.socialData.friends.filter(link => !(link.a === low && link.b === high));
		this.store.socialData.requests = this.store.socialData.requests.filter(
			request =>
				!(
					(request.from === account.id && request.to === target.id) ||
					(request.from === target.id && request.to === account.id)
				)
		);
		await this.store.saveSocial();
		return this.feed(account);
	}

	// ---- chat -----------------------------------------------------------

	async messagesWith(account: Account, username: string, sinceId: number, beforeId = Infinity): Promise<ChatMessage[]> {
		this.chat?.conversation(account, `dm:${username}`);
		const target = this.findByUsername(username);
		if (!target) throw new ApiError(404, 'unknown_player', 'No Esteria account with that name.');
		if (this.relation(account.id, target.id) !== 'friend')
			throw new ApiError(403, 'not_friends', 'Messages are only available between friends.');
		const messages = this.store.socialData.messages
			.filter(
				message =>
					message.id > sinceId && message.id < beforeId &&
					((message.from === account.id && message.to === target.id) ||
						(message.from === target.id && message.to === account.id))
			)
			.slice(sinceId > 0 ? 0 : -MESSAGE_LIMIT, sinceId > 0 ? MESSAGE_LIMIT : undefined);
		return messages;
	}

	async sendMessage(account: Account, username: string, body: string, attachmentIds?: unknown, requestId = ''): Promise<ChatMessage> {
		const target = this.findByUsername(username);
		if (!target) throw new ApiError(404, 'unknown_player', 'No Esteria account with that name.');
		if (this.relation(account.id, target.id) !== 'friend')
			throw new ApiError(403, 'not_friends', 'You can only message friends.');
		this.chat?.conversation(account, `dm:${username}`);
		this.validateRequest(requestId);
		const previous = requestId && this.store.socialData.messages.find(m => m.from === account.id && m.requestId === requestId);
		if (previous) {
			if (previous.to !== target.id || previous.body !== text(body, 1000) || JSON.stringify(previous.attachments ?? []) !== JSON.stringify(attachmentIds ?? []))
				throw new ApiError(409, 'request_conflict', 'Request ID already used for different content.');
			return previous;
		}
		this.chat?.rate(`send:${account.id}`, 30);
		const attachments = this.chat?.prepare(account, `dm:${username}`, attachmentIds) ?? [];
		const clean = text(body, 1000);
		if (!clean && !attachments.length) throw new ApiError(400, 'empty_message', 'Enter a message or attach an image first.');
		const message: ChatMessage = {
			attachments, requestId,
			id: this.store.socialData.nextMessageId++,
			from: account.id,
			to: target.id,
			body: clean,
			createdAt: Date.now(),
			readAt: null
		};
		this.store.socialData.messages.push(message);
		this.chat?.associate(attachments);
		await this.store.saveSocial();
		return message;
	}

	// ---- profile header, bio, friend metadata ---------------------------

	async setHeader(account: Account, base64: string, mimeType: string): Promise<WireAccount> {
		const image = this.decodeImage(base64, mimeType, MAX_HEADER_BYTES, 'Profile headers');
		const previous = account.header;
		await fs.writeFile(this.store.headerPath(account.id, image.ext), image.data);
		if (previous && previous.ext !== image.ext)
			await fs.rm(this.store.headerPath(account.id, previous.ext), { force: true });
		account.header = { ext: image.ext, version: (previous?.version ?? 0) + 1 };
		await this.store.saveAccounts();
		return this.wire(account, true);
	}

	async clearHeader(account: Account): Promise<WireAccount> {
		if (account.header) {
			await fs.rm(this.store.headerPath(account.id, account.header.ext), { force: true });
			account.header = null;
			await this.store.saveAccounts();
		}
		return this.wire(account, true);
	}

	async profileFor(account: Account, username: string): Promise<(WireAccount & { relation: string; note: string; favorite: boolean }) | null> {
		const target = this.findByUsername(username);
		if (!target) return null;
		const link = this.linkBetween(account.id, target.id);
		return {
			...this.wire(target),
			relation: this.relation(account.id, target.id),
			note: link?.note ?? '',
			favorite: link?.favorite === true
		};
	}

	async setFriendMeta(account: Account, username: string, patch: { nickname?: unknown; favorite?: unknown }): Promise<Feed> {
		const target = this.findByUsername(username);
		if (!target) throw new ApiError(404, 'unknown_player', 'No Esteria account with that name.');
		const link = this.linkBetween(account.id, target.id);
		if (!link) throw new ApiError(403, 'not_friends', 'That player is not on your friends list.');
		if (patch.nickname !== undefined) link.note = text(patch.nickname, 32);
		if (patch.favorite !== undefined) link.favorite = patch.favorite === true;
		await this.store.saveSocial();
		return this.feed(account);
	}

	// ---- group chat -----------------------------------------------------

	async createGroup(account: Account, name: string, members: string[]): Promise<GroupWire> {
		if (this.chat && !this.chat.config.features.groups) throw new ApiError(403, 'disabled', 'Groups are disabled.');
		const ids = new Set<number>([account.id]);
		for (const username of members) {
			const friend = this.findByUsername(username);
			if (!friend || friend.id === account.id) continue;
			if (this.relation(account.id, friend.id) !== 'friend' || this.chat?.blocked(account.id, friend.id)) continue;
			ids.add(friend.id);
		}
		if (ids.size < 2) throw new ApiError(400, 'group_too_small', 'Choose at least one friend for the group.');
		if (ids.size > 20) throw new ApiError(400, 'group_too_large', 'Groups are limited to 20 members.');
		const group: Group = {
			id: this.store.socialData.nextGroupId++,
			name: text(name, 40) || 'New group',
			ownerId: account.id,
			members: [...ids],
			createdAt: Date.now()
		};
		this.store.socialData.groups.push(group);
		await this.store.saveSocial();
		return this.groupWire(group);
	}

	myGroups(account: Account): GroupWire[] {
		return this.store.socialData.groups
			.filter(group => group.members.includes(account.id))
			.sort((left, right) => left.createdAt - right.createdAt)
			.map(group => ({ ...this.groupWire(group), unread: this.chat?.groupUnread(account, group.id) ?? 0 }));
	}

	async groupMessages(account: Account, groupId: number, sinceId: number, beforeId = Infinity): Promise<GroupMessageWire[]> {
		this.chat?.conversation(account, `group:${groupId}`);
		const group = this.requireGroup(account, groupId);
		return this.store.socialData.groupMessages
			.filter(message => message.groupId === group.id && message.id > sinceId && message.id < beforeId && !this.chat?.blocked(account.id, message.from))
			.slice(sinceId > 0 ? 0 : -MESSAGE_LIMIT, sinceId > 0 ? MESSAGE_LIMIT : undefined)
			.map(message => this.groupMessageWire(message));
	}

	async sendGroupMessage(account: Account, groupId: number, body: string, attachmentIds?: unknown, requestId = ''): Promise<GroupMessageWire> {
		const group = this.requireGroup(account, groupId);
		this.chat?.conversation(account, `group:${groupId}`);
		if (group.members.some(id => this.chat?.blocked(account.id, id))) throw new ApiError(403, 'blocked', 'A group member has blocked this conversation.');
		this.validateRequest(requestId);
		const previous = requestId && this.store.socialData.groupMessages.find(m => m.from === account.id && m.requestId === requestId);
		if (previous) {
			if (previous.groupId !== groupId || previous.body !== text(body, 1000) || JSON.stringify(previous.attachments ?? []) !== JSON.stringify(attachmentIds ?? []))
				throw new ApiError(409, 'request_conflict', 'Request ID already used for different content.');
			return this.groupMessageWire(previous);
		}
		this.chat?.rate(`send:${account.id}`, 30);
		const attachments = this.chat?.prepare(account, `group:${groupId}`, attachmentIds) ?? [];
		const clean = text(body, 1000);
		if (!clean && !attachments.length) throw new ApiError(400, 'empty_message', 'Enter a message or attach an image first.');
		const message: GroupMessage = {
			attachments, requestId,
			id: this.store.socialData.nextGroupMessageId++,
			groupId: group.id,
			from: account.id,
			body: clean,
			createdAt: Date.now()
		};
		this.store.socialData.groupMessages.push(message);
		this.chat?.associate(attachments);
		await this.store.saveSocial();
		return this.groupMessageWire(message);
	}

	async leaveGroup(account: Account, groupId: number): Promise<void> {
		const group = this.requireGroup(account, groupId);
		group.members = group.members.filter(id => id !== account.id);
		if (!group.members.length)
			this.store.socialData.groups = this.store.socialData.groups.filter(entry => entry.id !== group.id);
		await this.store.saveSocial();
	}

	// ---- community posts ------------------------------------------------

	async feedPosts(account: Account, sinceId: number): Promise<PostWire[]> {
		const visible = new Set<number>([account.id]);
		for (const link of this.store.socialData.friends) {
			if (link.a === account.id) visible.add(link.b);
			if (link.b === account.id) visible.add(link.a);
		}
		return this.store.socialData.posts
			.filter(post => visible.has(post.authorId) && post.id > sinceId)
			.sort((left, right) => right.id - left.id)
			.slice(0, 60)
			.map(post => this.postWire(post));
	}

	async createPost(
		account: Account,
		body: string,
		media: { data: Buffer; ext: MediaExt; kind: MediaKind } | null
	): Promise<PostWire> {
		const clean = text(body, 2000);
		if (!clean && !media) throw new ApiError(400, 'empty_post', 'Write something or attach a file first.');
		const post: Post = {
			id: this.store.socialData.nextPostId++,
			authorId: account.id,
			body: clean,
			mediaKind: media?.kind ?? null,
			mediaExt: media?.ext ?? null,
			createdAt: Date.now()
		};
		if (media) await fs.writeFile(this.store.mediaPath(post.id, media.ext), media.data);
		this.store.socialData.posts.push(post);
		await this.store.saveSocial();
		return this.postWire(post);
	}

	async deletePost(account: Account, postId: number): Promise<void> {
		const post = this.store.socialData.posts.find(entry => entry.id === postId);
		if (!post) throw new ApiError(404, 'unknown_post', 'That post no longer exists.');
		if (post.authorId !== account.id) throw new ApiError(403, 'not_author', 'You can only delete your own posts.');
		this.store.socialData.posts = this.store.socialData.posts.filter(entry => entry.id !== postId);
		if (post.mediaExt) await fs.rm(this.store.mediaPath(post.id, post.mediaExt), { force: true });
		await this.store.saveSocial();
	}

	// ---- helpers --------------------------------------------------------

	private validateRequest(requestId: string): void {
		if (requestId && !/^[A-Za-z0-9_-]{8,80}$/.test(requestId)) throw new ApiError(400, 'invalid_request_id', 'Invalid request ID.');
	}

	async removeGroupMember(account: Account, groupId: number, username: string): Promise<void> {
		const group = this.requireGroup(account, groupId);
		const target = this.findByUsername(username);
		if (group.ownerId !== account.id || !target || target.id === account.id) throw new ApiError(403, 'not_owner', 'Only the owner can remove another member.');
		group.members = group.members.filter(id => id !== target.id);
		await this.store.saveSocial();
	}

	linkBetween(leftId: number, rightId: number) {
		const low = Math.min(leftId, rightId);
		const high = Math.max(leftId, rightId);
		return this.store.socialData.friends.find(link => link.a === low && link.b === high);
	}

	private decodeImage(base64: string, mimeType: string, limit: number, label: string): { ext: ImageExt; data: Buffer } {
		const declared = avatarExtensions[mimeType.toLowerCase()];
		if (!declared) throw new ApiError(415, 'unsupported_image', `${label} must be PNG, JPEG, WebP, or GIF.`);
		const data = Buffer.from(base64, 'base64');
		if (!data.length) throw new ApiError(400, 'empty_image', 'That image could not be read.');
		if (data.length > limit)
			throw new ApiError(413, 'image_too_large', `${label} must be ${Math.round(limit / (1024 * 1024))} MB or smaller.`);
		const sniffed = sniffImageType(data);
		if (!sniffed || sniffed !== declared)
			throw new ApiError(415, 'invalid_image', 'That file is not a valid image.');
		return { ext: sniffed, data };
	}

	private groupWire(group: Group): GroupWire {
		return {
			id: group.id,
			name: group.name,
			owner: this.accountFor(group.ownerId)?.username ?? '',
			members: group.members
				.map(id => this.accountFor(id)?.username ?? '')
				.filter(Boolean),
			createdAt: new Date(group.createdAt).toISOString()
		};
	}

	private groupMessageWire(message: GroupMessage): GroupMessageWire {
		return {
			attachments: this.chat?.attachments(message.attachments),
			id: message.id,
			groupId: message.groupId,
			from: this.accountFor(message.from)?.username ?? '',
			body: message.body,
			createdAt: new Date(message.createdAt).toISOString()
		};
	}

	private postWire(post: Post): PostWire {
		const author = this.accountFor(post.authorId);
		return {
			id: post.id,
			author: author ? this.wire(author) : this.wire({
				id: 0,
				username: 'unknown',
				displayName: 'Unknown',
				createdAt: 0,
				passwordSalt: '',
				passwordHash: '',
				statusMessage: '',
				bio: '',
				presence: 'offline',
				avatar: null,
				header: null,
				gameAccount: null
			}),
			body: post.body,
			mediaKind: post.mediaKind,
			mediaUrl: post.mediaExt ? `${this.publicBaseUrl}/media/${post.id}.${post.mediaExt}` : null,
			createdAt: new Date(post.createdAt).toISOString()
		};
	}

	private requireGroup(account: Account, groupId: number): Group {
		const group = this.store.socialData.groups.find(entry => entry.id === groupId);
		if (!group) throw new ApiError(404, 'unknown_group', 'That group no longer exists.');
		if (!group.members.includes(account.id)) throw new ApiError(403, 'not_a_member', 'You are not in that group.');
		return group;
	}

	findByUsername(username: string): Account | null {
		const needle = username.trim().toLowerCase();
		if (!needle) return null;
		return this.store.accountData.accounts.find(entry => entry.username === needle) ?? null;
	}

	accountFor(id: number): Account | null {
		return this.store.accountData.accounts.find(entry => entry.id === id) ?? null;
	}

	link(a: number, b: number): void {
		const low = Math.min(a, b);
		const high = Math.max(a, b);
		if (!this.store.socialData.friends.some(entry => entry.a === low && entry.b === high))
			this.store.socialData.friends.push({ a: low, b: high, note: '', favorite: false, createdAt: Date.now() });
	}

	private relation(viewerId: number, otherId: number): string {
		const low = Math.min(viewerId, otherId);
		const high = Math.max(viewerId, otherId);
		if (this.store.socialData.friends.some(entry => entry.a === low && entry.b === high)) return 'friend';
		if (this.store.socialData.requests.some(request => request.from === viewerId && request.to === otherId)) return 'requested';
		if (this.store.socialData.requests.some(request => request.from === otherId && request.to === viewerId)) return 'incoming';
		return 'none';
	}

	private unreadFrom(viewerId: number, fromId: number): number {
		return this.store.socialData.messages.filter(
			message => message.from === fromId && message.to === viewerId && message.readAt === null
		).length;
	}

	private effectivePresence(account: Account): Presence {
		if (account.presence === 'offline') return 'offline';
		const age = Date.now() - (this.chat ? this.chat.active(account) : this.lastSeen.get(account.id) ?? 0);
		if (age <= ONLINE_TTL_MS) return account.presence;
		if (age <= AWAY_TTL_MS) return 'away';
		return 'offline';
	}

	private wire(account: Account, self = false): WireAccount {
		return {
			gamePresence: this.chat?.presenceDetails(account),
			...(self ? { shareCharacterPresence: account.shareCharacterPresence === true } : {}),
			username: account.username,
			displayName: account.displayName,
			statusMessage: account.statusMessage,
			bio: account.bio,
			presence: this.effectivePresence(account),
			explicitPresence: account.presence,
			avatarUrl: account.avatar
				? `${this.publicBaseUrl}/avatars/${account.id}.${account.avatar.ext}?v=${account.avatar.version}`
				: null,
			headerUrl: account.header
				? `${this.publicBaseUrl}/headers/${account.id}.${account.header.ext}?v=${account.header.version}`
				: null,
			createdAt: new Date(account.createdAt).toISOString(),
			lastSeen: this.lastSeen.has(account.id) ? new Date(this.lastSeen.get(account.id) ?? 0).toISOString() : null,
			...(self ? { gameAccount: account.gameAccount } : {})
		};
	}

	private async createSession(account: Account): Promise<string> {
		const token = newToken();
		this.chat?.touch(account, `launcher:${token}`);
		this.store.accountData.sessions = this.store.accountData.sessions.filter(session => session.expiresAt > Date.now());
		this.store.accountData.sessions.push({
			token,
			accountId: account.id,
			createdAt: Date.now(),
			expiresAt: Date.now() + SESSION_TTL_MS
		});
		await this.store.saveAccounts();
		return token;
	}
}

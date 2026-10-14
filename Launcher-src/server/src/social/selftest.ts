import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import type { AddressInfo } from 'node:net';
import os from 'node:os';
import path from 'node:path';

import express from 'express';

import { attachSocial } from './routes.js';

const tinyPng = Buffer.from(
	'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFAAH/q842iQAAAABJRU5ErkJggg==',
	'base64'
);
const tinyGif = Buffer.from('R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7', 'base64');
// 1.5 MB of padding keeps the PNG magic bytes while pushing the base64 body past the
// 1 MB JSON parser limit that used to reject real uploads.
const bigPng = Buffer.concat([tinyPng, Buffer.alloc(1_500_000, 7)]);

const main = async () => {
	const dataDir = await fs.mkdtemp(path.join(os.tmpdir(), 'esteria-social-'));
	const app = express();
	const service = await attachSocial(app, { dataDir });
	const server = app.listen(0);
	const port = (server.address() as AddressInfo).port;
	const base = `http://127.0.0.1:${port}`;

	const call = async (
		method: string,
		route: string,
		options: { token?: string; body?: unknown } = {}
	): Promise<{ status: number; json: any }> => {
		const response = await fetch(`${base}${route}`, {
			method,
			headers: {
				...(options.body === undefined ? {} : { 'content-type': 'application/json' }),
				...(options.token ? { authorization: `Bearer ${options.token}` } : {})
			},
			...(options.body === undefined ? {} : { body: JSON.stringify(options.body) })
		});
		return { status: response.status, json: await response.json().catch(() => null) };
	};

	try {
		const registered = await call('POST', '/api/v2/account/register', {
			body: { username: 'Aelira', password: 'hunter2', displayName: 'Aelira' }
		});
		assert.equal(registered.status, 201, 'register succeeds');
		const aelira = registered.json.token as string;
		assert.equal(registered.json.account.username, 'aelira', 'username is lowercased');

		const duplicate = await call('POST', '/api/v2/account/register', {
			body: { username: 'aelira', password: 'hunter2' }
		});
		assert.equal(duplicate.status, 409, 'duplicate account name rejected');

		const weak = await call('POST', '/api/v2/account/register', { body: { username: 'bo', password: 'x' } });
		assert.equal(weak.status, 400, 'short name/password rejected');

		const wrongPassword = await call('POST', '/api/v2/account/login', {
			body: { username: 'aelira', password: 'nope' }
		});
		assert.equal(wrongPassword.status, 401, 'wrong password rejected');

		const anonymous = await call('GET', '/api/v2/account/me');
		assert.equal(anonymous.status, 401, 'unauthenticated request rejected');

		const profiled = await call('POST', '/api/v2/account/profile', {
			token: aelira,
			body: { statusMessage: 'Running heroics', presence: 'dnd' }
		});
		assert.equal(profiled.json.account.statusMessage, 'Running heroics', 'status message saved');
		assert.equal(profiled.json.account.presence, 'dnd', 'presence published');

		const heartbeat = await call('POST', '/api/v2/social/heartbeat', {
			token: aelira,
			body: { presence: 'away', statusMessage: 'In a raid', displayName: 'Aelira' }
		});
		assert.equal(heartbeat.status, 200, 'heartbeat succeeds');
		assert.equal(heartbeat.json.me.presence, 'away', 'heartbeat publishes presence');
		assert.equal(heartbeat.json.me.statusMessage, 'In a raid', 'heartbeat publishes the status message');
		assert.equal(heartbeat.json.me.displayName, 'Aelira', 'heartbeat publishes the display name');

		const second = await call('POST', '/api/v2/account/register', {
			body: { username: 'Borin', password: 'hunter2', displayName: 'Borin' }
		});
		const borin = second.json.token as string;

		const discover = await call('GET', '/api/v2/social/discover?q=bor', { token: aelira });
		assert.equal(discover.json.players.length, 1, 'discovery finds the other account');
		assert.equal(discover.json.players[0].relation, 'none', 'discovery reports relation');

		const requested = await call('POST', '/api/v2/social/friends', { token: aelira, body: { username: 'borin' } });
		assert.deepEqual(requested.json.outgoing, ['borin'], 'outgoing request recorded');
		const pending = await call('GET', '/api/v2/social/feed', { token: borin });
		assert.equal(pending.json.incoming[0].username, 'aelira', 'incoming request visible to target');

		const accepted = await call('POST', '/api/v2/social/friends/accept', { token: borin, body: { username: 'aelira' } });
		assert.equal(accepted.json.friends[0].username, 'aelira', 'accept creates the friendship');

		const notFriendsYet = await call('POST', '/api/v2/social/messages', {
			token: aelira,
			body: { to: 'borin', body: 'hi' }
		});
		assert.equal(notFriendsYet.status, 201, 'friends can message');

		const thread = await call('GET', '/api/v2/social/messages?with=aelira&since=0', { token: borin });
		assert.equal(thread.json.messages.length, 1, 'message delivered');
		assert.equal(thread.json.messages[0].from, 'aelira', 'message keeps its sender');
		assert.equal(thread.json.messages[0].read, false, 'background fetching does not mark read');
		await call('POST', '/api/v2/social/chat/op', { token: borin, body: { op: 'read', conversation: 'dm:aelira', cursor: thread.json.messages[0].id } });

		const unread = await call('GET', '/api/v2/social/feed', { token: aelira });
		assert.equal(unread.json.unread, 0, 'sender has no unread from the thread');

		const avatar = await call('PUT', '/api/v2/account/avatar', {
			token: aelira,
			body: { mimeType: 'image/png', dataBase64: tinyPng.toString('base64') }
		});
		assert.match(avatar.json.account.avatarUrl, /^\/avatars\/1\.png\?v=1$/, 'avatar url returned');
		const avatarResponse = await fetch(`${base}${avatar.json.account.avatarUrl}`);
		assert.equal(avatarResponse.status, 200, 'avatar file is served');
		assert.equal(avatarResponse.headers.get('content-type'), 'image/png', 'avatar served as an image');

		const fake = await call('PUT', '/api/v2/account/avatar', {
			token: borin,
			body: { mimeType: 'image/png', dataBase64: Buffer.from('not an image at all').toString('base64') }
		});
		assert.equal(fake.status, 415, 'non-image avatar rejected');

		const gifAvatar = await call('PUT', '/api/v2/account/avatar', {
			token: borin,
			body: { mimeType: 'image/gif', dataBase64: tinyGif.toString('base64') }
		});
		assert.equal(gifAvatar.status, 200, 'gif avatars accepted');
		assert.match(gifAvatar.json.account.avatarUrl, /\.gif/, 'gif avatar keeps its extension');

		const profiledBio = await call('POST', '/api/v2/account/profile', {
			token: aelira,
			body: { bio: 'Raiding since 2009', statusMessage: 'Running heroics' }
		});
		assert.equal(profiledBio.json.account.bio, 'Raiding since 2009', 'bio stored');

		const header = await call('PUT', '/api/v2/account/header', {
			token: aelira,
			body: { mimeType: 'image/png', dataBase64: tinyPng.toString('base64') }
		});
		assert.match(header.json.account.headerUrl, /^\/headers\/1\.png\?v=1$/, 'header url returned');
		const headerResponse = await fetch(`${base}${header.json.account.headerUrl}`);
		assert.equal(headerResponse.status, 200, 'header file is served');
		assert.equal(headerResponse.headers.get('content-type'), 'image/png', 'header keeps its content type');

		const bigAvatar = await call('PUT', '/api/v2/account/avatar', {
			token: borin,
			body: { mimeType: 'image/png', dataBase64: bigPng.toString('base64') }
		});
		assert.equal(bigAvatar.status, 200, 'a 1.5 MB avatar passes the body parser');

		const bigHeader = await call('PUT', '/api/v2/account/header', {
			token: borin,
			body: { mimeType: 'image/gif', dataBase64: Buffer.concat([tinyGif, Buffer.alloc(1_200_000, 7)]).toString('base64') }
		});
		assert.equal(bigHeader.status, 200, 'a 1.2 MB gif header passes the body parser');
		assert.match(bigHeader.json.account.headerUrl, /^\/headers\/\d+\.gif\?v=\d+$/, 'gif header keeps its extension');
		const gifHeaderResponse = await fetch(`${base}${bigHeader.json.account.headerUrl}`);
		assert.equal(gifHeaderResponse.status, 200, 'gif header is served');
		assert.equal(gifHeaderResponse.headers.get('content-type'), 'image/gif', 'gif header keeps its content type');

		const friendSeesHeader = await call('GET', '/api/v2/social/feed', { token: aelira });
		const borinEntry = friendSeesHeader.json.friends.find((friend: { username: string }) => friend.username === 'borin');
		assert.ok(borinEntry.headerUrl, 'friends see each other profile headers in the feed');
		assert.match(borinEntry.headerUrl, /^\/headers\/\d+\.gif\?/, 'feed header url points at the header file');

		const meta = await call('POST', '/api/v2/social/friends/aelira', {
			token: borin,
			body: { nickname: 'Ael', favorite: true }
		});
		assert.equal(meta.json.friends[0].note, 'Ael', 'nickname stored');
		assert.equal(meta.json.friends[0].favorite, true, 'favorite stored');

		const card = await call('GET', '/api/v2/social/profiles/aelira', { token: borin });
		assert.equal(card.json.profile.bio, 'Raiding since 2009', 'profile card carries the bio');
		assert.equal(card.json.profile.favorite, true, 'profile card carries friend metadata');
		assert.equal(card.json.profile.relation, 'friend', 'profile card reports the relation');

		const group = await call('POST', '/api/v2/social/groups', {
			token: aelira,
			body: { name: 'Weekly raid', members: ['borin'] }
		});
		assert.equal(group.status, 201, 'group created');
		assert.deepEqual(group.json.group.members, ['aelira', 'borin'], 'group members resolved');
		const groupId = group.json.group.id as number;
		const groupMessage = await call('POST', `/api/v2/social/groups/${groupId}/messages`, {
			token: borin,
			body: { body: 'On my way' }
		});
		assert.equal(groupMessage.status, 201, 'group message sent');
		const groupThread = await call('GET', `/api/v2/social/groups/${groupId}/messages?since=0`, { token: aelira });
		assert.equal(groupThread.json.messages.length, 1, 'group message delivered to members');
		assert.equal(groupThread.json.messages[0].from, 'borin', 'group message keeps its sender');
		const groupList = await call('GET', '/api/v2/social/groups', { token: borin });
		assert.equal(groupList.json.groups.length, 1, 'group listed for its members');

		const post = await call('POST', '/api/v2/social/posts', {
			token: aelira,
			body: { body: 'First look at the new zone', mimeType: 'image/png', dataBase64: tinyPng.toString('base64') }
		});
		assert.equal(post.status, 201, 'post created');
		assert.match(post.json.post.mediaUrl, /^\/media\/1\.png$/, 'post media url returned');
		const postMedia = await fetch(`${base}${post.json.post.mediaUrl}`);
		assert.equal(postMedia.status, 200, 'post media served');
		const friendFeed = await call('GET', '/api/v2/social/posts?since=0', { token: borin });
		assert.equal(friendFeed.json.posts.length, 1, 'friends see the post');

		const stranger = await call('POST', '/api/v2/account/register', {
			body: { username: 'Stranger', password: 'hunter2' }
		});
		const strangerFeed = await call('GET', '/api/v2/social/posts?since=0', { token: stranger.json.token });
		assert.equal(strangerFeed.json.posts.length, 0, 'non-friends do not see the post');

		const removed = await call('DELETE', '/api/v2/social/friends/aelira', { token: borin });
		assert.equal(removed.json.friends.length, 0, 'removing a friend empties the list');
		const blocked = await call('POST', '/api/v2/social/messages', {
			token: aelira,
			body: { to: 'borin', body: 'still there?' }
		});
		assert.equal(blocked.status, 403, 'messages stop once the friendship ends');

		await call('POST', '/api/v2/account/logout', { token: aelira });
		const afterLogout = await call('GET', '/api/v2/account/me', { token: aelira });
		assert.equal(afterLogout.status, 401, 'logged-out token is rejected');

		console.log('social selftest passed');
	} finally {
		service.chat?.stop();
		service.chat?.store.close();
		server.close();
		await fs.rm(dataDir, { recursive: true, force: true });
	}
};

await main();

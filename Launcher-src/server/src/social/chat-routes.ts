import express from 'express';
import sharp from 'sharp';
import fs from 'node:fs/promises';
import { ChatService } from './chat.js';
import { ApiError } from './service.js';
import type { Account, ChatMessage } from './store.js';

const string = (value: unknown) => typeof value === 'string' ? value : '';
const handler = (fn: (req: express.Request, res: express.Response) => Promise<void>): express.RequestHandler =>
  (req, res, next) => { fn(req, res).catch(next); };

export function dmWire(chat: ChatService, m: ChatMessage) {
  return { id: m.id, from: chat.social.accountFor(m.from)?.username ?? '', to: chat.social.accountFor(m.to)?.username ?? '',
    body: m.body, createdAt: new Date(m.createdAt).toISOString(), read: m.readAt !== null, attachments: chat.attachments(m.attachments) };
}
export async function chatOperation(chat: ChatService, account: Account, p: Record<string, unknown>) {
  chat.rate(`op:${account.id}`);
  const key = string(p.conversation);
  const since = Number(p.since ?? 0);
  const before = p.before === undefined ? Infinity : Number(p.before);
  switch (p.op) {
    case 'capabilities': return chat.capabilities();
    case 'feed': {
      const feed = await chat.social.feed(account);
      const page = Math.max(0, Math.min(10000, Number(p.page) || 0));
      const brief = ({ bio, headerUrl, ...profile }: typeof feed.me) => profile;
      return { ...feed, me: brief(feed.me), friends: feed.friends.slice(page * 8, page * 8 + 8).map(brief), incoming: feed.incoming.slice(page * 8, page * 8 + 8).map(brief),
        outgoing: feed.outgoing.slice(page * 8, page * 8 + 8), groups: chat.social.myGroups(account).slice(page * 8, page * 8 + 8),
        hasMore: Math.max(feed.friends.length, feed.incoming.length, feed.outgoing.length, chat.social.myGroups(account).length) > page * 8 + 8 };
    }
    case 'history': {
      chat.conversation(account, key);
      if (!Number.isSafeInteger(since) || since < 0 || !(before === Infinity || Number.isSafeInteger(before) && before > 0))
        throw new ApiError(400, 'invalid_cursor', 'Invalid history cursor.');
      const messages = key.startsWith('group:')
        ? await chat.social.groupMessages(account, Number(key.slice(6)), since, before)
        : (await chat.social.messagesWith(account, key.replace(/^dm:/, ''), since, before)).map(m => dmWire(chat, m));
      const ordered = since > 0 ? messages : [...messages].reverse();
      const page: Array<(typeof messages)[number]> = [];
      for (const message of ordered) {
        if (page.length >= 8 || Buffer.byteLength(JSON.stringify([...page, message])) > 18000) break;
        page.push(message);
      }
      if (since === 0) page.reverse();
      return { messages: page, hasMore: messages.length > page.length || messages.length === 200 };
    }
    case 'send': {
      if (!string(p.requestId)) throw new ApiError(400, 'request_id_required', 'A durable request ID is required.');
      const message = key.startsWith('group:')
        ? await chat.social.sendGroupMessage(account, Number(key.slice(6)), string(p.body), p.attachments, string(p.requestId))
        : dmWire(chat, await chat.social.sendMessage(account, key.replace(/^dm:/, ''), string(p.body), p.attachments, string(p.requestId)));
      return { message };
    }
    case 'read': await chat.read(account, key, Number(p.cursor)); return { ok: true };
    case 'attachmentMetadata': {
      if (!Array.isArray(p.ids) || p.ids.length > 128) throw new ApiError(400, 'invalid_attachments', 'Request up to 128 attachment IDs.');
      return { attachments: p.ids.map(id => chat.state.attachments.find(a => a.id === id)).filter(a => a && chat.canAccess(account, a)).map(a => chat.attachmentWire(a!)) };
    }
    case 'friend': return chat.social.requestFriend(account, string(p.username));
    case 'accept': return chat.social.acceptFriend(account, string(p.username));
    case 'removeFriend': return chat.social.removeFriend(account, string(p.username));
    case 'createGroup': return { group: await chat.social.createGroup(account, string(p.name),
      Array.isArray(p.members) ? p.members.filter((v): v is string => typeof v === 'string') : []) };
    case 'leaveGroup': await chat.social.leaveGroup(account, Number(p.groupId)); return { ok: true };
    case 'removeMember': await chat.social.removeGroupMember(account, Number(p.groupId), string(p.username)); return { ok: true };
    case 'presence': return { account: await chat.social.updateProfile(account, { presence: p.presence }) };
    case 'privacy': return { account: await chat.social.updateProfile(account, { shareCharacterPresence: p.shareCharacterPresence }) };
    case 'block': await chat.block(account, string(p.username), p.remove === true); return { ok: true };
    case 'report': await chat.report(account, key, Number(p.messageId), string(p.reason)); return { ok: true };
    default: throw new ApiError(400, 'unknown_operation', 'Unsupported chat operation.');
  }
}

export function mountChat(router: express.Router, chat: ChatService, requireAuth: express.RequestHandler): void {
  const base = '/api/v2/social/chat';
  router.get(`${base}/capabilities`, (_req, res) => res.json(chat.capabilities()));
  router.get(`${base}/links`, requireAuth, handler(async (_req, res) => { res.json(chat.linkStatus(res.locals.account)); }));
  router.post(`${base}/links/challenge`, requireAuth, handler(async (_req, res) => { res.json(await chat.challenge(res.locals.account)); }));
  router.post(`${base}/links/confirm`, requireAuth, handler(async (req, res) => { res.json(await chat.confirm(res.locals.account, Number(req.body.gameId))); }));
  router.delete(`${base}/links/:id`, requireAuth, handler(async (req, res) => { await chat.unlink(res.locals.account, req.params.id ?? ""); res.json({ ok: true }); }));
  router.post(`${base}/op`, requireAuth, handler(async (req, res) => { res.json(await chatOperation(chat, res.locals.account, req.body)); }));
  const mediaAuth: express.RequestHandler = (req, res, next) => {
    if (req.get('x-chat-helper')) {
      try { res.locals.account = chat.helperAccount(req.get('x-chat-helper')!); next(); } catch (error) { next(error); }
    } else requireAuth(req, res, next);
  };
  router.post(`${base}/attachments`, mediaAuth, handler(async (req, res) => {
    if (req.readableEnded) throw new ApiError(415, 'binary_required', 'Upload the raw image body.');
    req.setTimeout(30000, () => req.destroy());
    const deadline = setTimeout(() => req.destroy(new Error('Upload timed out')), 30000);
    try { res.status(201).json({ attachment: await chat.upload(res.locals.account, string(req.query.conversation), req, req.get('content-type') ?? '') }); }
    finally { clearTimeout(deadline); }
  }));
  router.get(`${base}/attachments/:id`, mediaAuth, handler(async (req, res) => {
    if (/^avatar_\d{1,10}$/.test(req.params.id ?? '')) {
      const target = chat.social.accountFor(Number(req.params.id!.slice(7)));
      const viewer = res.locals.account as Account;
      if (!target?.avatar || (viewer.id !== target.id && (!chat.social.linkBetween(viewer.id, target.id) || chat.blocked(viewer.id, target.id))))
        throw new ApiError(403, 'avatar_denied', 'Avatar unavailable.');
      const source = sharp(await fs.readFile(chat.store.avatarPath(target.id, target.avatar.ext)), { animated: true,
        limitInputPixels: chat.config.media.MaxDecodedFramePixels, failOn: 'warning' });
      const meta = await source.metadata();
      if ((meta.pages ?? 1) > chat.config.media.MaxFrames) throw new ApiError(413, 'decode_limit', 'Avatar animation exceeds the client limit.');
      const preview = source.resize({ width: 320, height: 180, fit: 'fill' });
      const data = await ((meta.pages ?? 1) > 1 ? preview.gif() : preview.png()).toBuffer();
      if (data.length > chat.config.media.MaxUploadBytes) throw new ApiError(413, 'preview_limit', 'Avatar preview exceeds client limits.');
      res.setHeader('Cache-Control', 'private, no-store'); res.setHeader('X-Chat-Expires-At', String(Date.now() + 60000));
      res.type((meta.pages ?? 1) > 1 ? 'gif' : 'png').send(data); return;
    }
    const attachment = chat.download(res.locals.account, req.params.id ?? "");
    res.setHeader('Cache-Control', 'private, no-store');
    res.setHeader('X-Content-Type-Options', 'nosniff');
    res.setHeader('X-Chat-Expires-At', String(chat.attachmentWire(attachment).expiresAt));
    if (req.query.preview === '1') {
      const preview = sharp(await fs.readFile(chat.file(attachment.id)), { animated: attachment.frames > 1,
        limitInputPixels: chat.config.media.MaxDecodedFramePixels, failOn: 'warning' })
        .resize({ width: 320, height: 180, fit: 'contain', background: { r: 0, g: 0, b: 0, alpha: 0 } });
      const data = await (attachment.frames > 1 ? preview.gif() : preview.png()).toBuffer();
      chat.download(res.locals.account, attachment.id);
      if (data.length > chat.config.media.MaxUploadBytes) throw new ApiError(413, 'preview_limit', 'Preview exceeds media limit.');
      res.type(attachment.frames > 1 ? 'gif' : 'png').send(data);
      return;
    }
    res.type(attachment.ext === 'jpg' ? 'jpeg' : attachment.ext);
    res.sendFile(chat.file(attachment.id), { cacheControl: false, acceptRanges: false }, error => {
      if (error && !res.headersSent) res.status(410).json({ error: 'attachment_expired', message: 'Attachment expired' });
    });
  }));
  router.delete(`${base}/attachments/:id`, mediaAuth, handler(async (req, res) => { await chat.cancel(res.locals.account, req.params.id ?? ""); res.json({ ok: true }); }));
  // This credential exists only in the core's config; no addon-supplied social identity is accepted.
  router.get('/api/v2/bridge/chat/reports', handler(async (req, res) => {
    chat.bridgeAuth((req.get('authorization') ?? '').replace(/^Bearer /i, ''));
    res.setHeader('Cache-Control', 'private, no-store'); res.json({ reports: chat.state.reports ?? [], cleanupFailures: chat.state.attachments.filter(a => a.cleanupError).map(a => a.id) });
  }));
  router.post('/api/v2/bridge/chat', handler(async (req, res) => {
    chat.bridgeAuth((req.get('authorization') ?? '').replace(/^Bearer /i, ''));
    const p = req.body as Record<string, unknown>;
    if (p.protocolVersion !== 1 || p.serverId !== chat.config.serverId || p.realmId !== chat.config.realmId)
      throw new ApiError(400, 'incompatible_bridge', 'Bridge protocol or realm mismatch.');
    const gameId = Number(p.gameId);
    chat.rate(`bridge:${gameId}`, 90);
    if (p.op === 'link') { res.json(await chat.propose(gameId, string(p.code), string(p.gameName))); return; }
    if (p.op === 'logout') { await chat.logoutGame(gameId); res.json({ ok: true }); return; }
    if (p.op === 'mediaTicket') { res.json(await chat.helperTicket(gameId)); return; }
    const account = chat.gameAccount(gameId, string(p.gameName));
    res.json(await chatOperation(chat, account, p));
  }));
}

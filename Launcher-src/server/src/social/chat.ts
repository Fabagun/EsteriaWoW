import { createHash, randomBytes, timingSafeEqual } from 'node:crypto';
import fs from 'node:fs/promises';
import path from 'node:path';
import sharp from 'sharp';
import type { Metadata } from 'sharp';
import { ApiError, SocialService } from './service.js';
import { Account, Store, sniffImageType } from './store.js';

export const defaults = {
  RetentionHours: 168, MaxUploadBytes: 10485760, MaxAttachmentsPerMessage: 4,
  MaxMessageUploadBytes: 20971520, CleanupIntervalSeconds: 300, OrphanRetentionMinutes: 60,
  CacheMaxBytes: 268435456, MaxConcurrentAnimations: 3, MaxDimension: 4096,
  MaxDecodedPixels: 16777216, MaxDecodedFramePixels: 67108864, MaxFrames: 120,
  MaxAnimationDurationMs: 60000, UploadsPerMinute: 6, AccountQuotaBytes: 104857600,
  StorageBudgetBytes: 10737418240
};
export type MediaPolicy = typeof defaults;
export interface ChatConfig {
  media: MediaPolicy;
  bridgeSecret: string;
  serverId: string;
  realmId: string;
  productName: string;
  maxLinks: number;
  formats: string[];
  branding: { background: string; panel: string; accent: string; text: string; font: string };
  features: { direct: boolean; friends: boolean; groups: boolean; attachments: boolean; characterPresence: boolean };
}
export function chatConfig(env: NodeJS.ProcessEnv = process.env): ChatConfig {
  const media = { ...defaults };
  for (const key of Object.keys(defaults) as Array<keyof MediaPolicy>) {
    const value = Number(env[`CHAT_MEDIA_${key.replace(/[A-Z]/g, (c, i) => `${i ? '_' : ''}${c}`).toUpperCase()}`] ?? defaults[key]);
    if (!Number.isSafeInteger(value) || value < 1 || value > Math.max(defaults[key] * 16, 1000))
      throw new Error(`ChatMedia.${key} must be a positive integer <= ${Math.max(defaults[key] * 16, 1000)}.`);
    media[key] = value;
  }
  if (media.MaxUploadBytes > media.MaxMessageUploadBytes || media.AccountQuotaBytes < media.MaxMessageUploadBytes ||
      media.StorageBudgetBytes < media.AccountQuotaBytes || media.MaxDimension > 8192 || media.MaxFrames > 240 ||
      media.MaxDecodedFramePixels > 268435456 || media.MaxAttachmentsPerMessage > 8 || media.MaxConcurrentAnimations > 8 ||
      media.OrphanRetentionMinutes > media.RetentionHours * 60)
    throw new Error('Invalid ChatMedia limits: check upload/message/quota/storage, dimension <=8192, frames <=240, decoded pixels <=268435456, attachments/animations <=8, and orphan <= retention.');
  const maxLinks = Number(env.CHAT_MAX_LINKS ?? 1);
  if (!Number.isInteger(maxLinks) || maxLinks < 1 || maxLinks > 8) throw new Error('CHAT_MAX_LINKS must be 1..8.');
  const bridgeSecret = env.CHAT_BRIDGE_SECRET ?? '';
  const formats = (env.CHAT_MEDIA_FORMATS ?? 'png,jpg,gif,webp').split(',').map(value => value.trim());
  if (!formats.length || formats.some(format => !['png', 'jpg', 'gif', 'webp'].includes(format))) throw new Error('CHAT_MEDIA_FORMATS must list PNG/JPG/GIF/WebP format names in lowercase.');
  if (bridgeSecret && bridgeSecret.length < 32) throw new Error('CHAT_BRIDGE_SECRET needs at least 32 characters.');
  const serverId = env.CHAT_SERVER_ID ?? 'esteria';
  const realmId = env.CHAT_REALM_ID ?? '1';
  if (![serverId, realmId].every(value => /^[A-Za-z0-9_.-]{1,64}$/.test(value))) throw new Error('Invalid chat server/realm ID.');
  const branding = { background: env.CHAT_COLOR_BACKGROUND ?? '#14171c', panel: env.CHAT_COLOR_PANEL ?? '#1a1e24',
    accent: env.CHAT_COLOR_ACCENT ?? '#b88a44', text: env.CHAT_COLOR_TEXT ?? '#eef1f5', font: env.CHAT_FONT ?? 'NotoSans-Regular.ttf' };
  if (![branding.background, branding.panel, branding.accent, branding.text].every(c => /^#[0-9a-fA-F]{6}$/.test(c)) ||
      !/^[A-Za-z0-9_.-]+\.(ttf|otf)$/.test(branding.font)) throw new Error('Invalid chat branding color or packaged font filename.');
  return { media, bridgeSecret, serverId, realmId, maxLinks, formats, branding, productName: (env.CHAT_PRODUCT_NAME ?? 'Esteria').slice(0, 64),
    features: { direct: env.CHAT_DIRECT !== 'false', friends: env.CHAT_FRIENDS !== 'false', groups: env.CHAT_GROUPS !== 'false',
      attachments: env.CHAT_ATTACHMENTS !== 'false', characterPresence: env.CHAT_CHARACTER_PRESENCE === 'true' } };
}
interface Link { id: string; accountId: number; serverId: string; realmId: string; gameId: number; revision: string }
interface Challenge { hash: string; accountId: number; expiresAt: number; candidate?: { gameId: number; name: string } }
interface Credential { hash: string; linkId: string; revision: string; expiresAt: number; sessionId: string }
export interface Attachment {
  id: string; ownerId: number; conversation: string; createdAt: number; expiresAt: number;
  bytes: number; ext: string; width: number; height: number; frames: number; durationMs: number;
  associated: boolean; deletedAt?: number; cleanupError?: boolean;
}
export interface ChatState {
  links: Link[]; challenges: Challenge[]; credentials: Credential[]; attachments: Attachment[];
  reads: Record<string, number>; blocks: Array<{ from: number; to: number }>;
  audit: Array<{ at: number; action: string; accountId: number; gameId: number }>;
  reports?: Array<{ at: number; from: number; conversation: string; messageId: number; reason: string }>;
}
const digest = (token: string) => createHash('sha256').update(token).digest('hex');
const opaque = () => randomBytes(24).toString('base64url');
function fail(status: number, code: string, message: string): never { throw new ApiError(status, code, message); }

export class ChatService {
  readonly state: ChatState;
  readonly mediaRoot: string;
  private readonly live = new Map<string, { accountId: number; at: number; characterName?: string }>();
  private readonly rates = new Map<string, { at: number; count: number }>();
  private tail = Promise.resolve();
  private cleanupTimer?: ReturnType<typeof setInterval>;
  private queued = 0;
  constructor(readonly store: Store, readonly social: SocialService, readonly config = chatConfig()) {
    this.state = store.socialData.chat ??= { links: [], challenges: [], credentials: [], attachments: [], reads: {}, blocks: [], audit: [] };
    this.mediaRoot = path.resolve(store.dataDir, 'chat-private');
  }
  async start(): Promise<void> {
    await fs.mkdir(this.mediaRoot, { recursive: true });
    await this.cleanup();
    this.cleanupTimer = setInterval(() => void this.cleanup().catch(() => console.error('Chat cleanup failed; retry scheduled.')),
      this.config.media.CleanupIntervalSeconds * 1000);
    this.cleanupTimer.unref();
  }
  stop(): void { if (this.cleanupTimer) clearInterval(this.cleanupTimer); }
  // Serializes upload reservation, validation, cancellation and cleanup, including their filesystem work.
  exclusive<T>(work: () => Promise<T>): Promise<T> {
    if (this.queued >= 16) return Promise.reject(new ApiError(503, 'media_busy', 'Media queue is busy. Retry shortly.'));
    this.queued++;
    const pending = this.tail.then(work).finally(() => { this.queued--; });
    this.tail = pending.then(() => undefined, () => undefined);
    return pending;
  }
  capabilities() {
    return { protocolVersion: 1, policyVersion: digest(JSON.stringify(this.config.media)), productName: this.config.productName,
      serverId: this.config.serverId, realmId: this.config.realmId, features: this.config.features,
      media: { ...this.config.media, formats: this.config.formats },
      transport: { fragmentBytes: 180, maxFragments: 128, maxBytes: 23040, timeoutSeconds: 15 },
      branding: this.config.branding };
  }
  bridgeAuth(token: string): void {
    const expected = Buffer.from(this.config.bridgeSecret);
    const actual = Buffer.from(token);
    if (!expected.length || expected.length !== actual.length || !timingSafeEqual(expected, actual))
      fail(401, 'bridge_unauthorized', 'Bridge authentication failed.');
  }
  rate(key: string, maximum = 60): void {
    const now = Date.now();
    for (const [id, gate] of this.rates) if (now - gate.at >= 60000) this.rates.delete(id);
    const gate = this.rates.get(key) ?? { at: now, count: 0 };
    if (++gate.count > maximum) fail(429, 'rate_limited', 'Please wait before trying again.');
    this.rates.set(key, gate);
  }
  touch(account: Account, sessionId: string): void { this.live.set(sessionId, { accountId: account.id, at: Date.now() }); }
  endSession(sessionId: string): void { this.live.delete(sessionId); }
  active(account: Account): number {
    for (const [id, session] of this.live) if (Date.now() - session.at > 70000) this.live.delete(id);
    return Math.max(0, ...Array.from(this.live.values()).filter(s => s.accountId === account.id).map(s => s.at));
  }
  presenceDetails(account: Account) {
    if (!this.config.features.characterPresence || !account.shareCharacterPresence || account.presence === 'offline') return undefined;
    const session = Array.from(this.live.values()).find(s => s.accountId === account.id && s.characterName && Date.now() - s.at <= 70000);
    return session ? { characterName: session.characterName!, realmId: this.config.realmId, serverId: this.config.serverId } : undefined;
  }
  async challenge(account: Account) {
    this.rate(`link:${account.id}`, 5);
    const code = randomBytes(12).toString('hex');
    const expiresAt = Date.now() + 5 * 60000;
    this.state.challenges = this.state.challenges.filter(c => c.accountId !== account.id && c.expiresAt > Date.now());
    this.state.challenges.push({ hash: digest(code), accountId: account.id, expiresAt });
    await this.store.saveSocial();
    return { code, expiresAt, instructions: 'Enter /ec link CODE in game, then confirm these identities here.' };
  }
  async propose(gameId: number, code: string, name: string) {
    this.validGameId(gameId);
    this.rate(`propose:${gameId}`, 5);
    const challenge = this.state.challenges.find(c => c.hash === digest(code) && c.expiresAt > Date.now());
    if (!challenge || challenge.candidate) fail(410, 'link_expired', 'Link code expired or already used.');
    challenge.candidate = { gameId, name: name.slice(0, 64) };
    await this.store.saveSocial();
    return { username: this.social.accountFor(challenge.accountId)?.username, gameId, confirmInLauncher: true };
  }
  linkStatus(account: Account) {
    const challenge = this.state.challenges.find(c => c.accountId === account.id && c.expiresAt > Date.now());
    return { links: this.state.links.filter(l => l.accountId === account.id).map(({ revision, ...l }) => l),
      pending: challenge?.candidate ? { ...challenge.candidate, expiresAt: challenge.expiresAt,
        username: account.username, serverId: this.config.serverId, realmId: this.config.realmId } : null };
  }
  async confirm(account: Account, gameId: number) {
    const challenge = this.state.challenges.find(c => c.accountId === account.id && c.expiresAt > Date.now() && c.candidate?.gameId === gameId);
    if (!challenge) fail(410, 'link_expired', 'No matching game confirmation.');
    if (this.state.links.some(l => l.serverId === this.config.serverId && l.realmId === this.config.realmId && l.gameId === gameId))
      fail(409, 'already_linked', 'Game account is already linked; unlink first.');
    if (this.state.links.filter(l => l.accountId === account.id).length >= this.config.maxLinks)
      fail(409, 'link_limit', 'Linked account limit reached.');
    this.state.links.push({ id: opaque(), accountId: account.id, gameId, serverId: this.config.serverId,
      realmId: this.config.realmId, revision: opaque() });
    this.state.challenges = this.state.challenges.filter(c => c !== challenge);
    this.state.audit.push({ at: Date.now(), action: 'link', accountId: account.id, gameId });
    await this.store.saveSocial();
    return this.linkStatus(account);
  }
  async unlink(account: Account, id: string): Promise<void> {
    const link = this.state.links.find(l => l.id === id && l.accountId === account.id);
    if (!link) fail(404, 'unknown_link', 'Link not found.');
    this.state.links = this.state.links.filter(l => l !== link);
    for (const credential of this.state.credentials.filter(c => c.linkId === id)) this.endSession(credential.sessionId);
    this.state.credentials = this.state.credentials.filter(c => c.linkId !== id);
    this.endSession(`game:${id}`);
    this.state.audit.push({ at: Date.now(), action: 'unlink', accountId: account.id, gameId: link.gameId });
    await this.store.saveSocial();
  }
  private validGameId(gameId: number): void {
    if (!Number.isSafeInteger(gameId) || gameId < 1 || gameId > 4294967295) fail(400, 'game_id', 'Invalid game account.');
  }
  gameAccount(gameId: number, characterName = ''): Account {
    this.validGameId(gameId);
    const link = this.state.links.find(l => l.gameId === gameId && l.serverId === this.config.serverId && l.realmId === this.config.realmId);
    const account = link && this.social.accountFor(link.accountId);
    if (!account) fail(403, 'not_linked', 'Link your game account in the launcher first.');
    this.touch(account, `game:${link!.id}`);
    if (characterName) this.live.get(`game:${link!.id}`)!.characterName = characterName.slice(0, 64);
    return account;
  }
  async helperTicket(gameId: number) {
    this.gameAccount(gameId);
    const link = this.state.links.find(l => l.gameId === gameId && l.realmId === this.config.realmId && l.serverId === this.config.serverId)!;
    const token = opaque();
    const expiresAt = Date.now() + 60000;
    this.state.credentials = this.state.credentials.filter(c => c.expiresAt > Date.now());
    this.state.credentials.push({ hash: digest(token), linkId: link.id, revision: link.revision, expiresAt, sessionId: `helper:${opaque()}` });
    await this.store.saveSocial();
    return { token, expiresAt };
  }
  helperAccount(token: string): Account {
    const credential = this.state.credentials.find(c => c.hash === digest(token) && c.expiresAt > Date.now());
    const link = credential && this.state.links.find(l => l.id === credential.linkId && l.revision === credential.revision);
    const account = link && this.social.accountFor(link.accountId);
    if (!account) fail(401, 'helper_expired', 'Refresh media authorization through the game session.');
    return account;
  }
  async logoutGame(gameId: number): Promise<void> {
    const link = this.state.links.find(l => l.gameId === gameId && l.realmId === this.config.realmId && l.serverId === this.config.serverId);
    if (link) {
      this.endSession(`game:${link.id}`);
      this.state.credentials = this.state.credentials.filter(c => c.linkId !== link.id);
      await this.store.saveSocial();
    }
  }
  blocked(a: number, b: number): boolean { return this.state.blocks.some(v => (v.from === a && v.to === b) || (v.from === b && v.to === a)); }
  async block(account: Account, username: string, remove: boolean): Promise<void> {
    const target = this.social.findByUsername(username);
    if (!target || target.id === account.id) fail(400, 'invalid_player', 'Choose another player.');
    this.state.blocks = this.state.blocks.filter(b => b.from !== account.id || b.to !== target.id);
    if (!remove) this.state.blocks.push({ from: account.id, to: target.id });
    await this.store.saveSocial();
  }
  conversation(account: Account, key: string): string {
    if (key.startsWith('group:')) {
      const id = Number(key.slice(6));
      if (!this.config.features.groups) fail(403, 'disabled', 'Groups are disabled.');
      if (!this.store.socialData.groups.some(g => g.id === id && g.members.includes(account.id))) fail(403, 'not_a_member', 'You are not in that group.');
      return `group:${id}`;
    }
    if (!this.config.features.direct) fail(403, 'disabled', 'Direct chat is disabled.');
    const target = this.social.findByUsername(key.replace(/^dm:/, ''));
    if (!target || !this.social.linkBetween(account.id, target.id) || this.blocked(account.id, target.id))
      fail(403, 'not_friends', 'Chat requires an unblocked friend.');
    return `dm:${Math.min(account.id, target.id)}:${Math.max(account.id, target.id)}`;
  }
  canAccess(account: Account, attachment: Attachment): boolean {
    if (attachment.conversation.startsWith('group:')) {
      const group = this.store.socialData.groups.find(g => `group:${g.id}` === attachment.conversation);
      return Boolean(group?.members.includes(account.id) && !this.blocked(account.id, attachment.ownerId));
    }
    const ids = attachment.conversation.split(':').slice(1).map(Number);
    return ids.includes(account.id) && Boolean(this.social.linkBetween(ids[0]!, ids[1]!)) && !this.blocked(ids[0]!, ids[1]!);
  }
  file(id: string): string {
    if (!/^[A-Za-z0-9_-]{32}$/.test(id)) fail(404, 'unknown_attachment', 'Attachment not found.');
    return path.join(this.mediaRoot, id);
  }
  attachmentWire(attachment: Attachment) {
    const expiresAt = Math.min(attachment.expiresAt, attachment.createdAt + this.config.media.RetentionHours * 3600000);
    const expired = expiresAt <= Date.now() || Boolean(attachment.deletedAt);
    return { id: attachment.id, expiresAt, bytes: attachment.bytes, format: attachment.ext, width: attachment.width,
      height: attachment.height, frames: attachment.frames, durationMs: attachment.durationMs, expired,
      url: expired ? null : `/api/v2/social/chat/attachments/${attachment.id}` };
  }
  attachments(ids: string[] = []) { return ids.map(id => this.state.attachments.find(a => a.id === id)).filter((a): a is Attachment => !!a).map(a => this.attachmentWire(a)); }
  prepare(account: Account, key: string, ids: unknown): string[] {
    const conversation = this.conversation(account, key);
    if (ids === undefined) return [];
    if (!Array.isArray(ids) || !ids.every(id => typeof id === 'string') || new Set(ids).size !== ids.length)
      fail(400, 'invalid_attachments', 'Choose valid attachment IDs.');
    if (ids.length && !this.config.features.attachments) fail(403, 'disabled', 'Attachments are disabled.');
    if (ids.length > this.config.media.MaxAttachmentsPerMessage) fail(413, 'attachment_limit', 'Too many attachments.');
    let bytes = 0;
    for (const id of ids) {
      const a = this.state.attachments.find(a => a.id === id);
      if (!a || a.ownerId !== account.id || a.conversation !== conversation || a.associated || this.attachmentWire(a).expired ||
          a.createdAt + this.config.media.OrphanRetentionMinutes * 60000 <= Date.now())
        fail(403, 'invalid_attachment', 'Attachment unavailable or belongs to another conversation.');
      bytes += a.bytes;
    }
    if (bytes > this.config.media.MaxMessageUploadBytes) fail(413, 'message_upload_limit', 'Combined attachments exceed the message limit.');
    return ids as string[];
  }
  associate(ids: string[]): void { for (const id of ids) this.state.attachments.find(a => a.id === id)!.associated = true; }
  async upload(account: Account, key: string, stream: AsyncIterable<Uint8Array>, declared: string) {
    return this.exclusive(async () => {
      if (!this.config.features.attachments) fail(403, 'disabled', 'Attachments are disabled.');
      this.rate(`upload:${account.id}`, this.config.media.UploadsPerMinute);
      const conversation = this.conversation(account, key);
      const id = opaque();
      const temporary = path.join(this.mediaRoot, `${id}.tmp`);
      const handle = await fs.open(temporary, 'wx');
      let bytes = 0;
      try {
        for await (const chunk of stream) {
          bytes += chunk.byteLength;
          if (bytes > this.config.media.MaxUploadBytes) fail(413, 'upload_limit', 'File exceeds the upload limit.');
          await handle.write(chunk);
        }
      } catch (error) { await handle.close(); await fs.rm(temporary, { force: true }); throw error; }
      await handle.close();
      try {
        const data = await fs.readFile(temporary);
        const ext = sniffImageType(data);
        const mime = { png: 'image/png', jpg: 'image/jpeg', gif: 'image/gif', webp: 'image/webp' };
        if (!ext || mime[ext] !== declared || !this.config.formats.includes(ext)) fail(415, 'invalid_image', 'Choose an actual image format allowed by the server.');
        let metadata: Metadata;
        try { metadata = await sharp(data, { animated: true, limitInputPixels: this.config.media.MaxDecodedFramePixels, failOn: 'warning' }).metadata(); }
        catch { fail(415, 'invalid_image', 'Image could not be safely decoded.'); }
        const width = metadata.width ?? 0;
        const height = metadata.pageHeight ?? metadata.height ?? 0;
        const frames = metadata.pages ?? 1;
        const durationMs = (metadata.delay ?? []).reduce((sum, delay) => sum + Math.max(20, delay), 0);
        const p = this.config.media;
        if (!width || !height || width > p.MaxDimension || height > p.MaxDimension || width * height > p.MaxDecodedPixels ||
            width * height * frames > p.MaxDecodedFramePixels || frames > p.MaxFrames || durationMs > p.MaxAnimationDurationMs)
          fail(413, 'decode_limit', 'Image dimensions or animation exceed the server limits.');
        try { await sharp(data, { animated: true, limitInputPixels: p.MaxDecodedFramePixels, failOn: 'warning' }).raw().toBuffer(); }
        catch { fail(415, 'invalid_image', 'Image is malformed.'); }
        this.conversation(account, key);
        const stored = this.state.attachments.filter(a => !a.deletedAt);
        if (stored.filter(a => a.ownerId === account.id).reduce((s, a) => s + a.bytes, 0) + bytes > p.AccountQuotaBytes ||
            stored.reduce((s, a) => s + a.bytes, 0) + bytes > p.StorageBudgetBytes)
          fail(429, 'storage_quota', 'Chat media storage quota reached.');
        const attachment: Attachment = { id, ownerId: account.id, conversation, createdAt: Date.now(),
          expiresAt: Date.now() + p.RetentionHours * 3600000, bytes, ext, width, height, frames, durationMs, associated: false };
        await fs.rename(temporary, this.file(id));
        this.state.attachments.push(attachment);
        await this.store.saveSocial();
        return this.attachmentWire(attachment);
      } finally { await fs.rm(temporary, { force: true }); }
    });
  }
  download(account: Account, id: string): Attachment {
    const a = this.state.attachments.find(a => a.id === id);
    if (!a || !this.canAccess(account, a) || (!a.associated && a.ownerId !== account.id)) fail(403, 'attachment_denied', 'Attachment is not available to this account.');
    if (this.attachmentWire(a).expired || (!a.associated && a.createdAt + this.config.media.OrphanRetentionMinutes * 60000 <= Date.now()))
      fail(410, 'attachment_expired', 'Attachment expired');
    return a;
  }
  async cancel(account: Account, id: string): Promise<void> {
    await this.exclusive(async () => {
      const a = this.state.attachments.find(a => a.id === id && a.ownerId === account.id && !a.associated);
      if (!a) fail(403, 'attachment_denied', 'Only your unused uploads can be cancelled.');
      a.expiresAt = Math.min(a.expiresAt, Date.now());
      await this.store.saveSocial();
      await fs.rm(this.file(id), { force: true });
      a.deletedAt = Date.now();
      await this.store.saveSocial();
    });
  }
  async cleanup(): Promise<void> {
    await this.exclusive(async () => {
      const now = Date.now();
      this.state.challenges = this.state.challenges.filter(c => c.expiresAt > now);
      this.state.credentials = this.state.credentials.filter(c => c.expiresAt > now);
      for (const a of this.state.attachments) {
        a.expiresAt = Math.min(a.expiresAt, a.createdAt + this.config.media.RetentionHours * 3600000);
        if (a.deletedAt || (a.expiresAt > now && (a.associated || a.createdAt + this.config.media.OrphanRetentionMinutes * 60000 > now))) continue;
        try { await fs.rm(this.file(a.id), { force: true }); a.deletedAt = now; a.cleanupError = false; }
        catch { a.cleanupError = true; console.error(`Chat attachment cleanup failed: ${a.id}`); }
      }
      const known = new Set(this.state.attachments.filter(a => !a.deletedAt).map(a => a.id));
      for (const entry of await fs.readdir(this.mediaRoot, { withFileTypes: true })) {
        if (!entry.isFile() || !/^[A-Za-z0-9_-]{32}(\.tmp)?$/.test(entry.name) || known.has(entry.name)) continue;
        await fs.rm(path.join(this.mediaRoot, entry.name), { force: true });
      }
      await this.store.saveSocial();
    });
  }
  async read(account: Account, key: string, cursor: number): Promise<void> {
    const conversation = this.conversation(account, key);
    if (!Number.isSafeInteger(cursor) || cursor < 0) fail(400, 'invalid_cursor', 'Invalid read cursor.');
    const messages = conversation.startsWith('group:')
      ? this.store.socialData.groupMessages.filter(m => `group:${m.groupId}` === conversation)
      : this.store.socialData.messages.filter(m => `dm:${Math.min(m.from, m.to)}:${Math.max(m.from, m.to)}` === conversation);
    if (cursor > messages.reduce((max, m) => Math.max(max, m.id), 0)) fail(400, 'invalid_cursor', 'Read cursor exceeds conversation history.');
    this.state.reads[`${account.id}:${conversation}`] = Math.max(this.state.reads[`${account.id}:${conversation}`] ?? 0, cursor);
    if (conversation.startsWith('dm:')) for (const m of messages as import('./store.js').ChatMessage[])
      if (m.to === account.id && m.id <= cursor && m.readAt === null) m.readAt = Date.now();
    await this.store.saveSocial();
  }
  groupUnread(account: Account, id: number): number {
    const cursor = this.state.reads[`${account.id}:group:${id}`] ?? 0;
    return this.store.socialData.groupMessages.filter(m => m.groupId === id && m.id > cursor && m.from !== account.id && !this.blocked(account.id, m.from)).length;
  }
  async report(account: Account, key: string, messageId: number, reason: string): Promise<void> {
    const conversation = this.conversation(account, key);
    const found = conversation.startsWith('group:') ? this.store.socialData.groupMessages.some(m => m.id === messageId && `group:${m.groupId}` === conversation)
      : this.store.socialData.messages.some(m => m.id === messageId && `dm:${Math.min(m.from, m.to)}:${Math.max(m.from, m.to)}` === conversation);
    if (!found || !reason.trim() || reason.length > 500) fail(400, 'invalid_report', 'Choose a conversation message and a reason of 1..500 characters.');
    this.rate(`report:${account.id}`, 5);
    (this.state.reports ??= []).push({ at: Date.now(), from: account.id, conversation, messageId, reason: reason.trim() });
    await this.store.saveSocial();
  }
}

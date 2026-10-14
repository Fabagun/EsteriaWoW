import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { randomBytes } from 'node:crypto';
import { createConnection } from 'node:net';
import type { Socket } from 'node:net';
import { once } from 'node:events';

/** Tests the real isolated decoder over its authenticated pipe, without a game or launcher. */
export async function helperSelftest(executable: string, origin: string, token: string, attachmentId: string,
  expire: () => void, avatarId?: string, animatedId?: string): Promise<void> {
  const nonce = randomBytes(16).toString('hex');
  const child = spawn(executable, [String(process.pid), nonce, origin, '1'], { windowsHide: true, stdio: 'ignore' });
  let socket: Socket | undefined;
  for (let i = 0; i < 100; i++) {
    try {
      const next = createConnection(`\\\\.\\pipe\\EsteriaChat-${process.pid}-${nonce}`);
      await once(next, 'connect'); socket = next; break;
    } catch { await new Promise(resolve => setTimeout(resolve, 50)); }
  }
  assert.ok(socket, 'helper authenticated pipe starts');
  let buffered = Buffer.alloc(0);
  const inbox: Array<(data: Buffer) => void> = [];
  socket.on('data', data => {
    buffered = Buffer.concat([buffered, data]);
    while (buffered.length >= 8 && buffered.length >= 8 + buffered.readUInt32LE(4)) {
      assert.equal(buffered.readUInt32LE(0), 0x31484345);
      const size = buffered.readUInt32LE(4); assert.ok(size <= 2000000);
      const body = buffered.subarray(8, 8 + size); buffered = buffered.subarray(8 + size);
      inbox.shift()!(body);
    }
  });
  const send = async (visible: unknown[], ticket = token) => {
    const payload = Buffer.from(JSON.stringify({ ticket, visible }));
    const header = Buffer.alloc(8); header.writeUInt32LE(0x31484345); header.writeUInt32LE(payload.length, 4);
    const response = new Promise<Buffer>((resolve, reject) => {
      const timeout = setTimeout(() => reject(new Error('Helper response timed out')), 15000);
      inbox.push(data => { clearTimeout(timeout); resolve(data); });
    });
    socket!.write(Buffer.concat([header, payload]));
    const body = await response;
    let position = 4 + body.readUInt32LE(0);
    const count = body.readUInt32LE(position); position += 4;
    const frames: Array<{slot: number; state: number; pixels: Buffer}> = [];
    for (let i = 0; i < count; i++) {
      const slot = body.readUInt32LE(position), state = body.readUInt32LE(position + 4), size = body.readUInt32LE(position + 8); position += 20;
      frames.push({ slot, state, pixels: body.subarray(position, position + size) }); position += size;
    }
    assert.equal(position, body.length); return frames;
  };
  try {
    const visible = [{ slot: 1, id: attachmentId, animate: false }, ...(avatarId ? [{slot: 2, id: avatarId, animate: true}] : [])];
    const decoded = await send(visible);
    assert.equal(decoded[0]!.state, 1); assert.equal(decoded[0]!.pixels.length, 320 * 180 * 4);
    assert.ok(decoded[0]!.pixels.some(byte => byte !== 0), 'decoded pixels are nonblank');
    if (avatarId) { assert.equal(decoded[1]!.state, 1); assert.equal(decoded[1]!.pixels.length, 320 * 180 * 4); }
    const unchanged = await send(visible);
    assert.equal(unchanged[0]!.pixels.length, 0, 'unchanged frames do not consume IPC bandwidth');
    if (animatedId) {
      const first = await send([{slot: 3, id: animatedId, animate: true}]);
      assert.equal(first[0]!.state, 1);
      const images = new Set<string>([first[0]!.pixels.toString('base64')]);
      for (let i = 0; i < 8; i++) {
        await new Promise(resolve => setTimeout(resolve, 25));
        const next = await send([{slot: 3, id: animatedId, animate: true}]);
        if (next[0]!.pixels.length) images.add(next[0]!.pixels.toString('base64'));
      }
      assert.equal(images.size, 2, 'GIF frame delays produce both distinct decoded frames');
      await send([{slot: 3, id: animatedId, animate: false}]);
      assert.equal((await send([{slot: 3, id: animatedId, animate: false}]))[0]!.pixels.length, 0, 'autoplay off freezes GIF at the first frame');
    }
    assert.equal((await send([])).length, 0, 'hidden media produces no frames');
    const unauthorized = await send([{slot: 1, id: 'z'.repeat(32), animate: false}]);
    assert.equal(unauthorized[0]!.state, 0, 'unavailable media stays clear');
    expire();
    await send([]);
    // Existing bounded cache is checked against the actual server expiry; reauthorization is tested after its 15s lease.
    await new Promise(resolve => setTimeout(resolve, 15100));
    const expired = await send([{slot: 1, id: attachmentId, animate: false}]);
    assert.equal(expired[0]!.state, 2, 'expired media is a shared placeholder');
    console.log('helper IPC selftest passed: process-bound pipe, real decoding, frame suppression, hidden media, denial and expiry');
  } finally {
    socket.destroy();
    const exit = once(child, 'exit');
    await Promise.race([exit, new Promise(resolve => setTimeout(resolve, 3000))]);
    if (child.exitCode === null) child.kill();
    else assert.equal(child.exitCode, 0, 'helper exits cleanly when its game pipe closes');
  }
}

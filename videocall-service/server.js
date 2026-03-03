/**
 * dTelecom Token Service for Suite Clinica
 *
 * Lightweight Express server that uses the official dTelecom SDK
 * to generate access tokens and resolve the best SFU node via Solana.
 *
 * This runs internally (localhost:3100) and is called by the Flask backend.
 */

require('dotenv').config();
const express = require('express');
const cors = require('cors');
const { AccessToken, RoomServiceClient } = require('@dtelecom/server-sdk-js');

const app = express();
app.use(express.json());
app.use(cors({ origin: 'http://localhost:3000' }));

const PORT = process.env.VIDEOCALL_SERVICE_PORT || 3100;
const API_KEY = process.env.DTELECOM_API_KEY;
const API_SECRET = process.env.DTELECOM_API_SECRET;
const WEBHOOK_URL = process.env.DTELECOM_WEBHOOK_URL || '';

// ── Health check ─────────────────────────────────────────────────────────────
app.get('/health', (_req, res) => {
  res.json({ status: 'ok', configured: !!(API_KEY && API_SECRET) });
});

// ── Generate access token + resolve best SFU node ────────────────────────────
app.post('/token', async (req, res) => {
  try {
    const { roomName, identity, name, grants } = req.body;

    if (!roomName || !identity) {
      return res.status(400).json({ error: 'roomName and identity are required' });
    }
    if (!API_KEY || !API_SECRET) {
      return res.status(500).json({ error: 'DTELECOM_API_KEY and DTELECOM_API_SECRET not configured' });
    }

    const at = new AccessToken(API_KEY, API_SECRET, {
      identity,
      name: name || identity,
      ...(WEBHOOK_URL && { webHookURL: WEBHOOK_URL }),
    });

    at.addGrant({
      roomJoin: true,
      room: roomName,
      canPublish: grants?.canPublish !== false,
      canSubscribe: grants?.canSubscribe !== false,
      canPublishData: grants?.canPublishData !== false,
      ...(grants?.roomAdmin && { roomAdmin: true }),
      ...(grants?.roomCreate && { roomCreate: true }),
    });

    const token = at.toJwt();

    // Resolve the best SFU node based on client IP
    const clientIp = req.body.clientIp || req.ip || '127.0.0.1';
    const wsUrl = await at.getWsUrl(clientIp);

    res.json({ token, wsUrl });
  } catch (err) {
    console.error('[token] Error:', err.message);
    res.status(500).json({ error: err.message });
  }
});

// ── Create a room ────────────────────────────────────────────────────────────
app.post('/create-room', async (req, res) => {
  try {
    const { roomName, maxParticipants, emptyTimeout, metadata } = req.body;

    if (!API_KEY || !API_SECRET) {
      return res.status(500).json({ error: 'dTelecom not configured' });
    }

    const at = new AccessToken(API_KEY, API_SECRET, { identity: 'server' });
    const apiUrl = await at.getApiUrl();
    const client = new RoomServiceClient(apiUrl, API_KEY, API_SECRET);

    const room = await client.createRoom({
      name: roomName,
      emptyTimeout: emptyTimeout || 600,
      maxParticipants: maxParticipants || 10,
      ...(metadata && { metadata: JSON.stringify(metadata) }),
    });

    res.json({ room });
  } catch (err) {
    console.error('[create-room] Error:', err.message);
    res.status(500).json({ error: err.message });
  }
});

// ── List active rooms ────────────────────────────────────────────────────────
app.get('/rooms', async (_req, res) => {
  try {
    if (!API_KEY || !API_SECRET) {
      return res.status(500).json({ error: 'dTelecom not configured' });
    }

    const at = new AccessToken(API_KEY, API_SECRET, { identity: 'server' });
    const apiUrl = await at.getApiUrl();
    const client = new RoomServiceClient(apiUrl, API_KEY, API_SECRET);

    const rooms = await client.listRooms();
    res.json({ rooms });
  } catch (err) {
    console.error('[rooms] Error:', err.message);
    res.status(500).json({ error: err.message });
  }
});

// ── Remove participant from room ─────────────────────────────────────────────
app.post('/kick', async (req, res) => {
  try {
    const { roomName, identity } = req.body;

    const at = new AccessToken(API_KEY, API_SECRET, { identity: 'server' });
    const apiUrl = await at.getApiUrl();
    const client = new RoomServiceClient(apiUrl, API_KEY, API_SECRET);

    await client.removeParticipant(roomName, identity);
    res.json({ success: true });
  } catch (err) {
    console.error('[kick] Error:', err.message);
    res.status(500).json({ error: err.message });
  }
});

// ── Mute participant track ───────────────────────────────────────────────────
app.post('/mute', async (req, res) => {
  try {
    const { roomName, identity, trackSid, muted } = req.body;

    const at = new AccessToken(API_KEY, API_SECRET, { identity: 'server' });
    const apiUrl = await at.getApiUrl();
    const client = new RoomServiceClient(apiUrl, API_KEY, API_SECRET);

    await client.mutePublishedTrack(roomName, identity, trackSid, muted !== false);
    res.json({ success: true });
  } catch (err) {
    console.error('[mute] Error:', err.message);
    res.status(500).json({ error: err.message });
  }
});

// ─────────────────────────────────────────────────────────────────────────────
app.listen(PORT, () => {
  console.log(`🎥 dTelecom Token Service running on port ${PORT}`);
  console.log(`   API Key configured: ${!!API_KEY}`);
  console.log(`   Webhook URL: ${WEBHOOK_URL || '(none)'}`);
});

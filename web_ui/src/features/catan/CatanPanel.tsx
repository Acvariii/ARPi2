import React, { useCallback, useMemo, useRef } from 'react';
import { Box, Button, Chip, Paper, Stack, Typography } from '@mui/material';
import { alpha } from '@mui/material/styles';
import type { Snapshot } from '../../types';
import GameBanner from '../../components/GameBanner';

/* ──────────────────────────────────────────
   Catan — Warm earth-tone premium theme
   ────────────────────────────────────────── */

const CT_GOLD = '#f5b731';
const CT_AMBER = '#e09520';
const CT_DARK = '#12140e';
const CT_PANEL = '#1a1c14';
const CT_ACCENT = '#ffd740';
const CT_BORDER = '#4a3f28';

export default function CatanPanel(props: {
  snapshot: Snapshot;
  send: (obj: unknown) => void;
  seatLabel: (seat: number) => string;
}): React.ReactElement {
  const { snapshot, send, seatLabel } = props;
  const st = snapshot.catan;

  if (snapshot.server_state !== 'catan' || !st) return <></>;

  const mySeat = typeof snapshot.your_player_slot === 'number' ? snapshot.your_player_slot : null;
  const turnSeat = typeof st.current_turn_seat === 'number' ? st.current_turn_seat : null;
  const isMyTurn = typeof mySeat === 'number' && typeof turnSeat === 'number' && mySeat === turnSeat;

  const buttons = snapshot.panel_buttons || [];

  // Some games include Roll/End in panel_buttons; avoid showing multiple sets
  // by rendering actions in a single unified grid.

  const buttonEmoji = useCallback((id: string): string => {
    if (id === 'roll') return '🎲';
    if (id === 'end_turn') return '✅';
    if (id === 'build_road') return '🛣️';
    if (id === 'build_settlement') return '🏠';
    if (id === 'build_city') return '🏰';
    if (id === 'buy_dev') return '🃏';
    if (id === 'trade_bank') return '🏦';
    if (id === 'trade_player') return '🤝';
    if (id === 'trade_confirm') return '🤝';
    if (id === 'trade_cancel') return '↩️';
    if (id.startsWith('trade_give:') || id.startsWith('trade_get:')) return '🔁';
    if (id.startsWith('trade_to:')) return '👥';
    if (id.startsWith('p2p_give:') || id.startsWith('p2p_get:')) return '🔁';
    if (id === 'p2p_offer') return '📨';
    if (id === 'p2p_accept') return '✅';
    if (id === 'p2p_decline') return '❌';
    if (id.startsWith('play_dev:knight')) return '🦹';
    if (id.startsWith('play_dev:road_building')) return '🛣️';
    if (id.startsWith('play_dev:year_of_plenty')) return '🌾';
    if (id.startsWith('play_dev:monopoly')) return '💰';
    if (id.startsWith('discard:')) return '🗑️';
    if (id.startsWith('steal:')) return '🧤';
    if (id === 'skip_steal') return '⏭️';
    if (id === 'cancel_build') return '❌';
    return '✨';
  }, []);

  const buttonLabel = useCallback(
    (id: string, text: string): string => {
      const e = buttonEmoji(id);
      return `${e} ${text}`;
    },
    [buttonEmoji]
  );

  const sendClick = (id: string) => send({ type: 'click_button', id });

  const padRef = useRef<HTMLDivElement | null>(null);

  // Mobile/desktop input behavior:
  // - Coarse pointer (phones/tablets): drag to move the cursor; "Select" taps at last cursor location.
  // - Fine pointer (mouse): click directly on the pad to tap at that point; moving the mouse updates cursor.
  const isCoarsePointer = useMemo(() => {
    try {
      if (typeof window !== 'undefined' && typeof window.matchMedia === 'function') {
        return window.matchMedia('(pointer: coarse)').matches;
      }
    } catch {
      // ignore
    }
    try {
      return typeof navigator !== 'undefined' && (navigator as any).maxTouchPoints > 0;
    } catch {
      return false;
    }
  }, []);

  const lastCursorRef = useRef<{ x: number; y: number }>({ x: 0.5, y: 0.5 });
  const draggingRef = useRef<boolean>(false);

  const toPadCoords = useCallback((clientX: number, clientY: number) => {
    const el = padRef.current;
    if (!el) return null;
    const rect = el.getBoundingClientRect();
    const x = (clientX - rect.left) / Math.max(1, rect.width);
    const y = (clientY - rect.top) / Math.max(1, rect.height);
    const nx = Math.max(0, Math.min(1, x));
    const ny = Math.max(0, Math.min(1, y));
    return { x: nx, y: ny };
  }, []);

  const sendPointer = useCallback(
    (clientX: number, clientY: number) => {
      const p = toPadCoords(clientX, clientY);
      if (!p) return;
      lastCursorRef.current = p;
      send({ type: 'pointer', x: p.x, y: p.y, click: false });
    },
    [send, toPadCoords]
  );

  const sendTapAtLastCursor = useCallback(() => {
    const p = lastCursorRef.current || { x: 0.5, y: 0.5 };
    send({ type: 'tap', x: p.x, y: p.y, click: true });
  }, [send]);

  const sendTapAtPoint = useCallback(
    (clientX: number, clientY: number) => {
      const el = padRef.current;
      if (!el) return;
      const p = toPadCoords(clientX, clientY);
      if (!p) return;
      // Desktop behavior: click where you press.
      lastCursorRef.current = p;
      send({ type: 'tap', x: p.x, y: p.y, click: true });
    },
    [send, toPadCoords]
  );

  return (
    <Stack spacing={1.5} sx={{ animation: 'fadeInUp 0.4s ease-out' }}>
      <GameBanner game="catan" />

      {/* ──── HUD BAR ──── */}
      <Paper
        variant="outlined"
        sx={{
          p: 1.5,
          bgcolor: CT_PANEL,
          borderColor: alpha(CT_GOLD, 0.3),
          borderWidth: 2,
          position: 'relative',
          overflow: 'hidden',
          animation: 'fadeInUp 0.4s ease-out',
          '&::before': {
            content: '""',
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            height: 3,
            background: `linear-gradient(90deg, ${CT_AMBER}, ${CT_GOLD}, ${CT_ACCENT})`,
          },
        }}
      >
        <Stack spacing={1.25}>
          {/* Turn & phase */}
          <Stack direction="row" spacing={1} justifyContent="center" flexWrap="wrap" useFlexGap>
            <Chip
              label={`🎯 ${typeof turnSeat === 'number' ? seatLabel(turnSeat) : '—'}`}
              size="small"
              sx={{
                bgcolor: isMyTurn ? alpha(CT_GOLD, 0.25) : alpha(CT_BORDER, 0.5),
                color: isMyTurn ? CT_ACCENT : '#ccc',
                fontWeight: 700,
                border: isMyTurn ? `1px solid ${CT_GOLD}` : 'none',
                animation: isMyTurn ? 'pulse 1.5s ease-in-out infinite' : 'none',
              }}
            />
            <Chip
              label={`📋 ${st.phase || '—'}`}
              size="small"
              sx={{ bgcolor: alpha(CT_BORDER, 0.5), color: '#bbb', fontWeight: 600 }}
            />
            {typeof st.last_roll === 'number' && (
              <Chip
                label={`🎲 ${st.last_roll}`}
                size="small"
                sx={{
                  bgcolor: st.last_roll === 7 ? '#c62828' : alpha(CT_GOLD, 0.3),
                  color: '#fff',
                  fontWeight: 900,
                  fontSize: '0.85rem',
                  height: 24,
                  animation: st.last_roll === 7 ? 'blink 0.6s ease-in-out 3' : 'badgePop 0.35s ease-out',
                }}
              />
            )}
          </Stack>

          {/* VP + award badges */}
          <Stack direction="row" spacing={0.75} justifyContent="center" flexWrap="wrap" useFlexGap>
            {typeof st.vp === 'number' && (
              <Chip
                label={`⭐ ${st.vp} VP`}
                size="small"
                sx={{
                  bgcolor: alpha(CT_GOLD, 0.35),
                  color: '#fff',
                  fontWeight: 900,
                  height: 24,
                  border: `1px solid ${alpha(CT_GOLD, 0.5)}`,
                  animation: 'badgePop 0.35s ease-out',
                }}
              />
            )}
            {typeof st.knights_played === 'number' && st.knights_played > 0 && (
              <Chip label={`⚔️ ${st.knights_played}`} size="small" sx={{ bgcolor: alpha('#7b1fa2', 0.3), color: '#ddd', fontWeight: 700, height: 22 }} />
            )}
            {typeof st.largest_army_holder === 'number' && st.largest_army_holder === mySeat && (
              <Chip label="⚔️ Army" size="small" sx={{ bgcolor: '#7b1fa2', color: '#fff', fontWeight: 700, height: 22, animation: 'winnerShimmer 2s linear infinite' }} />
            )}
            {typeof st.longest_road_holder === 'number' && st.longest_road_holder === mySeat && (
              <Chip label="🛣️ Road" size="small" sx={{ bgcolor: '#1565c0', color: '#fff', fontWeight: 700, height: 22, animation: 'winnerShimmer 2s linear infinite' }} />
            )}
          </Stack>

          {/* Resources */}
          {st.your_resources ? (
            <Stack direction="row" spacing={0.5} justifyContent="center" flexWrap="wrap" useFlexGap>
              {([
                ['wood', '🌲', '#2e7d32', '#c8e6c9'],
                ['brick', '🧱', '#bf360c', '#ffccbc'],
                ['sheep', '🐑', '#558b2f', '#dcedc8'],
                ['wheat', '🌾', '#e8a317', '#fff9c4'],
                ['ore', '⛰️', '#455a64', '#cfd8dc'],
              ] as [string, string, string, string][]).map(([res, em, bg, fg], i) => (
                <Chip
                  key={res}
                  label={`${em} ${st.your_resources![res] ?? 0}`}
                  size="small"
                  sx={{
                    bgcolor: alpha(bg, 0.6),
                    color: fg,
                    fontWeight: 700,
                    fontSize: '0.8rem',
                    height: 26,
                    minWidth: 48,
                    border: `1px solid ${alpha(bg, 0.3)}`,
                    animation: `badgePop 0.3s ease-out ${i * 0.05}s both`,
                  }}
                />
              ))}
            </Stack>
          ) : null}

          {st.last_event ? (
            <Typography
              variant="caption"
              display="block"
              align="center"
              sx={{
                mt: 0.5,
                color: alpha(CT_ACCENT, 0.8),
                animation: 'slideInRight 0.4s ease-out',
                fontStyle: 'italic',
              }}
            >
              📢 {st.last_event}
            </Typography>
          ) : null}
        </Stack>
      </Paper>

      {/* ──── ACTIONS ──── */}
      <Paper
        variant="outlined"
        sx={{
          p: 1.25,
          bgcolor: CT_PANEL,
          borderColor: alpha(CT_BORDER, 0.6),
          borderWidth: 1,
        }}
      >
        <Typography variant="subtitle2" sx={{ color: CT_GOLD, mb: 0.75, fontWeight: 700 }}>
          ⚔️ Actions
        </Typography>
        {buttons.length > 0 ? (
          <Box
            sx={{
              display: 'grid',
              gridTemplateColumns: { xs: 'repeat(2, 1fr)', sm: 'repeat(3, 1fr)' },
              gap: 0.75,
            }}
          >
            {buttons.map((b, bIdx) => {
              const isPrimary = b.id === 'roll';
              const isEnd = b.id === 'end_turn';
              return (
                <Button
                  key={b.id}
                  variant={isPrimary ? 'contained' : 'outlined'}
                  onClick={() => sendClick(b.id)}
                  disabled={!b.enabled || !!snapshot.popup?.active || (b.id === 'roll' && !isMyTurn) || (b.id === 'end_turn' && !isMyTurn)}
                  sx={{
                    minHeight: { xs: 48, sm: 40 },
                    fontSize: { xs: 14, sm: 13 },
                    gridColumn: isPrimary || isEnd ? { xs: 'span 2', sm: 'span 3' } : undefined,
                    bgcolor: isPrimary ? CT_GOLD : 'transparent',
                    color: isPrimary ? CT_DARK : alpha(CT_ACCENT, 0.85),
                    borderColor: isPrimary ? CT_GOLD : alpha(CT_BORDER, 0.6),
                    fontWeight: isPrimary ? 900 : 600,
                    '&:hover': {
                      bgcolor: isPrimary ? CT_AMBER : alpha(CT_GOLD, 0.1),
                      borderColor: CT_GOLD,
                    },
                    '&.Mui-disabled': {
                      color: alpha('#888', 0.5),
                      borderColor: alpha(CT_BORDER, 0.3),
                    },
                    animation: `bounceIn 0.4s ease-out ${bIdx * 0.04}s both`,
                  }}
                >
                  {buttonLabel(b.id, b.text)}
                </Button>
              );
            })}
          </Box>
        ) : (
          <Typography variant="body2" sx={{ color: '#888' }}>
            No actions available.
          </Typography>
        )}
      </Paper>

      {/* ──── MAP / POINTER PAD ──── */}
      <Paper
        variant="outlined"
        sx={{
          p: 1.25,
          bgcolor: CT_PANEL,
          borderColor: alpha(CT_BORDER, 0.6),
          borderWidth: 1,
        }}
      >
        <Typography variant="subtitle2" sx={{ color: CT_GOLD, mb: 0.75, fontWeight: 700 }}>
          🗺️ Board
        </Typography>
        <Stack direction="row" spacing={1} sx={{ mb: 0.75 }}>
          <Typography variant="caption" sx={{ color: '#999' }}>
            Tiles: {Array.isArray(st.tiles) ? st.tiles.length : 0}
          </Typography>
          <Typography variant="caption" sx={{ color: '#999' }}>
            Ports: {Array.isArray((st as any).ports) ? ((st as any).ports as any[]).length : 0}
          </Typography>
        </Stack>
        {isCoarsePointer ? (
          <Stack direction="row" spacing={1} sx={{ mb: 1 }}>
            <Button
              variant="contained"
              onClick={sendTapAtLastCursor}
              disabled={!!snapshot.popup?.active}
              sx={{
                minHeight: 44,
                flex: 1,
                bgcolor: CT_GOLD,
                color: CT_DARK,
                fontWeight: 800,
                '&:hover': { bgcolor: CT_AMBER },
              }}
            >
              👆 Select (tap)
            </Button>
          </Stack>
        ) : null}
        <Box
          ref={padRef}
          onPointerMove={(e) => {
            if (snapshot.popup?.active) return;
            if (isCoarsePointer && !draggingRef.current) return;
            sendPointer(e.clientX, e.clientY);
          }}
          onPointerDown={(e) => {
            if (snapshot.popup?.active) return;
            try {
              (e.currentTarget as any).setPointerCapture?.(e.pointerId);
            } catch {
              // ignore
            }
            if (isCoarsePointer) {
              draggingRef.current = true;
              return;
            }
            sendTapAtPoint(e.clientX, e.clientY);
          }}
          onPointerUp={() => {
            draggingRef.current = false;
          }}
          onPointerCancel={() => {
            draggingRef.current = false;
          }}
          sx={{
            height: { xs: 240, sm: 180 },
            borderRadius: 1,
            border: `1px solid ${alpha(CT_BORDER, 0.5)}`,
            bgcolor: alpha(CT_DARK, 0.6),
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            userSelect: 'none',
            touchAction: 'none',
          }}
        >
          <Typography variant="body2" align="center" sx={{ px: 2, color: alpha('#ccc', 0.6) }}>
            {isCoarsePointer
              ? 'Drag here to move the cursor. Use Select to tap.'
              : 'Move/click here to tap on the board.'}
            <br />
            Settlements go on intersections (not hex centers).
          </Typography>
        </Box>
      </Paper>

      {/* ──── PRICES REFERENCE ──── */}
      <Paper
        variant="outlined"
        sx={{
          p: 1.25,
          bgcolor: CT_PANEL,
          borderColor: alpha(CT_BORDER, 0.4),
          borderWidth: 1,
        }}
      >
        <Typography variant="subtitle2" sx={{ color: CT_GOLD, mb: 0.5, fontWeight: 700 }}>
          💰 Costs
        </Typography>
        {([
          ['🛣️ Road', '🌲1 + 🧱1'],
          ['🏠 Settlement', '🌲1 + 🧱1 + 🐑1 + 🌾1'],
          ['🏰 City', '⛰️3 + 🌾2'],
          ['🃏 Dev Card', '🐑1 + 🌾1 + ⛰️1'],
        ] as [string, string][]).map(([name, cost]) => (
          <Stack key={name} direction="row" justifyContent="space-between" sx={{ px: 0.5 }}>
            <Typography variant="caption" sx={{ color: '#ccc', fontWeight: 600 }}>{name}</Typography>
            <Typography variant="caption" sx={{ color: alpha(CT_ACCENT, 0.7) }}>{cost}</Typography>
          </Stack>
        ))}
      </Paper>
    </Stack>
  );
}

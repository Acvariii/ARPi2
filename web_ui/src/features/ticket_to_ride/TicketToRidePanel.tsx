import React, { useCallback, useMemo } from 'react';
import { Box, Button, Chip, Paper, Stack, Typography } from '@mui/material';
import type { Snapshot } from '../../types';
import GameBanner from '../../components/GameBanner';

/* ── Color helpers ─────────────────────────────────────────── */
const CARD_COLORS: Record<string, string> = {
  red: '#c62828',
  orange: '#e65100',
  yellow: '#f9a825',
  green: '#2e7d32',
  blue: '#1565c0',
  purple: '#6a1b9a',
  black: '#37474f',
  white: '#cfd8dc',
  gray: '#78909c',
  locomotive: '#fdd835',
};

const CARD_EMOJI: Record<string, string> = {
  red: '🔴',
  orange: '🟠',
  yellow: '🟡',
  green: '🟢',
  blue: '🔵',
  purple: '🟣',
  black: '⚫',
  white: '⚪',
  locomotive: '🚂',
};

export default function TicketToRidePanel(props: {
  snapshot: Snapshot;
  send: (obj: unknown) => void;
  seatLabel: (seat: number) => string;
}): React.ReactElement {
  const { snapshot, send, seatLabel } = props;
  const st = (snapshot as any).ticket_to_ride;

  if (snapshot.server_state !== 'ticket_to_ride' || !st) return <></>;

  const mySeat = typeof snapshot.your_player_slot === 'number' ? snapshot.your_player_slot : null;
  const turnSeat = typeof st.current_turn_seat === 'number' ? st.current_turn_seat : null;
  const isMyTurn = typeof mySeat === 'number' && typeof turnSeat === 'number' && mySeat === turnSeat;
  const buttons: Array<{ id: string; text: string; enabled: boolean }> = snapshot.panel_buttons || [];
  const phase: string = st.phase || '';
  const winner = typeof st.winner === 'number' ? st.winner : null;

  const sendClick = useCallback((id: string) => send({ type: 'click_button', id }), [send]);

  /* ── Hand cards grouped ─────────────────────────────────── */
  const handCounts: Record<string, number> = useMemo(() => {
    const counts: Record<string, number> = {};
    if (st.hand_counts && typeof st.hand_counts === 'object') {
      for (const [k, v] of Object.entries(st.hand_counts)) {
        counts[k] = typeof v === 'number' ? v : 0;
      }
    }
    return counts;
  }, [st.hand_counts]);

  const totalCards = useMemo(() => Object.values(handCounts).reduce((a, b) => a + b, 0), [handCounts]);

  /* ── Tickets ────────────────────────────────────────────── */
  const myTickets: Array<{ city_a: string; city_b: string; points: number; complete: boolean }> = st.my_tickets || [];
  const pendingTickets: Array<{ city_a: string; city_b: string; points: number }> = st.pending_tickets || [];

  /* ── Face-up cards ──────────────────────────────────────── */
  const faceUp: string[] = st.face_up || [];

  /* ── Player summaries ───────────────────────────────────── */
  const players: Array<{
    seat: number;
    hand_count: number;
    ticket_count: number;
    trains_left: number;
    score: number;
    routes_claimed: number;
  }> = st.players || [];

  /* ── Phase label ────────────────────────────────────────── */
  const phaseLabel = (p: string) => {
    switch (p) {
      case 'play': return 'Main Turn';
      case 'draw_second': return 'Draw 2nd Card';
      case 'pick_tickets': return 'Pick Tickets';
      case 'last_round': return '🔔 Last Round!';
      case 'game_over': return '🏁 Game Over';
      default: return p;
    }
  };

  /* ── Button emoji ───────────────────────────────────────── */
  const btnEmoji = (id: string): string => {
    if (id.startsWith('draw_face_up_')) return CARD_EMOJI[id.replace('draw_face_up_', '')] || '🎴';
    if (id === 'draw_deck') return '🃏';
    if (id === 'draw_tickets') return '🎫';
    if (id === 'end_turn') return '✅';
    if (id.startsWith('claim_')) return '🚂';
    if (id.startsWith('keep_ticket_')) return '✅';
    if (id === 'done_picking_tickets') return '📋';
    return '✨';
  };

  return (
    <Stack spacing={1.25} sx={{ animation: 'fadeInUp 0.4s ease-out' }}>
      <GameBanner game="ticket_to_ride" />

      {/* ── Status bar ───────────────────────────────────── */}
      <Paper variant="outlined" sx={{ p: 1.25 }}>
        <Stack direction="row" spacing={1} justifyContent="center" flexWrap="wrap" useFlexGap sx={{ mb: 0.75 }}>
          <Typography variant="body2" color="text.secondary">
            Turn: {typeof turnSeat === 'number' ? seatLabel(turnSeat) : '—'}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Phase: {phaseLabel(phase)}
          </Typography>
        </Stack>

        {/* Winner chip */}
        {winner !== null && (
          <Stack direction="row" justifyContent="center" sx={{ mb: 0.5 }}>
            <Chip
              label={`🏆 Winner: ${seatLabel(winner)}`}
              sx={{
                bgcolor: '#f9a825', color: '#000', fontWeight: 900,
                fontSize: '0.95rem', height: 28,
                animation: 'winnerShimmer 2s linear infinite',
              }}
            />
          </Stack>
        )}

        {/* My score + trains */}
        {mySeat !== null && (
          <Stack direction="row" spacing={0.75} justifyContent="center" flexWrap="wrap" useFlexGap sx={{ mb: 0.5 }}>
            <Chip
              label={`⭐ ${st.scores?.[mySeat] ?? 0} pts`} size="small"
              sx={{ bgcolor: '#1565c0', color: '#fff', fontWeight: 700, height: 22, animation: 'badgePop 0.35s ease-out' }}
            />
            {players.find(p => p.seat === mySeat) && (
              <Chip
                label={`🚂 ${players.find(p => p.seat === mySeat)!.trains_left} trains`} size="small"
                sx={{ bgcolor: '#37474f', color: '#fff', fontWeight: 700, height: 22, animation: 'badgePop 0.35s ease-out 0.05s both' }}
              />
            )}
            <Chip
              label={`🃏 ${totalCards} cards`} size="small"
              sx={{ bgcolor: '#4527a0', color: '#fff', fontWeight: 700, height: 22, animation: 'badgePop 0.35s ease-out 0.1s both' }}
            />
          </Stack>
        )}

        {/* Last event */}
        {st.last_event ? (
          <Typography variant="caption" color="text.secondary" display="block" align="center" sx={{ mt: 0.5, animation: 'slideInRight 0.4s ease-out' }}>
            📢 {st.last_event}
          </Typography>
        ) : null}
      </Paper>

      {/* ── Hand cards ───────────────────────────────────── */}
      <Paper variant="outlined" sx={{ p: 1.25 }}>
        <Typography variant="subtitle1" gutterBottom>🃏 My Hand</Typography>
        <Stack direction="row" spacing={0.75} justifyContent="center" flexWrap="wrap" useFlexGap>
          {Object.entries(handCounts)
            .filter(([, v]) => v > 0)
            .sort(([a], [b]) => a.localeCompare(b))
            .map(([color, count], i) => (
              <Chip
                key={color}
                label={`${CARD_EMOJI[color] ?? '🎴'} ${color} × ${count}`}
                size="small"
                sx={{
                  bgcolor: CARD_COLORS[color] ?? '#546e7a',
                  color: color === 'yellow' || color === 'white' || color === 'locomotive' ? '#000' : '#fff',
                  fontWeight: 700, fontSize: '0.8rem', height: 24, minWidth: 60,
                  animation: `badgePop 0.3s ease-out ${i * 0.05}s both`,
                }}
              />
            ))}
          {totalCards === 0 && (
            <Typography variant="body2" color="text.secondary">No cards in hand.</Typography>
          )}
        </Stack>
      </Paper>

      {/* ── Face-up cards ────────────────────────────────── */}
      <Paper variant="outlined" sx={{ p: 1.25 }}>
        <Typography variant="subtitle1" gutterBottom>🎴 Face-Up Cards</Typography>
        <Stack direction="row" spacing={0.75} justifyContent="center" flexWrap="wrap" useFlexGap>
          {faceUp.map((c, i) => (
            <Chip
              key={i}
              label={`${CARD_EMOJI[c] ?? '🎴'} ${c}`}
              size="small"
              sx={{
                bgcolor: CARD_COLORS[c] ?? '#546e7a',
                color: c === 'yellow' || c === 'white' || c === 'locomotive' ? '#000' : '#fff',
                fontWeight: 700, fontSize: '0.8rem', height: 24, minWidth: 44,
                animation: `badgePop 0.3s ease-out ${i * 0.06}s both`,
              }}
            />
          ))}
        </Stack>
        <Stack direction="row" spacing={1} justifyContent="center" sx={{ mt: 0.75 }}>
          <Typography variant="caption" color="text.secondary">
            🃏 Draw pile: {st.draw_pile_count ?? 0}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            🎫 Ticket pile: {st.ticket_pile_count ?? 0}
          </Typography>
        </Stack>
      </Paper>

      {/* ── Pending ticket selection ─────────────────────── */}
      {pendingTickets.length > 0 && (
        <Paper variant="outlined" sx={{ p: 1.25, borderColor: 'warning.main' }}>
          <Typography variant="subtitle1" gutterBottom>🎫 Choose Tickets</Typography>
          <Stack spacing={0.5}>
            {pendingTickets.map((t, i) => {
              const keepId = `keep_ticket_${i}`;
              const btn = buttons.find(b => b.id === keepId);
              const isKept = btn ? btn.text.toLowerCase().includes('✅') || btn.text.toLowerCase().includes('keep') : false;
              return (
                <Stack key={i} direction="row" spacing={1} alignItems="center">
                  <Typography variant="body2" sx={{ flex: 1 }}>
                    {t.city_a} → {t.city_b} ({t.points} pts)
                  </Typography>
                  {btn && (
                    <Button
                      size="small"
                      variant={isKept ? 'contained' : 'outlined'}
                      onClick={() => sendClick(keepId)}
                      disabled={!btn.enabled || !!snapshot.popup?.active}
                      sx={{ minWidth: 60, animation: `bounceIn 0.3s ease-out ${i * 0.08}s both` }}
                    >
                      {btn.text}
                    </Button>
                  )}
                </Stack>
              );
            })}
          </Stack>
          {buttons.find(b => b.id === 'done_picking_tickets') && (
            <Button
              variant="contained"
              fullWidth
              onClick={() => sendClick('done_picking_tickets')}
              disabled={!buttons.find(b => b.id === 'done_picking_tickets')!.enabled || !!snapshot.popup?.active}
              sx={{ mt: 1, animation: 'bounceIn 0.4s ease-out' }}
            >
              📋 Done Picking Tickets
            </Button>
          )}
        </Paper>
      )}

      {/* ── My Tickets ───────────────────────────────────── */}
      {myTickets.length > 0 && (
        <Paper variant="outlined" sx={{ p: 1.25 }}>
          <Typography variant="subtitle1" gutterBottom>🎫 My Destination Tickets</Typography>
          <Stack spacing={0.5}>
            {myTickets.map((t, i) => (
              <Stack key={i} direction="row" spacing={1} alignItems="center">
                <Chip
                  label={t.complete ? '✅' : '⏳'}
                  size="small"
                  sx={{
                    bgcolor: t.complete ? '#2e7d32' : '#37474f',
                    color: '#fff', fontWeight: 700, width: 36, height: 22,
                  }}
                />
                <Typography variant="body2" sx={{ flex: 1 }}>
                  {t.city_a} → {t.city_b}
                </Typography>
                <Chip
                  label={`${t.points} pts`}
                  size="small"
                  sx={{ bgcolor: t.complete ? '#1b5e20' : '#b71c1c', color: '#fff', fontWeight: 700, fontSize: '0.75rem', height: 20 }}
                />
              </Stack>
            ))}
          </Stack>
        </Paper>
      )}

      {/* ── Actions ──────────────────────────────────────── */}
      <Paper variant="outlined" sx={{ p: 1.25 }}>
        <Typography variant="subtitle1" gutterBottom>Actions</Typography>
        {buttons.length > 0 ? (
          <Box sx={{ display: 'grid', gridTemplateColumns: { xs: 'repeat(2, 1fr)', sm: 'repeat(3, 1fr)' }, gap: 1 }}>
            {buttons
              .filter(b => !b.id.startsWith('keep_ticket_') && b.id !== 'done_picking_tickets')
              .map((b, bIdx) => (
                <Button
                  key={b.id}
                  variant={b.id.startsWith('claim_') ? 'contained' : 'outlined'}
                  onClick={() => sendClick(b.id)}
                  disabled={!b.enabled || !!snapshot.popup?.active}
                  sx={{
                    minHeight: { xs: 48, sm: 40 },
                    fontSize: { xs: 14, sm: 13 },
                    gridColumn: b.id === 'draw_deck' || b.id === 'draw_tickets' || b.id === 'end_turn'
                      ? { xs: 'span 2', sm: 'span 3' } : undefined,
                    animation: `bounceIn 0.4s ease-out ${bIdx * 0.05}s both`,
                  }}
                >
                  {btnEmoji(b.id)} {b.text}
                </Button>
              ))}
          </Box>
        ) : (
          <Typography variant="body2" color="text.secondary">
            {isMyTurn ? 'No actions available.' : 'Waiting for your turn…'}
          </Typography>
        )}
      </Paper>

      {/* ── Players ──────────────────────────────────────── */}
      <Paper variant="outlined" sx={{ p: 1.25 }}>
        <Typography variant="subtitle1" gutterBottom>👥 Players</Typography>
        <Stack spacing={0.5}>
          {players.map((p, i) => {
            const isCurrent = p.seat === turnSeat;
            const isMe = p.seat === mySeat;
            return (
              <Stack
                key={p.seat}
                direction="row"
                spacing={1}
                alignItems="center"
                sx={{
                  p: 0.5, borderRadius: 1,
                  bgcolor: isCurrent ? 'action.hover' : 'transparent',
                  border: isMe ? '1px solid' : 'none',
                  borderColor: 'primary.main',
                  animation: `fadeInUp 0.3s ease-out ${i * 0.06}s both`,
                }}
              >
                <Typography variant="body2" sx={{ fontWeight: isCurrent ? 700 : 400, flex: 1 }}>
                  {isCurrent ? '▶ ' : ''}{seatLabel(p.seat)}
                </Typography>
                <Chip label={`⭐ ${p.score}`} size="small" sx={{ height: 20, fontWeight: 700 }} />
                <Chip label={`🚂 ${p.trains_left}`} size="small" variant="outlined" sx={{ height: 20 }} />
                <Chip label={`📍 ${p.routes_claimed}`} size="small" variant="outlined" sx={{ height: 20 }} />
              </Stack>
            );
          })}
        </Stack>
      </Paper>

      {/* ── Scoring reference ────────────────────────────── */}
      <Paper variant="outlined" sx={{ p: 1.25 }}>
        <Typography variant="subtitle1" gutterBottom>📊 Route Scoring</Typography>
        <Stack direction="row" spacing={0.75} justifyContent="center" flexWrap="wrap" useFlexGap>
          {[
            [1, 1], [2, 2], [3, 4], [4, 7], [5, 10], [6, 15],
          ].map(([len, pts]) => (
            <Chip key={len} label={`${len}→${pts}`} size="small" variant="outlined" sx={{ fontSize: '0.75rem', height: 20 }} />
          ))}
        </Stack>
      </Paper>
    </Stack>
  );
}

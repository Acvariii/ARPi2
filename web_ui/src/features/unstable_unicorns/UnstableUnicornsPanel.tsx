import React, { useMemo } from 'react';
import { Box, Button, Chip, Divider, LinearProgress, Paper, Stack, Typography } from '@mui/material';
import { alpha } from '@mui/material/styles';
import type { Snapshot } from '../../types';
import EmojiCardTile from '../../components/EmojiCardTile';
import GameBanner from '../../components/GameBanner';

/* ──────────────────────────────────────────
   Unstable Unicorns — EK-quality premium UI
   ────────────────────────────────────────── */

const UU_PURPLE = '#9c27b0';
const UU_PINK = '#e040fb';
const UU_DARK = '#0e0816';
const UU_PANEL = '#1a1028';
const UU_ACCENT = '#ce93d8';
const UU_GOLD = '#ffd740';

type Props = {
  snapshot: Snapshot;
  seatLabel: (seat: number) => string;
  send: (obj: unknown) => void;
  playerColors: string[];
};

type CardSummary = {
  id: string;
  name: string;
  kind: string;
  emoji?: string;
  color?: string;
  desc?: string;
  playable?: boolean;
  idx?: number;
};

export default function UnstableUnicornsPanel({ snapshot, seatLabel, send, playerColors }: Props): React.ReactElement {
  if (snapshot.server_state !== 'unstable_unicorns' || !snapshot.unstable_unicorns) return <></>;

  const uu = snapshot.unstable_unicorns;
  const mySeat = typeof snapshot.your_player_slot === 'number' ? snapshot.your_player_slot : null;

  const panelButtons = snapshot.panel_buttons || [];
  const buttonById = new Map(panelButtons.map((b) => [b.id, b] as const));

  const sendClick = (id: string) => send({ type: 'click_button', id });

  const turnSeat = typeof uu.current_turn_seat === 'number' ? uu.current_turn_seat : null;
  const goal = typeof uu.goal_unicorns === 'number' ? uu.goal_unicorns : 7;

  const myHand = Array.isArray(uu.your_hand) ? (uu.your_hand as CardSummary[]) : [];
  const stables = (uu.stables || {}) as Record<string, CardSummary[]>;
  const protectedTurns = (uu.protected_turns || {}) as Record<string, number>;
  const handCounts = (uu.hand_counts || {}) as Record<string, number>;
  const revealedHands = (uu.revealed_hands || {}) as Record<string, CardSummary[]>;
  const lastEvent = (uu.last_event as string) || '';

  const activePlayers = useMemo(() => {
    const a = Array.isArray(uu.active_players) ? (uu.active_players as number[]) : [];
    return a.filter((s) => typeof s === 'number');
  }, [uu.active_players]);

  const winner = typeof uu.winner === 'number' ? uu.winner : null;

  const reaction = uu.reaction as any;
  const prompt = uu.prompt as any;

  const discardButtons = panelButtons.filter((b) => b.id.startsWith('uu_discard:'));
  const isDiscardPhase = uu.turn_phase === 'discard';

  const actionButtons = panelButtons.filter(
    (b) => !b.id.startsWith('uu_play:') && !b.id.startsWith('uu_discard:')
  );

  const deckCount = typeof uu.deck_count === 'number' ? uu.deck_count : 0;
  const discardCount = typeof uu.discard_count === 'number' ? uu.discard_count : 0;
  const turnPhase = typeof uu.turn_phase === 'string' ? uu.turn_phase : '';

  return (
    <>
      <GameBanner game="unstable_unicorns" />

      {/* ── HUD Panel ── */}
      <Paper
        variant="outlined"
        sx={{
          p: 1.5, mb: 2,
          bgcolor: UU_PANEL,
          borderColor: alpha(UU_PURPLE, 0.5),
          borderWidth: 2,
          position: 'relative',
          overflow: 'hidden',
          animation: 'fadeInUp 0.4s ease-out',
          '&::before': {
            content: '""', position: 'absolute', top: 0, left: 0, right: 0, height: '3px',
            background: `linear-gradient(90deg, ${UU_PURPLE}, ${UU_PINK}, ${UU_ACCENT})`,
          },
        }}
      >
        <Stack spacing={1}>
          <Stack direction="row" justifyContent="center" spacing={1} flexWrap="wrap" useFlexGap>
            {/* Deck chip */}
            <Chip
              size="small"
              label={`🃏 Deck: ${deckCount}`}
              sx={{
                fontWeight: 700,
                bgcolor: deckCount <= 3 ? alpha('#ef5350', 0.15) : alpha(UU_PURPLE, 0.12),
                color: deckCount <= 3 ? '#ef5350' : UU_ACCENT,
                borderColor: deckCount <= 3 ? '#ef5350' : alpha(UU_PURPLE, 0.4),
                border: '1px solid',
                ...(deckCount <= 3 && { animation: 'blink 1s ease-in-out infinite' }),
              }}
            />
            {/* Discard chip */}
            <Chip
              size="small"
              label={`♻ Discard: ${discardCount}`}
              sx={{
                fontWeight: 600,
                bgcolor: alpha(UU_PURPLE, 0.08),
                color: '#b0a0c0',
              }}
            />
            {/* Goal chip */}
            <Chip
              size="small"
              label={`🦄 Goal: ${goal}`}
              sx={{
                fontWeight: 700,
                bgcolor: alpha(UU_GOLD, 0.12),
                color: UU_GOLD,
                border: `1px solid ${alpha(UU_GOLD, 0.3)}`,
              }}
            />
          </Stack>

          {/* Turn indicator */}
          {turnSeat !== null && (
            <Typography
              variant="body2"
              align="center"
              sx={{
                fontWeight: 800,
                color: UU_GOLD,
                textShadow: `0 0 8px ${alpha(UU_GOLD, 0.4)}`,
              }}
            >
              🦄 {seatLabel(turnSeat)}&apos;s Turn · Phase: {turnPhase || '—'}
            </Typography>
          )}

          {/* Winner display */}
          {winner !== null && (
            <Paper
              sx={{
                p: 1.5,
                background: `linear-gradient(135deg, ${alpha(UU_PURPLE, 0.3)}, ${alpha(UU_PINK, 0.2)})`,
                border: `2px solid ${UU_GOLD}`,
                borderRadius: 2,
                textAlign: 'center',
              }}
            >
              <Typography
                variant="h6"
                sx={{
                  fontWeight: 900,
                  background: `linear-gradient(90deg, ${UU_GOLD}, ${UU_PINK}, ${UU_GOLD})`,
                  backgroundSize: '200% 100%',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent',
                  animation: 'winnerShimmer 2s linear infinite',
                }}
              >
                🏆 {seatLabel(winner)} — UNICORN CHAMPION! 🏆
              </Typography>
            </Paper>
          )}

          {/* Neigh reaction window */}
          {!!reaction && (
            <Paper
              sx={{
                p: 1.5,
                bgcolor: alpha('#ef5350', 0.08),
                border: `2px solid #ef5350`,
                borderRadius: 2,
                animation: 'nopeFlash 1.2s ease-in-out infinite',
              }}
            >
              <Typography variant="body2" sx={{ fontWeight: 800, color: '#ef5350' }} align="center">
                🚫 NEIGH WINDOW — awaiting {Array.isArray(reaction.awaiting_seats) ? (reaction.awaiting_seats as number[]).map((s: number) => seatLabel(s)).join(', ') : '—'}
              </Typography>
              {reaction.card && (
                <Typography variant="caption" color="text.secondary" align="center" sx={{ display: 'block', mt: 0.5 }}>
                  Card: {reaction.card.emoji || ''} {reaction.card.name || ''}
                </Typography>
              )}
              {Array.isArray(reaction.stack) && reaction.stack.length > 0 && (
                <Typography variant="caption" sx={{ fontWeight: 600, color: '#ef5350' }} align="center" display="block">
                  Neigh stack: {reaction.stack.length}
                </Typography>
              )}
            </Paper>
          )}

          {/* Last event toast */}
          {!!lastEvent && (
            <Paper
              sx={{
                py: 0.5, px: 1.5,
                bgcolor: alpha(UU_ACCENT, 0.08),
                borderLeft: `3px solid ${UU_ACCENT}`,
                animation: 'slideInRight 0.4s ease-out',
              }}
            >
              <Typography variant="caption" sx={{ fontWeight: 600, color: UU_ACCENT }}>
                ⚡ {lastEvent}
              </Typography>
            </Paper>
          )}

          {/* Prompt info */}
          {!!prompt && (
            <Typography variant="body2" sx={{ fontWeight: 800, color: UU_PINK, animation: 'slideInRight 0.4s ease-out' }} align="center">
              🎯 Choose a target in the action buttons below.
            </Typography>
          )}
        </Stack>
      </Paper>

      {/* ── Actions ── */}
      <Typography variant="subtitle2" gutterBottom align="center" sx={{ color: UU_ACCENT, fontWeight: 700, letterSpacing: 1 }}>
        ACTIONS
      </Typography>

      {isDiscardPhase && !!discardButtons.length && (
        <Paper
          sx={{
            p: 1.25, mb: 2,
            bgcolor: alpha('#ef5350', 0.06),
            border: `2px solid #ef5350`,
            borderRadius: 2,
          }}
        >
          <Typography variant="subtitle2" gutterBottom align="center" sx={{ color: '#ef5350', fontWeight: 700 }}>
            ⚠️ DISCARD PHASE — Select a card to discard
          </Typography>
          <Box sx={{ display: 'flex', gap: 1, justifyContent: 'center', flexWrap: 'wrap' }}>
            {discardButtons.map((b, i) => (
              <Button
                key={b.id}
                variant="outlined"
                color="error"
                onClick={() => sendClick(b.id)}
                disabled={!b.enabled}
                sx={{ animation: `bounceIn 0.35s ease-out ${i * 0.05}s both` }}
              >
                {b.text}
              </Button>
            ))}
          </Box>
        </Paper>
      )}

      <Paper
        sx={{
          p: 1.25, mb: 2,
          bgcolor: alpha(UU_PURPLE, 0.06),
          border: `1px solid ${alpha(UU_PURPLE, 0.2)}`,
          borderRadius: 2,
        }}
      >
        <Box sx={{ display: 'flex', gap: 1, justifyContent: 'center', flexWrap: 'wrap' }}>
          {actionButtons.map((b, bIdx) => (
            <EmojiCardTile
              key={b.id}
              emoji={b.id.startsWith('uu_react_neigh') ? '🚫' : b.id.startsWith('uu_react_super') ? '⚡' : b.id.startsWith('uu_react_pass') ? '✅' : b.id.startsWith('uu_draw') ? '🂠' : b.id.startsWith('uu_end') ? '⏭️' : b.id.startsWith('uu_target') ? '🎯' : b.id.startsWith('uu_cancel') ? '❌' : '🃏'}
              title={b.text}
              corner={b.id.startsWith('uu_react') ? 'NEIGH' : b.id.startsWith('uu_draw') ? 'DRAW' : b.id.startsWith('uu_end') ? 'END' : 'ACT'}
              accent={b.id.startsWith('uu_react_neigh') || b.id.startsWith('uu_react_super') ? '#ef5350' : b.id.startsWith('uu_draw') ? UU_ACCENT : b.id.startsWith('uu_target') ? UU_PINK : UU_PURPLE}
              enabled={!!b.enabled && !snapshot.popup?.active}
              onClick={() => sendClick(b.id)}
              width={90}
            />
          ))}
          {!actionButtons.length && !isDiscardPhase && (
            <Typography variant="caption" color="text.secondary">No actions available.</Typography>
          )}
        </Box>
      </Paper>

      <Divider sx={{ mb: 2, borderColor: alpha(UU_PURPLE, 0.2) }} />

      {/* ── Your Hand ── */}
      <Typography variant="subtitle2" gutterBottom align="center" sx={{ color: UU_ACCENT, fontWeight: 700, letterSpacing: 1 }}>
        YOUR HAND
      </Typography>
      <Paper
        sx={{
          p: 1.25, mb: 2,
          bgcolor: alpha(UU_PANEL, 0.6),
          borderColor: typeof mySeat === 'number' ? playerColors[mySeat % playerColors.length] : alpha(UU_PURPLE, 0.3),
          border: '2px solid',
          borderRadius: 2,
        }}
      >
        <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(90px, 90px))', gap: 1, justifyContent: 'center' }}>
          {myHand.map((c, i) => (
            <Box key={`${c.id}-${c.idx}`} sx={{ animation: `flipIn 0.4s ease-out ${i * 0.05}s both` }}>
              <EmojiCardTile
                emoji={c.emoji || '🂠'}
                title={c.name}
                corner={String(c.kind || '').toUpperCase().slice(0, 4)}
                accent={c.color}
                desc={c.desc}
                enabled={!!c.playable && !snapshot.popup?.active}
                onClick={() => typeof c.idx === 'number' && sendClick(`uu_play:${c.idx}`)}
                width={90}
              />
            </Box>
          ))}
          {!myHand.length && <Typography variant="caption" color="text.secondary" sx={{ gridColumn: '1 / -1', textAlign: 'center' }}>No cards.</Typography>}
        </Box>
      </Paper>

      <Divider sx={{ mb: 2, borderColor: alpha(UU_PURPLE, 0.2) }} />

      {/* ── Player Stables ── */}
      <Typography variant="subtitle2" gutterBottom align="center" sx={{ color: UU_ACCENT, fontWeight: 700, letterSpacing: 1 }}>
        STABLES
      </Typography>
      <Stack spacing={1.5} alignItems="center" sx={{ mb: 2 }}>
        {activePlayers.map((seat, sIdx) => {
          const color = playerColors[seat % playerColors.length];
          const stable = stables[String(seat)] || [];
          const isTurn = turnSeat !== null && seat === turnSeat;
          const prot = protectedTurns[String(seat)] || 0;
          const handN = handCounts[String(seat)] || 0;
          const unicornN = stable.filter((c) => c.kind === 'unicorn' || c.kind === 'baby_unicorn').length;
          const nearWin = unicornN >= goal - 1;

          return (
            <Paper
              key={seat}
              sx={{
                p: 1.5,
                bgcolor: isTurn ? alpha(color, 0.06) : alpha(UU_PANEL, 0.5),
                borderColor: isTurn ? UU_GOLD : alpha(color, 0.4),
                border: isTurn ? `2px solid ${UU_GOLD}` : `1px solid`,
                borderRadius: 2,
                width: '100%',
                maxWidth: 760,
                position: 'relative',
                overflow: 'hidden',
                animation: `fadeInUp 0.3s ease-out ${sIdx * 0.07}s both`,
                ...(isTurn && {
                  boxShadow: `0 0 12px ${alpha(UU_GOLD, 0.2)}, inset 0 0 30px ${alpha(UU_GOLD, 0.03)}`,
                }),
                ...(nearWin && !winner && {
                  boxShadow: `0 0 16px ${alpha(UU_GOLD, 0.35)}`,
                }),
              }}
            >
              {/* Player color accent strip */}
              <Box sx={{ position: 'absolute', top: 0, left: 0, right: 0, height: 3, bgcolor: color }} />

              <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1, mt: 0.5 }}>
                <Stack direction="row" alignItems="center" spacing={1}>
                  {/* Color dot */}
                  <Box sx={{ width: 10, height: 10, borderRadius: '50%', bgcolor: color, boxShadow: `0 0 4px ${color}` }} />
                  <Typography variant="body2" sx={{ fontWeight: isTurn ? 900 : 700, color: isTurn ? UU_GOLD : '#e0d0f0' }}>
                    {seatLabel(seat)} {isTurn ? ' ★' : ''} {prot > 0 ? ' 🛡' : ''}
                  </Typography>
                </Stack>
                <Stack direction="row" spacing={0.5}>
                  <Chip size="small" label={`🦄 ${unicornN}/${goal}`} sx={{
                    fontWeight: 700,
                    bgcolor: nearWin ? alpha(UU_GOLD, 0.15) : alpha(UU_PURPLE, 0.1),
                    color: nearWin ? UU_GOLD : UU_ACCENT,
                    border: nearWin ? `1px solid ${UU_GOLD}` : 'none',
                    fontSize: '0.75rem',
                  }} />
                  <Chip size="small" label={`✋ ${handN}`} sx={{
                    fontWeight: 600,
                    bgcolor: alpha(UU_PURPLE, 0.08),
                    color: '#a090c0',
                    fontSize: '0.7rem',
                  }} />
                </Stack>
              </Stack>

              <Box sx={{ display: 'flex', gap: 1, justifyContent: 'center', flexWrap: 'wrap' }}>
                {stable.map((c, i) => (
                  <EmojiCardTile
                    key={`${seat}-${c.id}-${i}`}
                    emoji={c.emoji || '🂠'}
                    title={c.name}
                    corner={String(c.kind || '').toUpperCase().slice(0, 4)}
                    accent={c.color}
                    desc={c.desc}
                    enabled={false}
                    width={82}
                  />
                ))}
                {!stable.length && <Typography variant="caption" color="text.secondary">Empty stable.</Typography>}
              </Box>

              {/* Nanny Cam revealed hand */}
              {Array.isArray(revealedHands[String(seat)]) && (
                <Paper
                  sx={{
                    mt: 1.5, p: 1,
                    bgcolor: alpha('#6366f1', 0.06),
                    border: `1px solid ${alpha('#6366f1', 0.25)}`,
                    borderRadius: 1,
                  }}
                >
                  <Typography variant="caption" sx={{ fontWeight: 700, color: '#6366f1' }} align="center" display="block">
                    📷 Nanny Cam — Revealed Hand ({(revealedHands[String(seat)] as CardSummary[]).length} cards)
                  </Typography>
                  {(revealedHands[String(seat)] as CardSummary[]).length > 0 ? (
                    <Box sx={{ display: 'flex', gap: 1, justifyContent: 'center', flexWrap: 'wrap', mt: 0.5 }}>
                      {(revealedHands[String(seat)] as CardSummary[]).map((c, i) => (
                        <EmojiCardTile
                          key={`revealed-${seat}-${c.id}-${i}`}
                          emoji={c.emoji || '🂠'}
                          title={c.name}
                          corner={String(c.kind || '').toUpperCase().slice(0, 4)}
                          accent={c.color}
                          desc={c.desc}
                          enabled={false}
                          width={72}
                        />
                      ))}
                    </Box>
                  ) : (
                    <Typography variant="caption" color="text.secondary" align="center" display="block" sx={{ mt: 0.5 }}>
                      No cards in hand.
                    </Typography>
                  )}
                </Paper>
              )}
            </Paper>
          );
        })}
      </Stack>
    </>
  );
}
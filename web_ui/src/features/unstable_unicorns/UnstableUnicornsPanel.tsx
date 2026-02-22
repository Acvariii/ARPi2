import React, { useMemo } from 'react';
import { Box, Button, Divider, Paper, Stack, Typography } from '@mui/material';
import type { Snapshot } from '../../types';
import EmojiCardTile from '../../components/EmojiCardTile';
import GameBanner from '../../components/GameBanner';

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

  return (
    <>
      <GameBanner game="unstable_unicorns" />
      <Paper variant="outlined" sx={{ p: 1.5, mb: 2, animation: 'fadeInUp 0.4s ease-out' }}>
        <Stack spacing={1}>
          <Typography variant="body2" color="text.secondary" align="center">
            Goal: {goal} unicorns {' · '}Deck: {uu.deck_count ?? 0} {' · '}Discard: {uu.discard_count ?? 0}
          </Typography>
          <Typography variant="body2" color="text.secondary" align="center">
            Turn: {turnSeat !== null ? seatLabel(turnSeat) : '—'} {' · '}Phase: {uu.turn_phase ?? '—'}
          </Typography>
          {winner !== null && (
            <Typography variant="body1" sx={{ fontWeight: 900, animation: 'winnerShimmer 2s linear infinite, glowText 1.5s ease-in-out infinite' }} align="center">
              Winner: {seatLabel(winner)}
            </Typography>
          )}

          {!!reaction && (
            <Paper variant="outlined" sx={{ p: 1, borderColor: '#ef5350', borderWidth: 2, bgcolor: '#ef535012', animation: 'blink 1s ease-in-out infinite' }}>
              <Typography variant="body2" sx={{ fontWeight: 800 }} align="center">
                🚫 Reaction: awaiting {typeof reaction.awaiting_seat === 'number' ? seatLabel(reaction.awaiting_seat) : '—'}
              </Typography>
              {reaction.card && (
                <Typography variant="caption" color="text.secondary" align="center" sx={{ display: 'block' }}>
                  Card played: {reaction.card.emoji || ''} {reaction.card.name || ''}
                </Typography>
              )}
            </Paper>
          )}

          {!!prompt && (
            <Typography variant="body2" sx={{ fontWeight: 800, animation: 'slideInRight 0.4s ease-out' }} align="center">
              Choose a target in the action buttons below.
            </Typography>
          )}
        </Stack>
      </Paper>

      <Typography variant="subtitle1" gutterBottom align="center">
        Actions
      </Typography>
      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} justifyContent="center" sx={{ mb: 2, flexWrap: 'wrap' }}>
        {actionButtons.map((b, bIdx) => (
          <Button key={b.id} variant="contained" onClick={() => sendClick(b.id)} disabled={!b.enabled || !!snapshot.popup?.active} sx={{ animation: `bounceIn 0.35s ease-out ${bIdx * 0.05}s both` }}>
            {b.text}
          </Button>
        ))}
        {!actionButtons.length && !isDiscardPhase && <Typography variant="caption" color="text.secondary">No actions available.</Typography>}
      </Stack>

      {isDiscardPhase && !!discardButtons.length && (
        <>
          <Typography variant="subtitle1" gutterBottom align="center" sx={{ color: '#ef5350', fontWeight: 700 }}>
            ⚠️ Discard Phase — Select a card to discard
          </Typography>
          <Paper variant="outlined" sx={{ p: 1.25, mb: 2, borderColor: '#ef5350', borderWidth: 2 }}>
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
        </>
      )}

      <Divider sx={{ mb: 2 }} />

      <Typography variant="subtitle1" gutterBottom align="center">
        Your Hand
      </Typography>
      <Paper
        variant="outlined"
        sx={{
          p: 1.25,
          mb: 2,
          borderColor: typeof mySeat === 'number' ? playerColors[mySeat % playerColors.length] : undefined,
        }}
      >
        <Box sx={{ display: 'flex', gap: 1, justifyContent: 'center', flexWrap: 'wrap' }}>
          {myHand.map((c, i) => (
            <Box key={`${c.id}-${c.idx}`} sx={{ animation: `flipIn 0.4s ease-out ${i * 0.05}s both` }}>
              <EmojiCardTile
                emoji={c.emoji || '🂠'}
                title={c.name}
                corner={String(c.kind || '').toUpperCase().slice(0, 4)}
                accent={c.color}
                enabled={!!c.playable && !snapshot.popup?.active}
                onClick={() => typeof c.idx === 'number' && sendClick(`uu_play:${c.idx}`)}
                width={90}
              />
            </Box>
          ))}
          {!myHand.length && <Typography variant="caption" color="text.secondary">No cards.</Typography>}
        </Box>
      </Paper>

      <Typography variant="subtitle1" gutterBottom align="center">
        Stables
      </Typography>
      <Stack spacing={1} alignItems="center" sx={{ mb: 2 }}>
        {activePlayers.map((seat) => {
          const color = playerColors[seat % playerColors.length];
          const stable = stables[String(seat)] || [];
          const isTurn = turnSeat !== null && seat === turnSeat;
          const prot = protectedTurns[String(seat)] || 0;
          const handN = handCounts[String(seat)] || 0;
          return (
            <Paper
              key={seat}
              variant="outlined"
              sx={{
                p: 1.25,
                borderColor: color,
                width: '100%',
                maxWidth: 760,
                animation: `fadeInUp 0.3s ease-out ${seat * 0.07}s both`,
              }}
            >
              <Typography variant="body2" sx={{ fontWeight: 900 }} align="center">
                {seatLabel(seat)} {isTurn ? ' · (turn)' : ''} {prot > 0 ? ' · 🛡' : ''} {' · '}Hand: {handN}
              </Typography>
              <Typography variant="body2" color="text.secondary" align="center" sx={{ mb: 1 }}>
                Unicorns in stable: {stable.filter((c) => c.kind === 'unicorn' || c.kind === 'baby_unicorn').length}
              </Typography>
              <Box sx={{ display: 'flex', gap: 1, justifyContent: 'center', flexWrap: 'wrap' }}>
                {stable.map((c, i) => (
                  <EmojiCardTile
                    key={`${seat}-${c.id}-${i}`}
                    emoji={c.emoji || '🂠'}
                    title={c.name}
                    corner={String(c.kind || '').toUpperCase().slice(0, 4)}
                    accent={c.color}
                    enabled={false}
                    width={90}
                  />
                ))}
                {!stable.length && <Typography variant="caption" color="text.secondary">Empty stable.</Typography>}
              </Box>
            </Paper>
          );
        })}
      </Stack>
    </>
  );
}

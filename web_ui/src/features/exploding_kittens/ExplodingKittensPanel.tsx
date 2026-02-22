import React from 'react';
import { Box, Chip, Paper, Stack, Typography } from '@mui/material';
import { useTheme } from '@mui/material/styles';
import type { Snapshot } from '../../types';
import EmojiCardTile from '../../components/EmojiCardTile';
import GameBanner from '../../components/GameBanner';

type Props = {
  snapshot: Snapshot;
  seatLabel: (seat: number) => string;
  send: (obj: unknown) => void;
  playerColors: string[];
};

export default function ExplodingKittensPanel({ snapshot, seatLabel, send, playerColors }: Props): React.ReactElement {
  if (snapshot.server_state !== 'exploding_kittens' || !snapshot.exploding_kittens) return <></>;

  const theme = useTheme();
  const ek = snapshot.exploding_kittens;

  const turnSeat = typeof ek.current_turn_seat === 'number' ? ek.current_turn_seat : null;
  const mySeat = typeof snapshot.your_player_slot === 'number' ? snapshot.your_player_slot : null;

  const panelButtons = snapshot.panel_buttons || [];
  const buttonById = new Map(panelButtons.map((b) => [b.id, b] as const));

  const ctrlDraw = buttonById.get('ek_draw');
  const ctrlNope = buttonById.get('ek_nope');
  const ctrlFavorTargets = panelButtons.filter((b) => b.id.startsWith('favor_target:'));

  const sendClick = (id: string) => send({ type: 'click_button', id });

  const ekCardFace = (text: string): { emoji: string; title: string; corner: string; accent: string; isBack?: boolean } => {
    const t = String(text || '').trim();
    const u = t.toUpperCase();

    // Control tiles (not actual hand cards)
    if (u === 'DRAW') {
      return { emoji: '🂠', title: 'Draw', corner: 'DRAW', accent: theme.palette.primary.main, isBack: true };
    }
    if (u === 'NOPE') {
      return { emoji: '🚫', title: 'Nope', corner: 'NOPE', accent: theme.palette.grey[900] };
    }
    if (u.startsWith('FAVOR')) {
      return { emoji: '🎁', title: t, corner: 'FAV', accent: theme.palette.primary.dark };
    }

    // EK card kinds: EK, DEF, ATK, SKIP, SHUF, FUT, FAV, NOPE
    if (u === 'EK') return { emoji: '💣😼', title: 'Explode', corner: 'EK', accent: theme.palette.error.main };
    if (u === 'DEF') return { emoji: '🧯', title: 'Defuse', corner: 'DEF', accent: theme.palette.success.main };
    if (u === 'ATK') return { emoji: '⚔️', title: 'Attack', corner: 'ATK', accent: theme.palette.warning.main };
    if (u === 'SKIP') return { emoji: '⏭️', title: 'Skip', corner: 'SKIP', accent: theme.palette.info.main };
    if (u === 'SHUF') return { emoji: '🔀', title: 'Shuffle', corner: 'SHUF', accent: theme.palette.secondary.main };
    if (u === 'FUT') return { emoji: '🔮', title: 'Future', corner: 'FUT', accent: theme.palette.grey[700] };
    if (u === 'FAV') return { emoji: '🎁', title: 'Favor', corner: 'FAV', accent: theme.palette.primary.main };

    return { emoji: '😺', title: t || '—', corner: u || '—', accent: theme.palette.divider };
  };

  const renderCardTile = (opts: { key: string | number; text: string; onClick?: () => void; enabled?: boolean }) => {
    const enabled = opts.enabled ?? true;
    const clickable = !!opts.onClick && enabled && !snapshot.popup?.active;
    const face = ekCardFace(opts.text);

    return (
      <EmojiCardTile
        key={String(opts.key)}
        emoji={face.emoji}
        title={face.title}
        corner={face.corner}
        accent={face.accent}
        isBack={!!face.isBack}
        enabled={clickable}
        onClick={opts.onClick}
        width={74}
      />
    );
  };

  const eliminatedSet = new Set((ek.eliminated_players || []).map((n) => Number(n)));
  const iAmEliminated = mySeat !== null && eliminatedSet.has(mySeat);

  return (
    <>
      <GameBanner game="exploding_kittens" />
      <Paper variant="outlined" sx={{ p: 1.5, mb: 2, animation: 'fadeInUp 0.4s ease-out' }}>
        <Stack spacing={1}>
          <Stack direction="row" spacing={1} justifyContent="center" flexWrap="wrap" useFlexGap>
            <Typography variant="caption" color="text.secondary">
              Deck:
            </Typography>
            <Chip
              label={`🃍 ${ek.deck_count ?? '?'} left`}
              size="small"
              sx={{
                bgcolor:
                  typeof ek.deck_count === 'number' && ek.deck_count <= 5
                    ? '#c62828'
                    : typeof ek.deck_count === 'number' && ek.deck_count <= 10
                      ? '#e65100'
                      : '#37474f',
                color: '#fff',
                fontWeight: 700,
                height: 20,
                fontSize: '0.7rem',
                animation: typeof ek.deck_count === 'number' && ek.deck_count <= 5 ? 'blink 0.8s ease-in-out infinite' : undefined,
              }}
            />
            {(ek.pending_draws ?? 1) > 1 && (
              <Chip
                label={`Draw ${ek.pending_draws}×`}
                size="small"
                sx={{ bgcolor: '#c62828', color: '#fff', fontWeight: 900, height: 20, fontSize: '0.7rem' }}
              />
            )}
            {ek.discard_top && (
              <Chip label={`Discard: ${ek.discard_top}`} size="small" variant="outlined" sx={{ height: 20, fontSize: '0.7rem' }} />
            )}
          </Stack>
          <Typography variant="body2" color="text.secondary" align="center">
            Turn: {turnSeat !== null ? seatLabel(turnSeat) : '—'}
          </Typography>
          {typeof ek.winner === 'number' && (
            <Typography variant="body2" sx={{ fontWeight: 700, animation: 'winnerShimmer 2s linear infinite, glowText 1.5s ease-in-out infinite' }} align="center">
              🏆 Winner: {seatLabel(ek.winner)}
            </Typography>
          )}
          {/* NOPE window — prominent alert */}
          {!!ek.nope_active && (
            <Paper
              variant="outlined"
              sx={{
                p: 1,
                borderColor: '#ef5350',
                borderWidth: 2,
                bgcolor: '#ef535018',
                textAlign: 'center',
                animation: 'nopeFlash 0.7s ease-in-out infinite',
              }}
            >
              <Typography variant="body1" sx={{ fontWeight: 900, color: '#ef5350' }}>
                🚫 NOPE WINDOW OPEN! ({ek.nope_count ?? 0} played)
              </Typography>
            </Paper>
          )}

          {!!ek.last_event && (
            <Typography variant="body2" sx={{ fontWeight: 700, animation: 'slideInRight 0.4s ease-out' }} align="center">
              {ek.last_event}
            </Typography>
          )}

          {/* See the Future — private cards visible only to the player who played FUT */}
          {Array.isArray(ek.future_cards) && ek.future_cards.length > 0 && (
            <Paper
              variant="outlined"
              sx={{
                p: 1,
                borderColor: '#7e57c2',
                borderWidth: 2,
                bgcolor: '#7e57c218',
                textAlign: 'center',
                animation: 'fadeInUp 0.4s ease-out',
              }}
            >
              <Typography variant="caption" sx={{ fontWeight: 800, color: '#b39ddb', mb: 0.5, display: 'block' }}>
                🔮 Top of deck (only you can see)
              </Typography>
              <Stack direction="row" spacing={1} justifyContent="center" flexWrap="wrap" useFlexGap>
                {ek.future_cards.map((c: string, i: number) => renderCardTile({ key: `fut-${i}`, text: c }))}
              </Stack>
            </Paper>
          )}

          {iAmEliminated && (
            <Typography variant="body2" color="error" sx={{ fontWeight: 800 }} align="center">
              You exploded. You&apos;re out.
            </Typography>
          )}
        </Stack>
      </Paper>

      <Typography variant="subtitle1" gutterBottom align="center">
        Your Hand
      </Typography>

      {(ek.your_hand || []).length ? (
        <Paper
          variant="outlined"
          sx={{
            p: 1.25,
            mb: 2,
            borderColor: typeof mySeat === 'number' && mySeat >= 0 ? playerColors[mySeat % playerColors.length] : undefined,
          }}
        >
          <Box
            sx={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(74px, 74px))',
              gap: 1,
              alignItems: 'start',
              justifyContent: 'center',
            }}
          >
            {(ek.your_hand || []).map((c) =>
              renderCardTile({
                key: c.idx,
                text: c.text,
                enabled: !!c.playable,
                onClick: c.playable ? () => sendClick(`ek_play:${c.idx}`) : undefined,
              })
            )}
          </Box>
        </Paper>
      ) : (
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }} align="center">
          No cards (yet).
        </Typography>
      )}

      {(!snapshot.popup?.active && (!!ctrlFavorTargets.length || !!ctrlNope || !!ctrlDraw || !!ek.awaiting_favor_target)) && (
        <>
          <Typography variant="subtitle1" gutterBottom align="center">
            Actions
          </Typography>
          <Paper
            variant="outlined"
            sx={{
              p: 1.25,
              mb: 2,
              borderColor: typeof mySeat === 'number' && mySeat >= 0 ? playerColors[mySeat % playerColors.length] : undefined,
            }}
          >
            <Box
              sx={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(74px, 74px))',
                gap: 1,
                alignItems: 'start',
                justifyContent: 'center',
              }}
            >
              {!!ctrlFavorTargets.length &&
                ctrlFavorTargets.map((b) =>
                  renderCardTile({
                    key: b.id,
                    text: `FAVOR ${seatLabel(Number(String(b.id).split(':')[1] || -1))}`,
                    enabled: !!b.enabled,
                    onClick: () => sendClick(b.id),
                  })
                )}

              {ctrlNope &&
                renderCardTile({
                  key: ctrlNope.id,
                  text: 'NOPE',
                  enabled: !!ctrlNope.enabled,
                  onClick: () => sendClick(ctrlNope.id),
                })}

              {ctrlDraw &&
                renderCardTile({
                  key: ctrlDraw.id,
                  text: 'DRAW',
                  enabled: !!ctrlDraw.enabled,
                  onClick: () => sendClick(ctrlDraw.id),
                })}
            </Box>

            {!!ek.awaiting_favor_target && (
              <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block', textAlign: 'center' }}>
                Choose a player to Favor.
              </Typography>
            )}
          </Paper>
        </>
      )}

      {!!ek.active_players?.length && (
        <Box sx={{ mb: 2 }}>
          <Typography variant="subtitle1" gutterBottom align="center">
            Players
          </Typography>
          <Stack spacing={1} alignItems="center">
            {(ek.active_players || []).map((pidx) => {
              const eliminated = eliminatedSet.has(Number(pidx));
              return (
                <Paper
                  key={pidx}
                  variant="outlined"
                  sx={{
                    p: 1.25,
                    borderColor: playerColors[pidx % playerColors.length],
                    width: '100%',
                    maxWidth: 440,
                    textAlign: 'center',
                    opacity: eliminated ? 0.55 : 1,
                    animation: `fadeInUp 0.3s ease-out ${pidx * 0.06}s both`,
                  }}
                >
                  <Typography variant="body2" sx={{ fontWeight: 700 }} align="center">
                    {seatLabel(pidx)}{eliminated ? ' (out)' : ''}
                  </Typography>
                  <Typography variant="body2" color="text.secondary" align="center">
                    Cards: {ek.hand_counts?.[String(pidx)] ?? 0}
                    {turnSeat === pidx ? ' · (turn)' : ''}
                  </Typography>
                </Paper>
              );
            })}
          </Stack>
        </Box>
      )}
    </>
  );
}

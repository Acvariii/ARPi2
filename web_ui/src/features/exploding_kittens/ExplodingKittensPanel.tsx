import React from 'react';
import { Box, Chip, Paper, Stack, Typography, LinearProgress } from '@mui/material';
import { alpha } from '@mui/material/styles';
import type { Snapshot } from '../../types';
import EmojiCardTile from '../../components/EmojiCardTile';
import GameBanner from '../../components/GameBanner';

type Props = {
  snapshot: Snapshot;
  seatLabel: (seat: number) => string;
  send: (obj: unknown) => void;
  playerColors: string[];
};

/* ──────────────────────────────────────────
   Exploding Kittens 2 — Amazon Luna vibe
   ────────────────────────────────────────── */

const EK2_ORANGE = '#ff8c00';
const EK2_RED = '#e53935';
const EK2_DARK = '#0e0a14';
const EK2_PANEL = '#1a1422';
const EK2_ACCENT = '#ffab00';
const EK2_GOLD = '#ffd740';

export default function ExplodingKittensPanel({ snapshot, seatLabel, send, playerColors }: Props): React.ReactElement {
  if (snapshot.server_state !== 'exploding_kittens' || !snapshot.exploding_kittens) return <></>;

  const ek = snapshot.exploding_kittens;

  const turnSeat = typeof ek.current_turn_seat === 'number' ? ek.current_turn_seat : null;
  const mySeat = typeof snapshot.your_player_slot === 'number' ? snapshot.your_player_slot : null;

  const panelButtons = snapshot.panel_buttons || [];
  const buttonById = new Map(panelButtons.map((b) => [b.id, b] as const));

  const ctrlDraw = buttonById.get('ek_draw');
  const ctrlNope = buttonById.get('ek_nope');
  const ctrlFavorTargets = panelButtons.filter((b) => b.id.startsWith('favor_target:'));
  const ctrlCatTargets = panelButtons.filter((b) => b.id.startsWith('cat_target:'));

  const sendClick = (id: string) => send({ type: 'click_button', id });

  const ekCardFace = (text: string): { emoji: string; title: string; corner: string; accent: string; isBack?: boolean } => {
    const t = String(text || '').trim();
    const u = t.toUpperCase();

    // Control tiles
    if (u === 'DRAW') return { emoji: '🂠', title: 'Draw', corner: 'DRAW', accent: EK2_ORANGE, isBack: true };
    if (u === 'NOPE') return { emoji: '🚫', title: 'Nope!', corner: 'NOPE', accent: EK2_RED };
    if (u.startsWith('FAVOR')) return { emoji: '🎁', title: t, corner: 'FAV', accent: '#e040fb' };

    // EK card kinds
    if (u === 'EK') return { emoji: '💣😼', title: 'EXPLODE!', corner: 'EK', accent: '#ff1744' };
    if (u === 'DEF') return { emoji: '🧯', title: 'Defuse', corner: 'DEF', accent: '#00e676' };
    if (u === 'ATK') return { emoji: '⚔️', title: 'Attack!', corner: 'ATK', accent: '#ff6e40' };
    if (u === 'SKIP') return { emoji: '⏭️', title: 'Skip', corner: 'SKIP', accent: EK2_GOLD };
    if (u === 'SHUF') return { emoji: '🔀', title: 'Shuffle', corner: 'SHUF', accent: '#448aff' };
    if (u === 'FUT') return { emoji: '🔮', title: 'Future', corner: 'FUT', accent: '#b388ff' };
    if (u === 'FAV') return { emoji: '🎁', title: 'Favor', corner: 'FAV', accent: '#ff80ab' };
    if (u === 'TACO') return { emoji: '🌮', title: 'Tacocat', corner: 'TACO', accent: '#ffb300' };
    if (u === 'CATER') return { emoji: '🍉', title: 'Catermelon', corner: 'CATER', accent: '#66bb6a' };
    if (u === 'HAIRY') return { emoji: '🥔', title: 'Hairy P. Cat', corner: 'HAIRY', accent: '#a1887f' };
    if (u === 'BEARD') return { emoji: '🐈', title: 'Beard Cat', corner: 'BEARD', accent: '#8d6e63' };
    if (u === 'RAINBOW') return { emoji: '🌈', title: 'Rainbow Cat', corner: 'RAINBOW', accent: '#f06292' };
    if (u.startsWith('STEAL')) return { emoji: '😼', title: t, corner: 'STEAL', accent: '#ffab00' };

    return { emoji: '😺', title: t || '—', corner: u || '—', accent: EK2_ACCENT };
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
        width={78}
      />
    );
  };

  const eliminatedSet = new Set((ek.eliminated_players || []).map((n) => Number(n)));
  const iAmEliminated = mySeat !== null && eliminatedSet.has(mySeat);

  const deckCount = typeof ek.deck_count === 'number' ? ek.deck_count : null;
  const deckDanger = deckCount !== null && deckCount <= 5;
  const deckWarn = deckCount !== null && deckCount <= 10;

  return (
    <>
      <GameBanner game="exploding_kittens" />

      {/* ──── HUD BAR ──── */}
      <Paper
        variant="outlined"
        sx={{
          p: 1.5,
          mb: 2,
          bgcolor: EK2_PANEL,
          borderColor: alpha(EK2_ORANGE, 0.3),
          borderWidth: 2,
          animation: 'fadeInUp 0.4s ease-out',
          position: 'relative',
          overflow: 'hidden',
          '&::before': {
            content: '""',
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            height: 3,
            background: `linear-gradient(90deg, ${EK2_RED}, ${EK2_ORANGE}, ${EK2_GOLD})`,
          },
        }}
      >
        <Stack spacing={1.5}>
          {/* Status chips row */}
          <Stack direction="row" spacing={1} justifyContent="center" flexWrap="wrap" useFlexGap>
            <Chip
              label={`${deckDanger ? '🔥' : '🃏'} ${deckCount ?? '?'} left`}
              size="small"
              sx={{
                bgcolor: deckDanger ? EK2_RED : deckWarn ? '#e65100' : '#37474f',
                color: '#fff',
                fontWeight: 900,
                height: 24,
                fontSize: '0.75rem',
                letterSpacing: '0.05em',
                animation: deckDanger ? 'blink 0.8s ease-in-out infinite' : undefined,
                border: `1px solid ${deckDanger ? '#ff5252' : 'transparent'}`,
              }}
            />
            {(ek.pending_draws ?? 1) > 1 && (
              <Chip
                label={`⚠ Draw ${ek.pending_draws}×`}
                size="small"
                sx={{
                  bgcolor: EK2_RED,
                  color: '#fff',
                  fontWeight: 900,
                  height: 24,
                  fontSize: '0.75rem',
                  animation: 'blink 1s ease-in-out infinite',
                }}
              />
            )}
            {ek.discard_top && (
              <Chip
                label={`Discard: ${ek.discard_top}`}
                size="small"
                variant="outlined"
                sx={{
                  height: 24,
                  fontSize: '0.7rem',
                  borderColor: alpha(EK2_ORANGE, 0.4),
                  color: alpha('#fff', 0.7),
                }}
              />
            )}
          </Stack>

          {/* Turn indicator */}
          <Box sx={{ textAlign: 'center' }}>
            {turnSeat !== null ? (
              <Typography
                variant="body2"
                sx={{
                  fontWeight: 800,
                  color: EK2_GOLD,
                  letterSpacing: '0.08em',
                  textShadow: `0 0 12px ${alpha(EK2_ORANGE, 0.5)}`,
                }}
              >
                🐱 {seatLabel(turnSeat)}&apos;s Turn
              </Typography>
            ) : (
              <Typography variant="body2" color="text.secondary">
                Turn: —
              </Typography>
            )}
          </Box>

          {/* Winner */}
          {typeof ek.winner === 'number' && (
            <Box
              sx={{
                textAlign: 'center',
                py: 1,
                borderRadius: 1,
                background: `linear-gradient(135deg, ${alpha(EK2_GOLD, 0.15)}, ${alpha(EK2_ORANGE, 0.1)})`,
                border: `1px solid ${alpha(EK2_GOLD, 0.3)}`,
              }}
            >
              <Typography
                variant="h6"
                sx={{
                  fontWeight: 900,
                  background: `linear-gradient(90deg, ${EK2_GOLD}, ${EK2_ORANGE})`,
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent',
                  animation: 'winnerShimmer 2s linear infinite',
                }}
              >
                🏆 {seatLabel(ek.winner)} — SURVIVOR!
              </Typography>
            </Box>
          )}

          {/* NOPE window — dramatic red alert */}
          {!!ek.nope_active && (
            <Paper
              variant="outlined"
              sx={{
                p: 1.5,
                borderColor: EK2_RED,
                borderWidth: 2,
                bgcolor: alpha(EK2_RED, 0.12),
                textAlign: 'center',
                animation: 'nopeFlash 0.7s ease-in-out infinite',
                position: 'relative',
                overflow: 'hidden',
              }}
            >
              <Typography variant="body1" sx={{ fontWeight: 900, color: '#ff5252', letterSpacing: '0.1em' }}>
                🚫 NOPE WINDOW — REACT NOW!
              </Typography>
              {(ek.nope_count ?? 0) > 0 && (
                <Typography variant="caption" sx={{ color: '#ff8a80', fontWeight: 700 }}>
                  {ek.nope_count} Nope{(ek.nope_count ?? 0) > 1 ? 's' : ''} played
                </Typography>
              )}
              <LinearProgress
                variant="determinate"
                value={100}
                sx={{
                  mt: 0.5,
                  height: 3,
                  bgcolor: alpha(EK2_RED, 0.2),
                  '& .MuiLinearProgress-bar': {
                    bgcolor: EK2_RED,
                    animation: 'nopeCountdown 3s linear',
                  },
                }}
              />
            </Paper>
          )}

          {/* Last event */}
          {!!ek.last_event && (
            <Typography
              variant="body2"
              sx={{
                fontWeight: 700,
                color: alpha('#fff', 0.85),
                textAlign: 'center',
                animation: 'slideInRight 0.4s ease-out',
                borderLeft: `3px solid ${EK2_ORANGE}`,
                pl: 1,
                py: 0.25,
              }}
            >
              ⚡ {ek.last_event}
            </Typography>
          )}

          {/* See the Future — private reveal */}
          {Array.isArray(ek.future_cards) && ek.future_cards.length > 0 && (
            <Paper
              variant="outlined"
              sx={{
                p: 1,
                borderColor: '#7c4dff',
                borderWidth: 2,
                bgcolor: alpha('#7c4dff', 0.08),
                textAlign: 'center',
                animation: 'fadeInUp 0.4s ease-out',
              }}
            >
              <Typography variant="caption" sx={{ fontWeight: 800, color: '#b388ff', mb: 0.5, display: 'block', letterSpacing: '0.05em' }}>
                🔮 TOP OF DECK (only you)
              </Typography>
              <Stack direction="row" spacing={1} justifyContent="center" flexWrap="wrap" useFlexGap>
                {ek.future_cards.map((c: string, i: number) => renderCardTile({ key: `fut-${i}`, text: c }))}
              </Stack>
            </Paper>
          )}

          {iAmEliminated && (
            <Box
              sx={{
                textAlign: 'center',
                py: 0.5,
                bgcolor: alpha(EK2_RED, 0.1),
                borderRadius: 1,
                border: `1px solid ${alpha(EK2_RED, 0.3)}`,
              }}
            >
              <Typography variant="body2" sx={{ fontWeight: 800, color: '#ff5252' }}>
                💀 You exploded. Game over for you.
              </Typography>
            </Box>
          )}
        </Stack>
      </Paper>

      {/* ──── ACTIONS (steal / favor / nope / draw) ──── */}
      {(!snapshot.popup?.active && (!!ctrlFavorTargets.length || !!ctrlCatTargets.length || !!ctrlNope || !!ctrlDraw || !!ek.awaiting_favor_target || !!ek.awaiting_cat_steal)) && (
        <>
          <Typography
            variant="subtitle1"
            gutterBottom
            align="center"
            sx={{ fontWeight: 800, color: EK2_ORANGE, letterSpacing: '0.1em', fontSize: '0.95rem' }}
          >
            ACTIONS
          </Typography>
          <Paper
            variant="outlined"
            sx={{
              p: 1.25,
              mb: 2,
              bgcolor: alpha(EK2_PANEL, 0.9),
              borderColor: (!!ctrlCatTargets.length || !!ek.awaiting_cat_steal) ? '#ffab00'
                : (!!ctrlFavorTargets.length || !!ek.awaiting_favor_target) ? '#ff80ab'
                  : alpha(EK2_ORANGE, 0.3),
              borderWidth: 2,
            }}
          >
            <Box
              sx={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(78px, 78px))',
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

              {!!ctrlCatTargets.length &&
                ctrlCatTargets.map((b) =>
                  renderCardTile({
                    key: b.id,
                    text: `STEAL ${seatLabel(Number(String(b.id).split(':')[1] || -1))}`,
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
              <Typography
                variant="caption"
                sx={{
                  mt: 1,
                  display: 'block',
                  textAlign: 'center',
                  color: '#ff80ab',
                  fontWeight: 700,
                }}
              >
                🎁 Choose a player to Favor.
              </Typography>
            )}

            {!!ek.awaiting_cat_steal && (
              <Typography
                variant="caption"
                sx={{
                  mt: 1,
                  display: 'block',
                  textAlign: 'center',
                  color: '#ffab00',
                  fontWeight: 700,
                }}
              >
                😼 Choose a player to steal from!
              </Typography>
            )}
          </Paper>
        </>
      )}

      {/* ──── YOUR HAND ──── */}
      <Typography
        variant="subtitle1"
        gutterBottom
        align="center"
        sx={{ fontWeight: 800, color: EK2_GOLD, letterSpacing: '0.1em', fontSize: '0.95rem' }}
      >
        YOUR HAND
      </Typography>

      {(ek.your_hand || []).length ? (
        <Paper
          variant="outlined"
          sx={{
            p: 1.25,
            mb: 2,
            bgcolor: alpha(EK2_PANEL, 0.9),
            borderColor: typeof mySeat === 'number' && mySeat >= 0 ? playerColors[mySeat % playerColors.length] : alpha(EK2_ORANGE, 0.3),
            borderWidth: 2,
          }}
        >
          <Box
            sx={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(78px, 78px))',
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
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2, fontStyle: 'italic' }} align="center">
          No cards yet.
        </Typography>
      )}

      {/* ──── PLAYERS ──── */}
      {!!ek.active_players?.length && (
        <Box sx={{ mb: 2 }}>
          <Typography
            variant="subtitle1"
            gutterBottom
            align="center"
            sx={{ fontWeight: 800, color: alpha('#fff', 0.6), letterSpacing: '0.1em', fontSize: '0.85rem' }}
          >
            PLAYERS
          </Typography>
          <Stack spacing={0.75} alignItems="center">
            {(ek.active_players || []).map((pidx) => {
              const eliminated = eliminatedSet.has(Number(pidx));
              const isMyTurn = turnSeat === pidx;
              const cardCount = ek.hand_counts?.[String(pidx)] ?? 0;
              return (
                <Paper
                  key={pidx}
                  variant="outlined"
                  sx={{
                    p: 1,
                    borderColor: isMyTurn ? EK2_GOLD : playerColors[pidx % playerColors.length],
                    borderWidth: isMyTurn ? 2 : 1,
                    width: '100%',
                    maxWidth: 440,
                    bgcolor: isMyTurn ? alpha(EK2_GOLD, 0.06) : alpha(EK2_PANEL, 0.7),
                    opacity: eliminated ? 0.45 : 1,
                    animation: `fadeInUp 0.3s ease-out ${pidx * 0.06}s both`,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    gap: 1,
                  }}
                >
                  <Stack direction="row" spacing={1} alignItems="center">
                    <Box
                      sx={{
                        width: 10,
                        height: 10,
                        borderRadius: '50%',
                        bgcolor: playerColors[pidx % playerColors.length],
                        flexShrink: 0,
                        boxShadow: isMyTurn ? `0 0 8px ${EK2_GOLD}` : undefined,
                      }}
                    />
                    <Typography
                      variant="body2"
                      sx={{
                        fontWeight: isMyTurn ? 900 : 600,
                        color: eliminated ? '#777' : isMyTurn ? EK2_GOLD : '#fff',
                      }}
                    >
                      {eliminated ? '💀 ' : ''}
                      {seatLabel(pidx)}
                      {eliminated ? ' (out)' : ''}
                    </Typography>
                  </Stack>
                  <Stack direction="row" spacing={0.5} alignItems="center">
                    <Chip
                      label={`${cardCount} cards`}
                      size="small"
                      sx={{
                        height: 20,
                        fontSize: '0.65rem',
                        fontWeight: 700,
                        bgcolor: alpha('#fff', 0.08),
                        color: alpha('#fff', 0.7),
                      }}
                    />
                    {isMyTurn && (
                      <Chip
                        label="★ TURN"
                        size="small"
                        sx={{
                          height: 20,
                          fontSize: '0.6rem',
                          fontWeight: 900,
                          bgcolor: alpha(EK2_GOLD, 0.2),
                          color: EK2_GOLD,
                          letterSpacing: '0.05em',
                        }}
                      />
                    )}
                  </Stack>
                </Paper>
              );
            })}
          </Stack>
        </Box>
      )}
    </>
  );
}

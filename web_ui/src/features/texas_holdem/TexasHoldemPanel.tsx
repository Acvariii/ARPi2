import React, { useEffect, useMemo, useState } from 'react';
import { Box, Button, Chip, Paper, Slider, Stack, TextField, Typography } from '@mui/material';
import type { Snapshot } from '../../types';
import PlayingCard from '../../components/PlayingCard';
import GameBanner from '../../components/GameBanner';

type Props = {
  snapshot: Snapshot;
  seatLabel: (seat: number) => string;
  send: (obj: unknown) => void;
  playerColors: string[];
};

export default function TexasHoldemPanel({ snapshot, seatLabel, send, playerColors }: Props): React.ReactElement {
  if (snapshot.server_state !== 'texas_holdem' || !snapshot.texas_holdem) return <></>;

  const th = snapshot.texas_holdem;
  const mySeat = typeof snapshot.your_player_slot === 'number' ? snapshot.your_player_slot : null;

  const panelButtons = snapshot.panel_buttons || [];
  const buttonById = new Map(panelButtons.map((b) => [b.id, b] as const));

  const sendClick = (id: string) => send({ type: 'click_button', id });
  const sendBet = (raiseBy: number) => send({ type: 'texas_holdem_bet', raise_by: raiseBy });

  const community = Array.isArray(th.community) ? th.community : [];
  const myHole = Array.isArray(th.your_hole) ? th.your_hole : [];

  const turnSeat = typeof th.turn_seat === 'number' ? th.turn_seat : null;
  const dealerSeat = typeof th.dealer_seat === 'number' ? th.dealer_seat : null;

  const ctrlCheckCall = buttonById.get('check_call');
  const ctrlBetRaise = buttonById.get('bet_raise');
  const ctrlAllIn = buttonById.get('all_in');
  const ctrlFold = buttonById.get('fold');
  const ctrlNextHand = buttonById.get('next_hand');
  const ctrlToggleReveal = buttonById.get('toggle_reveal');

  const players = Array.isArray(th.players) ? th.players : [];
  const myPlayer = useMemo(() => {
    if (typeof mySeat !== 'number') return null;
    return players.find((p: any) => typeof p?.seat === 'number' && p.seat === mySeat) ?? null;
  }, [players, mySeat]);

  const myStack = typeof myPlayer?.stack === 'number' ? myPlayer.stack : 0;
  const callAmount = typeof th.call_amount === 'number' ? th.call_amount : 0;
  const maxRaiseBy = Math.max(0, myStack - callAmount);

  const defaultRaiseBy = Math.min(Math.max(0, 10), maxRaiseBy);
  const [raiseBy, setRaiseBy] = useState<number>(defaultRaiseBy);

  useEffect(() => {
    // Keep selection valid as stack/call changes.
    setRaiseBy((v) => Math.max(0, Math.min(maxRaiseBy, Number.isFinite(v) ? v : 0)));
  }, [maxRaiseBy]);
  const revealed = (th.revealed_holes || {}) as Record<string, string[]>;

  return (
    <>
      <GameBanner game="texas_holdem" />
      <Paper variant="outlined" sx={{ p: 1.5, mb: 2, animation: 'fadeInUp 0.4s ease-out' }}>
        <Stack spacing={1.25}>
          {/* Street progression */}
          {(() => {
            const streets = ['preflop', 'flop', 'turn', 'river', 'showdown'];
            const currentStreet = String(th.street ?? '').toLowerCase();
            const idx = streets.indexOf(currentStreet);
            return (
              <Stack direction="row" spacing={0.5} justifyContent="center" flexWrap="wrap" useFlexGap>
                {streets.map((s, i) => (
                  <Chip
                    key={s}
                    label={s.toUpperCase()}
                    size="small"
                    sx={{
                      fontWeight: 700,
                      fontSize: '0.65rem',
                      bgcolor: i === idx ? '#1565c0' : i < idx ? '#37474f' : 'transparent',
                      color: i <= idx ? '#fff' : 'text.secondary',
                      border: i === idx ? 'none' : '1px solid',
                      borderColor: i === idx ? 'transparent' : 'divider',
                    }}
                  />
                ))}
              </Stack>
            );
          })()}
          {/* Pot display */}
          <Box sx={{ textAlign: 'center' }}>
            <Typography variant="caption" color="text.secondary">POT</Typography>
            <Typography variant="h4" sx={{ fontWeight: 900, color: '#f9a825', lineHeight: 1.1, animation: 'potPop 0.4s ease-out, glowText 2s ease-in-out infinite' }}>
              🎰 ${(th.pot ?? 0).toLocaleString()}
            </Typography>
          </Box>
          <Stack direction="row" spacing={2} justifyContent="center">
            <Typography variant="body2" color="text.secondary">
              Current bet: <strong>${th.current_bet ?? 0}</strong>
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Dealer: {dealerSeat !== null ? seatLabel(dealerSeat) : '—'}
            </Typography>
          </Stack>
          <Typography variant="body2" color="text.secondary" align="center">
            Turn: {turnSeat !== null ? seatLabel(turnSeat) : '—'}
          </Typography>
          {!!th.showdown?.winners?.length && (
            <Typography variant="body2" sx={{ fontWeight: 700, animation: 'winnerShimmer 2s linear infinite, glowText 1.5s ease-in-out infinite' }} align="center">
              🏆 Winners: {(th.showdown.winners || []).map((s: number) => seatLabel(s)).join(', ')}
            </Typography>
          )}
        </Stack>
      </Paper>

      <Typography variant="subtitle1" gutterBottom align="center">
        Community
      </Typography>
      <Paper variant="outlined" sx={{ p: 1.25, mb: 2 }}>
        <Box sx={{ display: 'flex', gap: 1, justifyContent: 'center', flexWrap: 'wrap' }}>
          {Array.from({ length: 5 }).map((_, i) => {
            const c = community[i];
            const face = typeof c === 'string' && !!c;
            return <PlayingCard key={`c${i}`} card={face ? c : undefined} faceDown={!face} size="md" />;
          })}
        </Box>
      </Paper>

      <Typography variant="subtitle1" gutterBottom align="center">
        Your Cards
      </Typography>
      <Paper
        variant="outlined"
        sx={{
          p: 1.25,
          mb: 2,
          borderColor: typeof mySeat === 'number' && mySeat >= 0 ? playerColors[mySeat % playerColors.length] : undefined,
        }}
      >
        <Box sx={{ display: 'flex', gap: 1, justifyContent: 'center' }}>
          {Array.from({ length: 2 }).map((_, i) => {
            const c = myHole[i];
            const face = typeof c === 'string' && !!c;
            return <PlayingCard key={`h${i}`} card={face ? String(c) : undefined} faceDown={!face} size="md" />;
          })}
        </Box>
      </Paper>

      <Typography variant="subtitle1" gutterBottom align="center">
        Actions
      </Typography>
      {!!ctrlNextHand && (
        <Typography variant="caption" color="text.secondary" display="block" align="center" sx={{ mb: 1 }}>
          All players must press Next Hand.
        </Typography>
      )}

      {!!ctrlBetRaise?.enabled && !ctrlNextHand && (
        <Paper variant="outlined" sx={{ p: 1.25, mb: 2 }}>
          <Stack spacing={1} alignItems="center">
            <Typography variant="body2" color="text.secondary" align="center">
              Raise by: {raiseBy} {' · '}Call: {callAmount} {' · '}Total: {callAmount + raiseBy}
            </Typography>

            <Box sx={{ width: '100%', maxWidth: 520 }}>
              <Slider
                value={raiseBy}
                min={0}
                max={maxRaiseBy}
                step={5}
                onChange={(_, v) => setRaiseBy(Array.isArray(v) ? v[0] : (v as number))}
                disabled={!!snapshot.popup?.active}
              />
            </Box>

            <TextField
              label="Raise by"
              type="number"
              value={raiseBy}
              onChange={(e) => {
                const n = Number(e.target.value);
                if (!Number.isFinite(n)) return;
                setRaiseBy(Math.max(0, Math.min(maxRaiseBy, Math.floor(n))));
              }}
              inputProps={{ min: 0, max: maxRaiseBy, step: 1 }}
              size="small"
              disabled={!!snapshot.popup?.active}
            />
          </Stack>
        </Paper>
      )}

      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} justifyContent="center" sx={{ mb: 2 }}>
        {ctrlCheckCall && (
          <Button variant="contained" onClick={() => sendClick(ctrlCheckCall.id)} disabled={!ctrlCheckCall.enabled || !!snapshot.popup?.active}>
            {ctrlCheckCall.text}
          </Button>
        )}
        {ctrlBetRaise && (
          <Button
            variant="contained"
            onClick={() => (ctrlBetRaise.enabled ? sendBet(raiseBy) : sendClick(ctrlBetRaise.id))}
            disabled={!ctrlBetRaise.enabled || !!snapshot.popup?.active}
          >
            {ctrlBetRaise.text}
          </Button>
        )}
        {ctrlAllIn && (
          <Button variant="contained" onClick={() => sendClick(ctrlAllIn.id)} disabled={!ctrlAllIn.enabled || !!snapshot.popup?.active}>
            {ctrlAllIn.text}
          </Button>
        )}
        {ctrlFold && (
          <Button variant="contained" color="warning" onClick={() => sendClick(ctrlFold.id)} disabled={!ctrlFold.enabled || !!snapshot.popup?.active}>
            {ctrlFold.text}
          </Button>
        )}
        {ctrlNextHand && (
          <Button variant="contained" color="secondary" onClick={() => sendClick(ctrlNextHand.id)} disabled={!ctrlNextHand.enabled || !!snapshot.popup?.active}>
            {ctrlNextHand.text}
          </Button>
        )}

        {ctrlToggleReveal && (
          <Button variant="contained" color="info" onClick={() => sendClick(ctrlToggleReveal.id)} disabled={!ctrlToggleReveal.enabled || !!snapshot.popup?.active}>
            {ctrlToggleReveal.text}
          </Button>
        )}
      </Stack>

      {!!players.length && (
        <>
          <Typography variant="subtitle1" gutterBottom align="center">
            Players
          </Typography>
          <Stack spacing={1} alignItems="center" sx={{ mb: 2 }}>
            {players.map((p: any) => {
              const seat = typeof p.seat === 'number' ? p.seat : -1;
              const isTurn = turnSeat !== null && seat === turnSeat;
              const color = seat >= 0 ? playerColors[seat % playerColors.length] : undefined;
              const status = String(p.status ?? '').toLowerCase();
              const isFolded = status === 'fold' || status === 'folded';
              const isAllIn = status === 'all_in' || status === 'allin';
              const revealedCards = seat >= 0 ? revealed[String(seat)] : undefined;
              return (
                <Paper
                  key={seat}
                  variant="outlined"
                  sx={{
                    p: 1.25,
                    borderColor: isTurn ? color : isFolded ? '#555' : color,
                    borderWidth: isTurn ? 2 : 1,
                    bgcolor: isTurn ? `${color}18` : isFolded ? '#1a1a1a' : 'background.paper',
                    width: '100%',
                    maxWidth: 520,
                    opacity: isFolded ? 0.6 : 1,
                    animation: isTurn ? 'turnGlow 2s ease-in-out infinite' : 'fadeInUp 0.3s ease-out',
                  }}
                >
                  <Stack direction="row" justifyContent="space-between" alignItems="center">
                    <Stack direction="row" spacing={0.75} alignItems="center" flexWrap="wrap">
                      <Typography variant="body2" sx={{ fontWeight: 700 }}>
                        {seat >= 0 ? seatLabel(seat) : 'Player'}
                      </Typography>
                      {isTurn && <Chip label="Turn" size="small" color="primary" sx={{ height: 18, fontSize: '0.65rem', animation: 'badgePop 0.3s ease-out' }} />}
                      {dealerSeat !== null && seat === dealerSeat && <Chip label="D" size="small" variant="outlined" sx={{ height: 18, fontSize: '0.65rem' }} />}
                      {isFolded && <Chip label="Folded" size="small" sx={{ height: 18, fontSize: '0.65rem', bgcolor: '#555', color: '#fff' }} />}
                      {isAllIn && <Chip label="All-In" size="small" sx={{ height: 18, fontSize: '0.65rem', bgcolor: '#f9a825', color: '#000', animation: 'blink 0.8s ease-in-out 3' }} />}
                    </Stack>
                    <Stack direction="row" spacing={1} alignItems="center">
                      <Typography variant="body2" color="text.secondary">Stack: <strong>${p.stack ?? 0}</strong></Typography>
                      {(p.bet ?? 0) > 0 && <Typography variant="caption" color="text.secondary">Bet: ${p.bet}</Typography>}
                    </Stack>
                  </Stack>
                  {!!revealedCards?.length && (
                    <Box sx={{ display: 'flex', gap: 1, justifyContent: 'center', mt: 1, flexWrap: 'wrap' }}>
                      {revealedCards.map((c, i) => (
                        <PlayingCard key={`${seat}-${c}-${i}`} card={String(c)} size="sm" />
                      ))}
                    </Box>
                  )}
                </Paper>
              );
            })}
          </Stack>
        </>
      )}
    </>
  );
}

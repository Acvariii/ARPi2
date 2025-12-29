import React from 'react';
import { Box, Button, Paper, Stack, Typography } from '@mui/material';
import type { Snapshot } from '../../types';
import PlayingCard from '../../components/PlayingCard';

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

  const community = Array.isArray(th.community) ? th.community : [];
  const myHole = Array.isArray(th.your_hole) ? th.your_hole : [];

  const turnSeat = typeof th.turn_seat === 'number' ? th.turn_seat : null;
  const dealerSeat = typeof th.dealer_seat === 'number' ? th.dealer_seat : null;

  const ctrlCheckCall = buttonById.get('check_call');
  const ctrlBetRaise = buttonById.get('bet_raise');
  const ctrlFold = buttonById.get('fold');
  const ctrlNextHand = buttonById.get('next_hand');
  const ctrlToggleReveal = buttonById.get('toggle_reveal');

  const players = Array.isArray(th.players) ? th.players : [];
  const revealed = (th.revealed_holes || {}) as Record<string, string[]>;

  return (
    <>
      <Paper variant="outlined" sx={{ p: 1.5, mb: 2 }}>
        <Stack spacing={1}>
          <Typography variant="subtitle1" align="center">
            Texas Hold&apos;em
          </Typography>
          <Typography variant="body2" color="text.secondary" align="center">
            Street: {th.street ?? '—'} {' · '}Pot: {th.pot ?? 0} {' · '}Current bet: {th.current_bet ?? 0}
          </Typography>
          <Typography variant="body2" color="text.secondary" align="center">
            Dealer: {dealerSeat !== null ? seatLabel(dealerSeat) : '—'} {' · '}Turn: {turnSeat !== null ? seatLabel(turnSeat) : '—'}
          </Typography>
          {!!th.showdown?.winners?.length && (
            <Typography variant="body2" sx={{ fontWeight: 700 }} align="center">
              Winners: {(th.showdown.winners || []).map((s: number) => seatLabel(s)).join(', ')}
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
      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} justifyContent="center" sx={{ mb: 2 }}>
        {ctrlCheckCall && (
          <Button variant="contained" onClick={() => sendClick(ctrlCheckCall.id)} disabled={!ctrlCheckCall.enabled || !!snapshot.popup?.active}>
            {ctrlCheckCall.text}
          </Button>
        )}
        {ctrlBetRaise && (
          <Button variant="contained" onClick={() => sendClick(ctrlBetRaise.id)} disabled={!ctrlBetRaise.enabled || !!snapshot.popup?.active}>
            {ctrlBetRaise.text}
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
              const revealedCards = seat >= 0 ? revealed[String(seat)] : undefined;
              return (
                <Paper
                  key={seat}
                  variant="outlined"
                  sx={{
                    p: 1.25,
                    borderColor: color,
                    width: '100%',
                    maxWidth: 520,
                    textAlign: 'center',
                  }}
                >
                  <Typography variant="body2" sx={{ fontWeight: 700 }} align="center">
                    {seat >= 0 ? seatLabel(seat) : 'Player'}
                    {isTurn ? ' · (turn)' : ''}
                    {dealerSeat !== null && seat === dealerSeat ? ' · (dealer)' : ''}
                  </Typography>
                  <Typography variant="body2" color="text.secondary" align="center">
                    Stack: {p.stack ?? 0} {' · '}Bet: {p.bet ?? 0} {' · '}Status: {p.status ?? '—'}
                  </Typography>

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

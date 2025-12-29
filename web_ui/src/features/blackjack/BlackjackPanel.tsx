import React from 'react';
import {
  Button,
  Card,
  CardContent,
  Dialog,
  DialogActions,
  DialogContent,
  Divider,
  Paper,
  Stack,
  Typography,
} from '@mui/material';
import type { Snapshot } from '../../types';

type Props = {
  snapshot: Snapshot;
  status: string;
  isSeated: boolean;
  send: (obj: unknown) => void;
  CardRow: React.ComponentType<{ cards: string[] }>;
};

export default function BlackjackPanel({ snapshot, status, isSeated, send, CardRow }: Props): React.ReactElement {
  if (snapshot.server_state !== 'blackjack' || !snapshot.blackjack) return <></>;

  return (
    <>
      <Paper variant="outlined" sx={{ p: 1.5, mb: 2 }}>
        <Stack spacing={1}>
          <Typography variant="subtitle1">Blackjack</Typography>
          <Typography variant="body2" color="text.secondary">
            Chips: {typeof snapshot.blackjack.your_chips === 'number' ? `$${snapshot.blackjack.your_chips}` : '—'}
            {' · '}Bet: ${snapshot.blackjack.your_total_bet ?? 0}
          </Typography>

          {!!snapshot.blackjack.phase_text && (
            <Typography variant="body2" color="text.secondary">
              {snapshot.blackjack.phase_text}
              {typeof snapshot.blackjack.ready_count === 'number' && typeof snapshot.blackjack.required_count === 'number'
                ? ` (${snapshot.blackjack.ready_count}/${snapshot.blackjack.required_count})`
                : ''}
            </Typography>
          )}

          {snapshot.blackjack.state === 'betting' && (
            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}>
              <Button
                variant="outlined"
                onClick={() => send({ type: 'blackjack_adjust_bet', amount: 5 })}
                disabled={status !== 'connected' || !isSeated || (snapshot.blackjack.your_current_bet ?? 0) < 5}
              >
                -$5
              </Button>
              <Button
                variant="outlined"
                onClick={() => send({ type: 'blackjack_adjust_bet', amount: 25 })}
                disabled={status !== 'connected' || !isSeated || (snapshot.blackjack.your_current_bet ?? 0) < 25}
              >
                -$25
              </Button>
              <Button
                variant="outlined"
                onClick={() => send({ type: 'blackjack_adjust_bet', amount: snapshot.blackjack?.your_current_bet ?? 0 })}
                disabled={
                  status !== 'connected' ||
                  !isSeated ||
                  !(snapshot.blackjack?.your_current_bet && snapshot.blackjack.your_current_bet > 0)
                }
              >
                Clear bet
              </Button>
            </Stack>
          )}

          <Typography variant="body2" sx={{ fontWeight: 600 }}>
            Your hand
            {typeof snapshot.blackjack.your_hand_value === 'number' ? ` (value ${snapshot.blackjack.your_hand_value})` : ''}
          </Typography>
          {(snapshot.blackjack.your_hand || []).length ? (
            <CardRow cards={snapshot.blackjack.your_hand || []} />
          ) : (
            <Typography variant="body2" color="text.secondary">
              No cards yet.
            </Typography>
          )}
        </Stack>
      </Paper>

      <Dialog
        open={!!snapshot.blackjack?.result_popup}
        disableEscapeKeyDown
        onClose={(_, reason) => {
          if (reason === 'backdropClick' || reason === 'escapeKeyDown') return;
        }}
      >
        <DialogContent dividers>
          {snapshot.blackjack?.result_popup && (
            <Stack spacing={1.5}>
              <Typography variant="subtitle1" sx={{ fontWeight: 800 }}>
                Round Result
              </Typography>

              <Typography variant="body2" color="text.secondary">
                Dealer
                {typeof snapshot.blackjack.result_popup.dealer.value === 'number'
                  ? ` (value ${snapshot.blackjack.result_popup.dealer.value})`
                  : ''}
              </Typography>
              <CardRow cards={snapshot.blackjack.result_popup.dealer.cards || []} />

              <Divider />

              {(snapshot.blackjack.result_popup.hands || []).map((h, idx) => (
                <Card key={idx} variant="outlined">
                  <CardContent sx={{ py: 1.25, '&:last-child': { pb: 1.25 } }}>
                    <Stack spacing={1}>
                      <Stack direction="row" justifyContent="space-between" alignItems="center">
                        <Typography variant="body2" sx={{ fontWeight: 800 }}>
                          {h.title}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          Bet ${h.bet}
                        </Typography>
                      </Stack>
                      <Typography variant="body2" color="text.secondary">
                        {h.message}
                        {typeof h.value === 'number' ? ` (value ${h.value})` : ''}
                      </Typography>
                      <CardRow cards={h.cards || []} />
                    </Stack>
                  </CardContent>
                </Card>
              ))}

              <Typography variant="caption" color="text.secondary">
                You must close this popup.
              </Typography>
            </Stack>
          )}
        </DialogContent>
        <DialogActions>
          <Button
            variant="contained"
            onClick={() => send({ type: 'blackjack_close_result' })}
            disabled={status !== 'connected' || !isSeated}
          >
            Close
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
}

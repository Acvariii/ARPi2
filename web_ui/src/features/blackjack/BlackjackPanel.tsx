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

  const panelButtons = snapshot.panel_buttons || [];
  const buttonById = new Map(panelButtons.map((b) => [b.id, b] as const));
  const sendClick = (id: string) => send({ type: 'click_button', id });

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

          {snapshot.blackjack.state === 'betting' && (
            <>
              <Typography variant="body2" sx={{ fontWeight: 700 }}>
                Actions
              </Typography>
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

                <Button
                  variant="outlined"
                  onClick={() => sendClick('btn_4')}
                  disabled={status !== 'connected' || !isSeated || !(buttonById.get('btn_4')?.enabled ?? false)}
                >
                  All-in
                </Button>
              </Stack>

              {!!panelButtons.length && !snapshot.popup?.active && (
                <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} sx={{ mt: 1 }}>
                  {panelButtons.map((b) => (
                    <Button
                      key={b.id}
                      variant={String(b.text || '').toLowerCase().includes('ready') ? 'contained' : 'outlined'}
                      color={String(b.text || '').toLowerCase().includes('ready') ? 'success' : 'primary'}
                      disabled={status !== 'connected' || !isSeated || !b.enabled}
                      onClick={() => sendClick(b.id)}
                    >
                      {b.text || b.id}
                    </Button>
                  ))}
                </Stack>
              )}
            </>
          )}

          {snapshot.blackjack.state === 'playing' && !!panelButtons.length && !snapshot.popup?.active && (
            <>
              <Typography variant="body2" sx={{ fontWeight: 700 }}>
                Actions
              </Typography>
              <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}>
                {panelButtons.map((b) => (
                  <Button
                    key={b.id}
                    variant="contained"
                    disabled={status !== 'connected' || !isSeated || !b.enabled}
                    onClick={() => sendClick(b.id)}
                  >
                    {b.text || b.id}
                  </Button>
                ))}
              </Stack>
            </>
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
                All players must press Next hand.
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
            Next hand
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
}

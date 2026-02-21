import React from 'react';
import {
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  Divider,
  Paper,
  Stack,
  Typography,
} from '@mui/material';
import type { Snapshot } from '../../types';
import GameBanner from '../../components/GameBanner';

function handResultStyle(h: { message?: string; blackjack?: boolean; busted?: boolean }) {
  if (h.blackjack) return { border: '2px solid #f9a825', bgcolor: '#f9a82512' };
  if (h.busted) return { border: '2px solid #c62828', bgcolor: '#c6282812' };
  const msg = String(h.message ?? '').toLowerCase();
  if (msg.includes('win')) return { border: '2px solid #2e7d32', bgcolor: '#2e7d3212' };
  if (msg.includes('push') || msg.includes('tie')) return { border: '2px solid #78909c', bgcolor: 'transparent' };
  if (msg.includes('lose')) return { border: '2px solid #c62828', bgcolor: '#c6282812' };
  return { border: '1px solid', bgcolor: 'transparent' };
}

function handResultLabel(h: { message?: string; blackjack?: boolean; busted?: boolean }) {
  if (h.blackjack) return { text: '🃏 BLACKJACK!', color: '#f9a825' };
  if (h.busted) return { text: '💥 BUST', color: '#c62828' };
  const msg = String(h.message ?? '').toLowerCase();
  if (msg.includes('win')) return { text: '✅ WIN', color: '#2e7d32' };
  if (msg.includes('push') || msg.includes('tie')) return { text: '🤝 PUSH', color: '#78909c' };
  if (msg.includes('lose')) return { text: '❌ LOSE', color: '#c62828' };
  return { text: '', color: 'inherit' };
}

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
      <GameBanner game="blackjack" />
      <Paper variant="outlined" sx={{ p: 1.5, mb: 2, animation: 'fadeInUp 0.4s ease-out' }}>
        <Stack spacing={1}>
          <Typography variant="subtitle1">Blackjack</Typography>
          <Stack direction="row" spacing={3} justifyContent="center" alignItems="center" sx={{ py: 0.5 }}>
            <Box sx={{ textAlign: 'center' }}>
              <Typography variant="caption" color="text.secondary">Chips</Typography>
              <Typography variant="h5" sx={{ fontWeight: 900, color: '#4caf50', lineHeight: 1.1, animation: 'potPop 0.4s ease-out' }}>
                {typeof snapshot.blackjack.your_chips === 'number' ? `$${snapshot.blackjack.your_chips.toLocaleString()}` : '—'}
              </Typography>
            </Box>
            <Box sx={{ textAlign: 'center' }}>
              <Typography variant="caption" color="text.secondary">Bet</Typography>
              <Typography variant="h5" sx={{ fontWeight: 900, color: '#ff9800', lineHeight: 1.1, animation: 'bounceIn 0.35s ease-out' }}>
                ${snapshot.blackjack.your_total_bet ?? 0}
              </Typography>
            </Box>
          </Stack>

          {!!snapshot.blackjack.phase_text && (
            <Typography variant="body2" color="text.secondary">
              {snapshot.blackjack.phase_text}
              {typeof snapshot.blackjack.ready_count === 'number' && typeof snapshot.blackjack.required_count === 'number'
                ? ` (${snapshot.blackjack.ready_count}/${snapshot.blackjack.required_count})`
                : ''}
            </Typography>
          )}

          <Stack direction="row" spacing={1} alignItems="center">
            <Typography variant="body2" sx={{ fontWeight: 700 }}>Your hand</Typography>
            {typeof snapshot.blackjack.your_hand_value === 'number' && (
              <Chip
                label={`${snapshot.blackjack.your_hand_value}`}
                size="small"
                sx={{
                  bgcolor:
                    snapshot.blackjack.your_hand_value > 21
                      ? '#c62828'
                      : snapshot.blackjack.your_hand_value === 21
                        ? '#f9a825'
                        : '#1976d2',
                  color: '#fff',
                  fontWeight: 900,
                  animation: 'badgePop 0.3s ease-out',
                }}
              />
            )}
          </Stack>
          {(snapshot.blackjack.your_hand || []).length ? (
            <Box sx={{ animation: 'flipIn 0.5s ease-out' }}>
              <CardRow cards={snapshot.blackjack.your_hand || []} />
            </Box>
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
              <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} sx={{ '& > button': { animation: 'bounceIn 0.35s ease-out both' }, '& > button:nth-of-type(2)': { animationDelay: '0.05s' }, '& > button:nth-of-type(3)': { animationDelay: '0.1s' }, '& > button:nth-of-type(4)': { animationDelay: '0.15s' } }}>
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

              {(snapshot.blackjack.result_popup.hands || []).map((h, idx) => {
                const style = handResultStyle(h);
                const label = handResultLabel(h);
                return (
                  <Card key={idx} variant="outlined" sx={{ border: style.border, bgcolor: style.bgcolor, animation: `fadeInUp 0.3s ease-out ${idx * 0.1}s both` }}>
                    <CardContent sx={{ py: 1.25, '&:last-child': { pb: 1.25 } }}>
                      <Stack spacing={1}>
                        <Stack direction="row" justifyContent="space-between" alignItems="center">
                          <Stack direction="row" spacing={1} alignItems="center">
                            <Typography variant="body2" sx={{ fontWeight: 800 }}>
                              {h.title}
                            </Typography>
                            {!!label.text && (
                              <Typography variant="body2" sx={{ fontWeight: 900, color: label.color, animation: h.blackjack ? 'glowText 1.5s ease-in-out infinite' : 'badgePop 0.4s ease-out' }}>
                                {label.text}
                              </Typography>
                            )}
                          </Stack>
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
                );
              })}

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

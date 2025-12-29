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

export type TradeSide = 'offer' | 'request';

export type PropDragPayload = {
  side: TradeSide;
  propIdx: number;
  included: boolean;
};

export type TradeDropTarget = {
  side: TradeSide;
  included: boolean;
};

type Props = {
  snapshot: Snapshot;
  send: (obj: unknown) => void;
  seatLabel: (seat: number) => string;

  allowPopupLineColor: boolean;

  isTradePopup: boolean;
  tradePopup: NonNullable<Snapshot['popup']>['trade'] | null;
  isTradeEditable: boolean;
  tradeMoneyStep: number;
  tradeSetMoney: (side: TradeSide, delta: number) => void;
  tradeSetProperty: (side: TradeSide, propIdx: number, included: boolean) => void;
  onPropDragStart: (e: React.DragEvent, payload: PropDragPayload) => void;
  onTradeDrop: (e: React.DragEvent, target: TradeDropTarget) => void;

  isTradeSelectPopup: boolean;
  tradeSelectPopup: NonNullable<Snapshot['popup']>['trade_select'] | null;
};

export default function PopupDialog(props: Props): React.ReactElement {
  const {
    snapshot,
    send,
    seatLabel,
    allowPopupLineColor,
    isTradePopup,
    tradePopup,
    isTradeEditable,
    tradeMoneyStep,
    tradeSetMoney,
    tradeSetProperty,
    onPropDragStart,
    onTradeDrop,
    isTradeSelectPopup,
    tradeSelectPopup,
  } = props;

  if (!snapshot?.popup?.active) return <></>;

  return (
    <Dialog open={!!snapshot.popup?.active}>
      <DialogContent dividers>
        {isTradePopup ? (
          <Stack spacing={2}>
            <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
              Trade: {seatLabel(tradePopup!.initiator)} ↔ {seatLabel(tradePopup!.partner)}
            </Typography>

            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
              <Card variant="outlined" sx={{ flex: 1 }}>
                <CardContent>
                  <Typography variant="body2" sx={{ fontWeight: 700, mb: 1 }}>
                    You give
                  </Typography>
                  <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1, flexWrap: 'wrap' }}>
                    <Typography variant="body2">${tradePopup!.offer.money}</Typography>
                    {isTradeEditable && (
                      <>
                        <Button size="small" variant="outlined" onClick={() => tradeSetMoney('offer', -tradeMoneyStep)}>
                          -${tradeMoneyStep}
                        </Button>
                        <Button size="small" variant="outlined" onClick={() => tradeSetMoney('offer', +tradeMoneyStep)}>
                          +${tradeMoneyStep}
                        </Button>
                        <Typography variant="caption" color="text.secondary">
                          (max ${tradePopup!.initiator_assets.money})
                        </Typography>
                      </>
                    )}
                  </Stack>

                  <Paper
                    variant="outlined"
                    sx={{ p: 1, minHeight: 72 }}
                    onDragOver={(e) => isTradeEditable && e.preventDefault()}
                    onDrop={(e) => onTradeDrop(e, { side: 'offer', included: true })}
                  >
                    <Stack spacing={1}>
                      {(tradePopup!.offer.properties || []).length ? (
                        tradePopup!.offer.properties.map((idx) => {
                          const p = tradePopup!.initiator_assets.properties.find((pp) => pp.idx === idx);
                          if (!p) return null;
                          return (
                            <Card
                              key={`offer-${p.idx}`}
                              variant="outlined"
                              draggable={isTradeEditable && p.tradable}
                              onDragStart={(e) => onPropDragStart(e, { side: 'offer', propIdx: p.idx, included: true })}
                              sx={{ borderColor: p.color || 'divider', opacity: p.tradable ? 1 : 0.6 }}
                            >
                              <CardContent sx={{ py: 1, '&:last-child': { pb: 1 } }}>
                                <Typography variant="body2">{p.name}</Typography>
                                {!p.tradable && (
                                  <Typography variant="caption" color="text.secondary">
                                    {p.mortgaged ? 'Mortgaged' : p.houses > 0 ? `Houses: ${p.houses}` : 'Not tradable'}
                                  </Typography>
                                )}
                              </CardContent>
                            </Card>
                          );
                        })
                      ) : (
                        <Typography variant="body2" color="text.secondary">
                          Drop properties here
                        </Typography>
                      )}
                    </Stack>
                  </Paper>
                </CardContent>
              </Card>

              <Card variant="outlined" sx={{ flex: 1 }}>
                <CardContent>
                  <Typography variant="body2" sx={{ fontWeight: 700, mb: 1 }}>
                    You get
                  </Typography>
                  <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1, flexWrap: 'wrap' }}>
                    <Typography variant="body2">${tradePopup!.request.money}</Typography>
                    {isTradeEditable && (
                      <>
                        <Button size="small" variant="outlined" onClick={() => tradeSetMoney('request', -tradeMoneyStep)}>
                          -${tradeMoneyStep}
                        </Button>
                        <Button size="small" variant="outlined" onClick={() => tradeSetMoney('request', +tradeMoneyStep)}>
                          +${tradeMoneyStep}
                        </Button>
                        <Typography variant="caption" color="text.secondary">
                          (max ${tradePopup!.partner_assets.money})
                        </Typography>
                      </>
                    )}
                  </Stack>

                  <Paper
                    variant="outlined"
                    sx={{ p: 1, minHeight: 72 }}
                    onDragOver={(e) => isTradeEditable && e.preventDefault()}
                    onDrop={(e) => onTradeDrop(e, { side: 'request', included: true })}
                  >
                    <Stack spacing={1}>
                      {(tradePopup!.request.properties || []).length ? (
                        tradePopup!.request.properties.map((idx) => {
                          const p = tradePopup!.partner_assets.properties.find((pp) => pp.idx === idx);
                          if (!p) return null;
                          return (
                            <Card
                              key={`req-${p.idx}`}
                              variant="outlined"
                              draggable={isTradeEditable && p.tradable}
                              onDragStart={(e) => onPropDragStart(e, { side: 'request', propIdx: p.idx, included: true })}
                              sx={{ borderColor: p.color || 'divider', opacity: p.tradable ? 1 : 0.6 }}
                            >
                              <CardContent sx={{ py: 1, '&:last-child': { pb: 1 } }}>
                                <Typography variant="body2">{p.name}</Typography>
                                {!p.tradable && (
                                  <Typography variant="caption" color="text.secondary">
                                    {p.mortgaged ? 'Mortgaged' : p.houses > 0 ? `Houses: ${p.houses}` : 'Not tradable'}
                                  </Typography>
                                )}
                              </CardContent>
                            </Card>
                          );
                        })
                      ) : (
                        <Typography variant="body2" color="text.secondary">
                          Drop properties here
                        </Typography>
                      )}
                    </Stack>
                  </Paper>
                </CardContent>
              </Card>
            </Stack>

            {isTradeEditable && (
              <>
                <Divider />
                <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
                  <Card variant="outlined" sx={{ flex: 1 }}>
                    <CardContent>
                      <Typography variant="body2" sx={{ fontWeight: 700, mb: 1 }}>
                        Your properties
                      </Typography>
                      <Stack spacing={1}>
                        {tradePopup!.initiator_assets.properties.map((p) => {
                          const selected = tradePopup!.offer.properties.includes(p.idx);
                          return (
                            <Card
                              key={`my-${p.idx}`}
                              variant="outlined"
                              draggable={!selected && p.tradable}
                              onDragStart={(e) => onPropDragStart(e, { side: 'offer', propIdx: p.idx, included: false })}
                              onDoubleClick={() => p.tradable && tradeSetProperty('offer', p.idx, !selected)}
                              sx={{
                                borderColor: p.color || 'divider',
                                opacity: p.tradable ? 1 : 0.6,
                                backgroundColor: selected ? 'action.selected' : 'background.paper',
                                cursor: p.tradable ? 'grab' : 'not-allowed',
                              }}
                            >
                              <CardContent sx={{ py: 1, '&:last-child': { pb: 1 } }}>
                                <Typography variant="body2">{p.name}</Typography>
                                {!p.tradable && (
                                  <Typography variant="caption" color="text.secondary">
                                    {p.mortgaged ? 'Mortgaged' : p.houses > 0 ? `Houses: ${p.houses}` : 'Not tradable'}
                                  </Typography>
                                )}
                                {selected && (
                                  <Typography variant="caption" color="text.secondary">
                                    In offer (double-click to remove)
                                  </Typography>
                                )}
                              </CardContent>
                            </Card>
                          );
                        })}
                      </Stack>
                      <Paper
                        variant="outlined"
                        sx={{ mt: 1, p: 1 }}
                        onDragOver={(e) => e.preventDefault()}
                        onDrop={(e) => onTradeDrop(e, { side: 'offer', included: false })}
                      >
                        <Typography variant="caption" color="text.secondary">
                          Drop here to remove from offer
                        </Typography>
                      </Paper>
                    </CardContent>
                  </Card>

                  <Card variant="outlined" sx={{ flex: 1 }}>
                    <CardContent>
                      <Typography variant="body2" sx={{ fontWeight: 700, mb: 1 }}>
                        Their properties
                      </Typography>
                      <Stack spacing={1}>
                        {tradePopup!.partner_assets.properties.map((p) => {
                          const selected = tradePopup!.request.properties.includes(p.idx);
                          return (
                            <Card
                              key={`their-${p.idx}`}
                              variant="outlined"
                              draggable={!selected && p.tradable}
                              onDragStart={(e) => onPropDragStart(e, { side: 'request', propIdx: p.idx, included: false })}
                              onDoubleClick={() => p.tradable && tradeSetProperty('request', p.idx, !selected)}
                              sx={{
                                borderColor: p.color || 'divider',
                                opacity: p.tradable ? 1 : 0.6,
                                backgroundColor: selected ? 'action.selected' : 'background.paper',
                                cursor: p.tradable ? 'grab' : 'not-allowed',
                              }}
                            >
                              <CardContent sx={{ py: 1, '&:last-child': { pb: 1 } }}>
                                <Typography variant="body2">{p.name}</Typography>
                                {!p.tradable && (
                                  <Typography variant="caption" color="text.secondary">
                                    {p.mortgaged ? 'Mortgaged' : p.houses > 0 ? `Houses: ${p.houses}` : 'Not tradable'}
                                  </Typography>
                                )}
                                {selected && (
                                  <Typography variant="caption" color="text.secondary">
                                    In request (double-click to remove)
                                  </Typography>
                                )}
                              </CardContent>
                            </Card>
                          );
                        })}
                      </Stack>
                      <Paper
                        variant="outlined"
                        sx={{ mt: 1, p: 1 }}
                        onDragOver={(e) => e.preventDefault()}
                        onDrop={(e) => onTradeDrop(e, { side: 'request', included: false })}
                      >
                        <Typography variant="caption" color="text.secondary">
                          Drop here to remove from request
                        </Typography>
                      </Paper>
                    </CardContent>
                  </Card>
                </Stack>
              </>
            )}
          </Stack>
        ) : snapshot.popup?.popup_type === 'mortgage' && snapshot.popup?.deed_detail ? (
          (() => {
            const deed = snapshot.popup!.deed_detail!;
            const typeLabel =
              deed.type === 'property'
                ? 'Property'
                : deed.type === 'railroad'
                  ? 'Railroad'
                  : deed.type === 'utility'
                    ? 'Utility'
                    : 'Deed';

            const statusLabel = deed.mortgaged
              ? 'Mortgaged'
              : deed.houses >= 5
                ? 'Hotel'
                : deed.houses > 0
                  ? `${deed.houses} House${deed.houses === 1 ? '' : 's'}`
                  : 'Unmortgaged';

            const rentLines: Array<{ label: string; value: string }> = [];
            if (deed.type === 'property' && (deed.rent_tiers || []).length) {
              const tiers = deed.rent_tiers || [];
              const labels = ['Rent', '1 House', '2 Houses', '3 Houses', '4 Houses', 'Hotel'];
              for (let i = 0; i < Math.min(labels.length, tiers.length); i++) {
                rentLines.push({ label: labels[i], value: `$${tiers[i]}` });
              }
            } else if (deed.type === 'railroad' && (deed.rent_tiers || []).length) {
              const tiers = deed.rent_tiers || [];
              const labels = ['1 Railroad', '2 Railroads', '3 Railroads', '4 Railroads'];
              for (let i = 0; i < Math.min(labels.length, tiers.length); i++) {
                rentLines.push({ label: labels[i], value: `$${tiers[i]}` });
              }
            }

            return (
              <Stack spacing={1.5}>
                <Card variant="outlined" sx={{ borderColor: deed.color || 'divider' }}>
                  <Box sx={{ height: 10, bgcolor: deed.color || 'divider' }} />
                  <CardContent>
                    <Typography variant="subtitle1" sx={{ fontWeight: 800 }}>
                      {deed.name || `Property #${deed.idx}`}
                    </Typography>

                    <Stack direction="row" spacing={1} alignItems="center" sx={{ flexWrap: 'wrap', mt: 1 }}>
                      <Chip size="small" label={typeLabel} variant="outlined" />
                      <Chip size="small" label={statusLabel} variant="outlined" color={deed.mortgaged ? 'warning' : 'default'} />
                      {typeof deed.scroll_index === 'number' && typeof deed.scroll_total === 'number' && deed.scroll_total > 0 && (
                        <Chip size="small" label={`${deed.scroll_index}/${deed.scroll_total}`} variant="outlined" />
                      )}
                      {typeof deed.owned_in_group === 'number' && deed.owned_in_group > 0 && deed.group && (
                        <Chip size="small" label={`Owned in group: ${deed.owned_in_group}`} variant="outlined" />
                      )}
                    </Stack>

                    <Divider sx={{ my: 1.5 }} />

                    <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} sx={{ flexWrap: 'wrap' }}>
                      <Typography variant="body2" color="text.secondary">
                        Price: <Box component="span" sx={{ color: 'text.primary', fontWeight: 700 }}>${deed.price}</Box>
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Mortgage:{' '}
                        <Box component="span" sx={{ color: 'text.primary', fontWeight: 700 }}>${deed.mortgage_value}</Box>
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Unmortgage:{' '}
                        <Box component="span" sx={{ color: 'text.primary', fontWeight: 700 }}>${deed.unmortgage_cost}</Box>
                      </Typography>
                      {deed.type === 'property' && deed.house_cost > 0 && (
                        <Typography variant="body2" color="text.secondary">
                          House cost:{' '}
                          <Box component="span" sx={{ color: 'text.primary', fontWeight: 700 }}>${deed.house_cost}</Box>
                        </Typography>
                      )}
                    </Stack>

                    {deed.type === 'utility' && (
                      <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                        Rent: 4× dice (1 utility), 10× dice (2 utilities)
                      </Typography>
                    )}

                    {(rentLines.length > 0 || deed.type === 'utility') && <Divider sx={{ my: 1.5 }} />}

                    {rentLines.length > 0 && (
                      <Stack spacing={0.75}>
                        <Typography variant="body2" sx={{ fontWeight: 700 }}>
                          Rent
                        </Typography>
                        {rentLines.map((r) => (
                          <Box key={r.label} sx={{ display: 'flex', justifyContent: 'space-between', gap: 2 }}>
                            <Typography variant="body2" color="text.secondary">
                              {r.label}
                            </Typography>
                            <Typography variant="body2" sx={{ fontWeight: 700 }}>
                              {r.value}
                            </Typography>
                          </Box>
                        ))}
                      </Stack>
                    )}
                  </CardContent>
                </Card>
              </Stack>
            );
          })()
        ) : isTradeSelectPopup ? (
          <Stack spacing={1.5}>
            <Typography variant="subtitle1" sx={{ fontWeight: 800 }}>
              Select Trade Partner
            </Typography>

            <Stack direction="row" spacing={1} alignItems="center" sx={{ flexWrap: 'wrap' }}>
              <Typography variant="body2" sx={{ fontWeight: 700 }}>
                {seatLabel(tradeSelectPopup!.partner)}
              </Typography>
              <Chip size="small" label={`$${tradeSelectPopup!.partner_assets.money}`} color="success" variant="outlined" />
              <Chip
                size="small"
                label={`${tradeSelectPopup!.choice_index}/${tradeSelectPopup!.choice_count}`}
                variant="outlined"
              />
            </Stack>

            <Divider />

            <Typography variant="body2" sx={{ fontWeight: 700 }}>
              Properties
            </Typography>

            {(tradeSelectPopup!.partner_assets.properties || []).length ? (
              <Stack spacing={1}>
                {tradeSelectPopup!.partner_assets.properties.map((p) => (
                  <Card key={`tp-${p.idx}`} variant="outlined" sx={{ borderColor: p.color || 'divider' }}>
                    <CardContent sx={{ py: 1, '&:last-child': { pb: 1 } }}>
                      <Typography variant="body2">{p.name || `#${p.idx}`}</Typography>
                      {(p.mortgaged || p.houses > 0) && (
                        <Typography variant="caption" color="text.secondary">
                          {p.mortgaged ? 'Mortgaged' : p.houses > 0 ? `Houses: ${p.houses}` : ''}
                        </Typography>
                      )}
                    </CardContent>
                  </Card>
                ))}
              </Stack>
            ) : (
              <Typography variant="body2" color="text.secondary">
                No properties.
              </Typography>
            )}

            <Typography variant="caption" color="text.secondary">
              Use ◄/► to change player, Select to continue, or Cancel.
            </Typography>
          </Stack>
        ) : (
          <Stack spacing={1}>
            {(
              (snapshot.popup?.line_items && snapshot.popup.line_items.length
                ? snapshot.popup.line_items
                : (snapshot.popup?.lines || []).map((t) => ({ text: t, color: undefined })))
            ).map((line, i) => (
              <Typography
                key={i}
                variant="body2"
                sx={{
                  color: allowPopupLineColor ? line.color || 'text.primary' : 'text.primary',
                  fontWeight: allowPopupLineColor && line.color ? 600 : 400,
                }}
              >
                {line.text}
              </Typography>
            ))}
          </Stack>
        )}
      </DialogContent>

      <DialogActions sx={{ px: 2, pb: 2, pt: 1 }}>
        {snapshot.popup?.popup_type === 'mortgage' && snapshot.popup?.deed_detail ? (
          (() => {
            const deed = snapshot.popup!.deed_detail!;
            const buttons = snapshot.popup?.buttons || [];
            const leftBtn = buttons.find((b) => b.id === 'popup_0');
            const midBtn = buttons.find((b) => b.id === 'popup_1');
            const rightBtn = buttons.find((b) => b.id === 'popup_2');

            const scrollIndex = typeof deed.scroll_index === 'number' ? deed.scroll_index : null;
            const scrollTotal = typeof deed.scroll_total === 'number' ? deed.scroll_total : null;
            const canPrev = !!(scrollIndex && scrollTotal && scrollIndex > 1);
            const canNext = !!(scrollIndex && scrollTotal && scrollIndex < scrollTotal);

            const mortgageText = midBtn?.text || (deed.mortgaged ? 'Unmortgage' : 'Mortgage');
            const mortgageEnabled = !!midBtn?.enabled;

            return (
              <Box
                sx={{
                  width: '100%',
                  display: 'grid',
                  gridTemplateColumns: '1fr 1fr 1fr',
                  gridAutoRows: 'auto',
                  gap: 1,
                  alignItems: 'center',
                }}
              >
                <Box sx={{ justifySelf: 'start' }}>
                  <Button
                    variant="contained"
                    disabled={!canPrev || !leftBtn}
                    onClick={() => leftBtn && send({ type: 'click_button', id: leftBtn.id })}
                    sx={{ minWidth: 56 }}
                  >
                    ◄
                  </Button>
                </Box>

                <Box sx={{ justifySelf: 'center' }}>
                  <Button
                    variant="contained"
                    disabled={!mortgageEnabled || !midBtn}
                    onClick={() => midBtn && send({ type: 'click_button', id: midBtn.id })}
                    sx={{ minWidth: 160 }}
                  >
                    {mortgageText}
                  </Button>
                </Box>

                <Box sx={{ justifySelf: 'end' }}>
                  <Button
                    variant="contained"
                    disabled={!canNext || !rightBtn}
                    onClick={() => rightBtn && send({ type: 'click_button', id: rightBtn.id })}
                    sx={{ minWidth: 56 }}
                  >
                    ►
                  </Button>
                </Box>

                <Box sx={{ gridColumn: '2 / 3', justifySelf: 'center' }}>
                  <Button
                    variant="contained"
                    color="inherit"
                    onClick={() => send({ type: 'click_button', id: 'popup_close' })}
                    sx={{ minWidth: 160 }}
                  >
                    Close
                  </Button>
                </Box>
              </Box>
            );
          })()
        ) : isTradeSelectPopup ? (
          (() => {
            const tradeSelect = snapshot.popup!.trade_select!;
            const buttons = snapshot.popup?.buttons || [];
            const leftBtn = buttons.find((b) => b.id === 'popup_0');
            const selectBtn = buttons.find((b) => b.id === 'popup_1');
            const rightBtn = buttons.find((b) => b.id === 'popup_2');

            const canPrev = tradeSelect.choice_index > 1;
            const canNext = tradeSelect.choice_index < tradeSelect.choice_count;
            const canSelect = !!selectBtn?.enabled;

            return (
              <Box
                sx={{
                  width: '100%',
                  display: 'grid',
                  gridTemplateColumns: '1fr 1fr 1fr',
                  gridAutoRows: 'auto',
                  gap: 1,
                  alignItems: 'center',
                }}
              >
                <Box sx={{ justifySelf: 'start' }}>
                  <Button
                    variant="contained"
                    disabled={!canPrev || !leftBtn}
                    onClick={() => leftBtn && send({ type: 'click_button', id: leftBtn.id })}
                    sx={{ minWidth: 56 }}
                  >
                    ◄
                  </Button>
                </Box>

                <Box sx={{ justifySelf: 'center' }}>
                  <Button
                    variant="contained"
                    disabled={!canSelect || !selectBtn}
                    onClick={() => selectBtn && send({ type: 'click_button', id: selectBtn.id })}
                    sx={{ minWidth: 160 }}
                  >
                    Select
                  </Button>
                </Box>

                <Box sx={{ justifySelf: 'end' }}>
                  <Button
                    variant="contained"
                    disabled={!canNext || !rightBtn}
                    onClick={() => rightBtn && send({ type: 'click_button', id: rightBtn.id })}
                    sx={{ minWidth: 56 }}
                  >
                    ►
                  </Button>
                </Box>

                <Box sx={{ gridColumn: '2 / 3', justifySelf: 'center' }}>
                  <Button
                    variant="contained"
                    color="inherit"
                    onClick={() => send({ type: 'click_button', id: 'popup_cancel' })}
                    sx={{ minWidth: 160 }}
                  >
                    Cancel
                  </Button>
                </Box>
              </Box>
            );
          })()
        ) : (
          <Box
            sx={{
              width: '100%',
              display: 'flex',
              flexWrap: 'wrap',
              gap: 1,
              justifyContent: 'flex-end',
            }}
          >
            {(snapshot.popup?.buttons || []).map((b) => (
              <Button
                key={b.id}
                variant="contained"
                disabled={!b.enabled}
                onClick={() => send({ type: 'click_button', id: b.id })}
                sx={{ flex: '1 1 140px' }}
              >
                {b.text}
              </Button>
            ))}
          </Box>
        )}
      </DialogActions>
    </Dialog>
  );
}

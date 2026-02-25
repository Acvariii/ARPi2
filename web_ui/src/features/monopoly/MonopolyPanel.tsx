import React, { useMemo } from 'react';
import {
  Box,
  Button,
  Chip,
  Divider,
  LinearProgress,
  Paper,
  Stack,
  Typography,
} from '@mui/material';
import type { Snapshot } from '../../types';
import GameBanner from '../../components/GameBanner';

/* ─── Space names for position display ──────────────────────────── */
const MONOPOLY_SPACES = [
  'Go', 'Mediterranean Ave', 'Community Chest', 'Baltic Ave', 'Income Tax',
  'Reading Railroad', 'Oriental Ave', 'Chance', 'Vermont Ave', 'Connecticut Ave',
  'Just Visiting / Jail', 'St. Charles Place', 'Electric Company', 'States Ave', 'Virginia Ave',
  'Pennsylvania Railroad', 'St. James Place', 'Community Chest', 'Tennessee Ave', 'New York Ave',
  'Free Parking', 'Kentucky Ave', 'Chance', 'Indiana Ave', 'Illinois Ave',
  'B&O Railroad', 'Atlantic Ave', 'Ventnor Ave', 'Water Works', 'Marvin Gardens',
  'Go To Jail', 'Pacific Ave', 'N. Carolina Ave', 'Community Chest', 'Pennsylvania Ave',
  'Short Line Railroad', 'Chance', 'Park Place', 'Luxury Tax', 'Boardwalk',
];

/* ─── Property group colors ─────────────────────────────────────── */
const GROUP_COLORS: Record<string, { bg: string; fg: string }> = {
  brown: { bg: '#8B4513', fg: '#fff' },
  lblue: { bg: '#87CEEB', fg: '#000' },
  pink: { bg: '#D81B60', fg: '#fff' },
  orange: { bg: '#FF9800', fg: '#000' },
  red: { bg: '#F44336', fg: '#fff' },
  yellow: { bg: '#FDD835', fg: '#000' },
  green: { bg: '#4CAF50', fg: '#fff' },
  dblue: { bg: '#1A237E', fg: '#fff' },
  railroad: { bg: '#333', fg: '#fff' },
  utility: { bg: '#9E9E9E', fg: '#000' },
};

/* ─── Fallback color lookup by property index ───────────────────── */
const PROP_COLOR: Record<number, { bg: string; fg: string }> = {
  1: { bg: '#8B4513', fg: '#fff' }, 3: { bg: '#8B4513', fg: '#fff' },
  6: { bg: '#87CEEB', fg: '#000' }, 8: { bg: '#87CEEB', fg: '#000' }, 9: { bg: '#87CEEB', fg: '#000' },
  11: { bg: '#D81B60', fg: '#fff' }, 13: { bg: '#D81B60', fg: '#fff' }, 14: { bg: '#D81B60', fg: '#fff' },
  16: { bg: '#FF9800', fg: '#000' }, 18: { bg: '#FF9800', fg: '#000' }, 19: { bg: '#FF9800', fg: '#000' },
  21: { bg: '#F44336', fg: '#fff' }, 23: { bg: '#F44336', fg: '#fff' }, 24: { bg: '#F44336', fg: '#fff' },
  26: { bg: '#FDD835', fg: '#000' }, 27: { bg: '#FDD835', fg: '#000' }, 29: { bg: '#FDD835', fg: '#000' },
  31: { bg: '#4CAF50', fg: '#fff' }, 32: { bg: '#4CAF50', fg: '#fff' }, 34: { bg: '#4CAF50', fg: '#fff' },
  37: { bg: '#1A237E', fg: '#fff' }, 39: { bg: '#1A237E', fg: '#fff' },
  5: { bg: '#333', fg: '#fff' }, 15: { bg: '#333', fg: '#fff' }, 25: { bg: '#333', fg: '#fff' }, 35: { bg: '#333', fg: '#fff' },
  12: { bg: '#9E9E9E', fg: '#000' }, 28: { bg: '#9E9E9E', fg: '#000' },
};

function getColor(prop: { idx: number; color?: string | null; group?: string | null }) {
  if (prop.color) return { bg: prop.color, fg: '#fff' };
  if (prop.group && GROUP_COLORS[prop.group]) return GROUP_COLORS[prop.group];
  return PROP_COLOR[prop.idx] ?? { bg: '#9E9E9E', fg: '#000' };
}

/* ─── Token emojis matching the C# backend ──────────────────────── */
const TOKEN_EMOJIS = ['🎩', '🚗', '🐕', '👢', '🚢', '🔔', '🎲', '⭐'];

/* ─── Dice face component ───────────────────────────────────────── */
const DICE_DOTS: Record<number, [number, number][]> = {
  1: [[50, 50]],
  2: [[25, 25], [75, 75]],
  3: [[25, 25], [50, 50], [75, 75]],
  4: [[25, 25], [75, 25], [25, 75], [75, 75]],
  5: [[25, 25], [75, 25], [50, 50], [25, 75], [75, 75]],
  6: [[25, 20], [75, 20], [25, 50], [75, 50], [25, 80], [75, 80]],
};

function DiceFace({ value, size = 48 }: { value: number; size?: number }) {
  const dots = DICE_DOTS[value] ?? [];
  return (
    <Box
      sx={{
        width: size,
        height: size,
        bgcolor: '#FAFAFA',
        borderRadius: '8px',
        border: '2px solid #424242',
        boxShadow: '2px 3px 6px rgba(0,0,0,.25), inset 0 1px 0 rgba(255,255,255,.6)',
        position: 'relative',
        flexShrink: 0,
      }}
    >
      {dots.map(([x, y], i) => (
        <Box
          key={i}
          sx={{
            position: 'absolute',
            left: `${x}%`,
            top: `${y}%`,
            transform: 'translate(-50%,-50%)',
            width: size * 0.17,
            height: size * 0.17,
            borderRadius: '50%',
            bgcolor: '#212121',
          }}
        />
      ))}
    </Box>
  );
}

/* ─── Property chip with houses/mortgage indicator ──────────────── */
function PropChip({ prop }: {
  prop: { idx: number; name: string; color?: string | null; group?: string | null; houses?: number; mortgaged?: boolean };
}) {
  const c = getColor(prop);
  const houses = prop.houses ?? 0;
  const isHotel = houses === 5;
  const mortgaged = !!prop.mortgaged;

  let indicator = '';
  if (mortgaged) indicator = ' Ⓜ';
  else if (isHotel) indicator = ' 🏨';
  else if (houses > 0) indicator = ' ' + '🏠'.repeat(houses);

  return (
    <Chip
      label={`${prop.name}${indicator}`}
      size="small"
      sx={{
        bgcolor: mortgaged ? '#616161' : c.bg,
        color: mortgaged ? '#bbb' : c.fg,
        fontWeight: 700,
        fontSize: '0.65rem',
        height: 22,
        textDecoration: mortgaged ? 'line-through' : undefined,
        opacity: mortgaged ? 0.7 : 1,
        border: isHotel ? '1px solid #F44336' : houses > 0 ? '1px solid #4CAF50' : undefined,
      }}
    />
  );
}

/* ─── Deed card for mortgage / buy popups ───────────────────────── */
function DeedCard({ deed }: {
  deed: NonNullable<NonNullable<Snapshot['popup']>['deed_detail']>;
}) {
  const rentLabels = ['Rent', '1 House', '2 Houses', '3 Houses', '4 Houses', 'Hotel'];
  const headerColor = deed.color || '#333';
  return (
    <Paper
      elevation={6}
      sx={{
        width: '100%',
        maxWidth: 280,
        mx: 'auto',
        borderRadius: 2,
        overflow: 'hidden',
        border: '3px solid #222',
        bgcolor: '#FFFDE7',
      }}
    >
      {/* Color header */}
      <Box sx={{ bgcolor: headerColor, py: 1, px: 1.5, textAlign: 'center' }}>
        <Typography variant="caption" sx={{ color: '#fff', fontWeight: 900, letterSpacing: 1, textTransform: 'uppercase', fontSize: '0.85rem' }}>
          TITLE DEED
        </Typography>
        <Typography variant="h6" sx={{ color: '#fff', fontWeight: 900, lineHeight: 1.1 }}>
          {deed.name}
        </Typography>
      </Box>
      {/* Body */}
      <Box sx={{ p: 1.5 }}>
        {deed.rent_tiers?.length ? (
          <Stack spacing={0.25}>
            {deed.rent_tiers.map((rent, i) => (
              <Stack key={i} direction="row" justifyContent="space-between">
                <Typography variant="caption" sx={{ fontWeight: i === deed.houses ? 800 : 400, color: i === deed.houses ? '#1B5E20' : '#333' }}>
                  {rentLabels[i] ?? `Tier ${i}`}
                </Typography>
                <Typography variant="caption" sx={{ fontWeight: i === deed.houses ? 800 : 400, color: i === deed.houses ? '#1B5E20' : '#333' }}>
                  ${rent}
                </Typography>
              </Stack>
            ))}
          </Stack>
        ) : deed.type === 'railroad' ? (
          <Typography variant="caption" display="block" sx={{ textAlign: 'center', my: 1, color: '#333' }}>
            Rent: $25 per railroad owned
          </Typography>
        ) : deed.type === 'utility' ? (
          <Typography variant="caption" display="block" sx={{ textAlign: 'center', my: 1, color: '#333' }}>
            Rent: 4× / 10× dice roll
          </Typography>
        ) : null}

        <Divider sx={{ my: 1 }} />
        <Stack spacing={0.25}>
          <Stack direction="row" justifyContent="space-between">
            <Typography variant="caption" sx={{ color: '#333' }}>Price</Typography>
            <Typography variant="caption" sx={{ color: '#333' }} fontWeight={700}>${deed.price}</Typography>
          </Stack>
          {!!deed.house_cost && (
            <Stack direction="row" justifyContent="space-between">
              <Typography variant="caption" sx={{ color: '#333' }}>Houses</Typography>
              <Typography variant="caption" sx={{ color: '#333' }} fontWeight={700}>${deed.house_cost} each</Typography>
            </Stack>
          )}
          <Stack direction="row" justifyContent="space-between">
            <Typography variant="caption" sx={{ color: '#333' }}>Mortgage</Typography>
            <Typography variant="caption" sx={{ color: '#333' }} fontWeight={700}>${deed.mortgage_value}</Typography>
          </Stack>
          {deed.mortgaged && (
            <Stack direction="row" justifyContent="space-between">
              <Typography variant="caption" color="error">Unmortgage</Typography>
              <Typography variant="caption" color="error" fontWeight={700}>${deed.unmortgage_cost}</Typography>
            </Stack>
          )}
        </Stack>
        {deed.mortgaged && (
          <Chip label="MORTGAGED" size="small" color="error" sx={{ mt: 1, width: '100%', fontWeight: 900 }} />
        )}
        {deed.scroll_index != null && deed.scroll_total != null && (
          <Typography variant="caption" display="block" textAlign="center" sx={{ mt: 1, color: '#888' }}>
            {deed.scroll_index} / {deed.scroll_total}
          </Typography>
        )}
      </Box>
    </Paper>
  );
}

/* ─── Trade asset list ──────────────────────────────────────────── */
function TradeAssetList({ label, money, props, selectedProps, selectedMoney, isOffer }:
  {
    label: string;
    money: number;
    props: Array<{ idx: number; name: string; color?: string | null; mortgaged: boolean; houses: number; tradable: boolean }>;
    selectedProps: number[];
    selectedMoney: number;
    isOffer: boolean;
  }) {
  return (
    <Box>
      <Typography variant="subtitle2" sx={{ fontWeight: 800, mb: 0.5 }}>
        {label}
      </Typography>
      <Typography variant="caption" color="text.secondary">
        💵 ${money.toLocaleString()} {selectedMoney > 0 && (
          <Chip label={`${isOffer ? '−' : '+'}$${selectedMoney}`} size="small"
            sx={{ height: 18, fontSize: '0.6rem', ml: 0.5, bgcolor: isOffer ? '#C62828' : '#2E7D32', color: '#fff' }} />
        )}
      </Typography>
      {props.length > 0 && (
        <Box sx={{ mt: 0.5, display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
          {props.map(p => {
            const selected = selectedProps.includes(p.idx);
            const c = getColor(p);
            return (
              <Chip
                key={p.idx}
                label={p.name}
                size="small"
                sx={{
                  bgcolor: selected ? c.bg : `${c.bg}44`,
                  color: selected ? c.fg : 'text.primary',
                  fontWeight: selected ? 900 : 500,
                  fontSize: '0.6rem',
                  height: 20,
                  border: selected ? `2px solid ${c.bg}` : '1px solid transparent',
                  opacity: p.tradable ? 1 : 0.4,
                }}
              />
            );
          })}
        </Box>
      )}
    </Box>
  );
}

/* ──────────────────────── Popup renderer ────────────────────────── */
function MonopolyPopup({ popup, seatLabel, send, playerColors }: {
  popup: NonNullable<Snapshot['popup']>;
  seatLabel: (seat: number) => string;
  send: (obj: unknown) => void;
  playerColors: string[];
}) {
  if (!popup.active) return null;
  const pt = popup.popup_type ?? '';

  /* ── Card popup (Chance / Community Chest) ── */
  if (pt === 'card') {
    const isChance = popup.lines?.some(l => l.toLowerCase().includes('chance'));
    const accent = isChance ? '#FF8F00' : '#1565C0';
    const emoji = isChance ? '❓' : '💰';
    return (
      <Paper elevation={8} sx={{
        p: 2, borderRadius: 2,
        border: `3px solid ${accent}`,
        bgcolor: `${accent}12`,
        animation: 'fadeInUp 0.3s ease-out',
      }}>
        <Typography variant="h6" align="center" sx={{ fontWeight: 900, color: accent, mb: 1 }}>
          {emoji} {isChance ? 'Chance' : 'Community Chest'} {emoji}
        </Typography>
        {popup.line_items?.map((li, i) => (
          <Typography key={i} variant="body1" align="center" sx={{ color: li.color || '#fff', fontWeight: 600 }}>
            {li.text}
          </Typography>
        ))}
        {!!popup.buttons?.length && (
          <Stack direction="row" spacing={1} justifyContent="center" sx={{ mt: 2 }}>
            {popup.buttons.map(b => (
              <Button key={b.id} variant="contained" disabled={!b.enabled}
                onClick={() => send({ type: 'click_button', id: b.id })}
                sx={{ bgcolor: accent, '&:hover': { bgcolor: accent }, fontWeight: 700 }}>
                {b.text}
              </Button>
            ))}
          </Stack>
        )}
      </Paper>
    );
  }

  /* ── Buy prompt ── */
  if (pt === 'buy_prompt') {
    return (
      <Paper elevation={8} sx={{ p: 2, borderRadius: 2, border: '2px solid #4CAF50', animation: 'fadeInUp 0.3s ease-out' }}>
        <Typography variant="h6" align="center" sx={{ fontWeight: 900, mb: 1 }}>
          🏠 Property Available!
        </Typography>
        {popup.line_items?.map((li, i) => (
          <Typography key={i} variant="body1" align="center" sx={{ color: li.color || '#fff', fontWeight: 600, mb: 0.25 }}>
            {li.text}
          </Typography>
        ))}
        {!!popup.buttons?.length && (
          <Stack direction="row" spacing={1} justifyContent="center" sx={{ mt: 2 }}>
            {popup.buttons.map(b => (
              <Button key={b.id} variant="contained" disabled={!b.enabled}
                onClick={() => send({ type: 'click_button', id: b.id })}
                color={b.text.toLowerCase().includes('buy') ? 'success' : 'error'}
                sx={{ fontWeight: 700, minWidth: 100 }}>
                {b.text}
              </Button>
            ))}
          </Stack>
        )}
      </Paper>
    );
  }

  /* ── Auction ── */
  if (pt === 'auction') {
    return (
      <Paper elevation={8} sx={{ p: 2, borderRadius: 2, border: '2px solid #FF9800', bgcolor: '#FFF3E022', animation: 'fadeInUp 0.3s ease-out' }}>
        <Typography variant="h6" align="center" sx={{ fontWeight: 900, color: '#FF9800', mb: 1 }}>
          🔨 Auction
        </Typography>
        {popup.line_items?.map((li, i) => (
          <Typography key={i} variant="body1" align="center" sx={{ color: li.color || '#fff', fontWeight: 600 }}>
            {li.text}
          </Typography>
        ))}
        {!!popup.buttons?.length && (
          <Stack direction="row" spacing={1} justifyContent="center" flexWrap="wrap" useFlexGap sx={{ mt: 2 }}>
            {popup.buttons.map(b => (
              <Button key={b.id} variant="contained" size="small" disabled={!b.enabled}
                onClick={() => send({ type: 'click_button', id: b.id })}
                sx={{ fontWeight: 700, minWidth: 80 }}>
                {b.text}
              </Button>
            ))}
          </Stack>
        )}
      </Paper>
    );
  }

  /* ── Mortgage / Deed detail ── */
  if (pt === 'mortgage' && popup.deed_detail) {
    return (
      <Paper elevation={8} sx={{ p: 2, borderRadius: 2, border: '2px solid #9C27B0', animation: 'fadeInUp 0.3s ease-out' }}>
        <Typography variant="subtitle1" align="center" sx={{ fontWeight: 800, mb: 1 }}>
          📜 Property Management
        </Typography>
        <DeedCard deed={popup.deed_detail} />
        {!!popup.buttons?.length && (
          <Stack direction="row" spacing={1} justifyContent="center" flexWrap="wrap" useFlexGap sx={{ mt: 2 }}>
            {popup.buttons.map(b => (
              <Button key={b.id} variant="contained" size="small" disabled={!b.enabled}
                onClick={() => send({ type: 'click_button', id: b.id })}
                sx={{ fontWeight: 700, minWidth: 70 }}>
                {b.text}
              </Button>
            ))}
          </Stack>
        )}
      </Paper>
    );
  }

  /* ── Trade partner selection ── */
  if (pt === 'trade_select' && popup.trade_select) {
    const ts = popup.trade_select;
    const partnerColor = playerColors[ts.partner % playerColors.length];
    return (
      <Paper elevation={8} sx={{ p: 2, borderRadius: 2, border: `2px solid ${partnerColor}`, animation: 'fadeInUp 0.3s ease-out' }}>
        <Typography variant="h6" align="center" sx={{ fontWeight: 900, mb: 1 }}>
          🤝 Select Trade Partner
        </Typography>
        <Paper variant="outlined" sx={{ p: 1.5, borderColor: partnerColor, borderWidth: 2, mb: 1.5 }}>
          <Typography variant="body1" align="center" sx={{ fontWeight: 800, color: partnerColor }}>
            {ts.partner_name} ({ts.choice_index}/{ts.choice_count})
          </Typography>
          <Typography variant="caption" display="block" align="center" sx={{ color: 'text.secondary' }}>
            💵 ${ts.partner_assets.money.toLocaleString()} · {ts.partner_assets.properties.length} properties
          </Typography>
          {ts.partner_assets.properties.length > 0 && (
            <Box sx={{ mt: 0.75, display: 'flex', flexWrap: 'wrap', gap: 0.5, justifyContent: 'center' }}>
              {ts.partner_assets.properties.slice(0, 8).map(p => {
                const c = getColor(p);
                return <Chip key={p.idx} label={p.name} size="small"
                  sx={{ bgcolor: c.bg, color: c.fg, fontWeight: 700, fontSize: '0.6rem', height: 18 }} />;
              })}
              {ts.partner_assets.properties.length > 8 && (
                <Chip label={`+${ts.partner_assets.properties.length - 8} more`} size="small" sx={{ height: 18, fontSize: '0.6rem' }} />
              )}
            </Box>
          )}
        </Paper>
        {!!popup.buttons?.length && (
          <Stack direction="row" spacing={1} justifyContent="center" flexWrap="wrap" useFlexGap>
            {popup.buttons.map(b => (
              <Button key={b.id} variant="contained" size="small" disabled={!b.enabled}
                onClick={() => send({ type: 'click_button', id: b.id })}
                sx={{ fontWeight: 700, minWidth: 70 }}>
                {b.text}
              </Button>
            ))}
          </Stack>
        )}
      </Paper>
    );
  }

  /* ── Trade edit / review ── */
  if ((pt === 'trade_web_edit' || pt === 'trade_web_response' || pt === 'trade_response' || pt === 'trade_detail') && popup.trade) {
    const t = popup.trade;
    const initColor = playerColors[t.initiator % playerColors.length];
    const partColor = playerColors[t.partner % playerColors.length];
    const isReview = pt === 'trade_web_response' || pt === 'trade_response';
    return (
      <Paper elevation={8} sx={{ p: 2, borderRadius: 2, border: '2px solid #FF9800', animation: 'fadeInUp 0.3s ease-out' }}>
        <Typography variant="h6" align="center" sx={{ fontWeight: 900, color: '#FF9800', mb: 1 }}>
          🤝 {isReview ? 'Trade Offer' : 'Build Trade'}
        </Typography>
        <Stack spacing={1.5}>
          {/* Initiator's offer */}
          <Box sx={{ p: 1, borderRadius: 1, bgcolor: `${initColor}18`, border: `1px solid ${initColor}44` }}>
            <TradeAssetList
              label={`${seatLabel(t.initiator)} offers:`}
              money={t.initiator_assets.money}
              props={t.initiator_assets.properties}
              selectedProps={t.offer.properties}
              selectedMoney={t.offer.money}
              isOffer={true}
            />
          </Box>
          <Typography variant="body2" align="center" sx={{ fontWeight: 700 }}>⇅</Typography>
          {/* Partner's side */}
          <Box sx={{ p: 1, borderRadius: 1, bgcolor: `${partColor}18`, border: `1px solid ${partColor}44` }}>
            <TradeAssetList
              label={`${seatLabel(t.partner)} gives:`}
              money={t.partner_assets.money}
              props={t.partner_assets.properties}
              selectedProps={t.request.properties}
              selectedMoney={t.request.money}
              isOffer={false}
            />
          </Box>
        </Stack>
        {/* Popup text lines (instructions) */}
        {popup.line_items?.filter(l => l.text.trim()).map((li, i) => (
          <Typography key={i} variant="caption" display="block" align="center" sx={{ mt: 0.5, color: li.color || 'text.secondary' }}>
            {li.text}
          </Typography>
        ))}
        {!!popup.buttons?.length && (
          <Stack direction="row" spacing={1} justifyContent="center" flexWrap="wrap" useFlexGap sx={{ mt: 2 }}>
            {popup.buttons.map(b => (
              <Button key={b.id} variant="contained" size="small" disabled={!b.enabled}
                onClick={() => send({ type: 'click_button', id: b.id })}
                color={b.text.toLowerCase().includes('accept') ? 'success' : b.text.toLowerCase().includes('decline') || b.text.toLowerCase().includes('cancel') ? 'error' : 'primary'}
                sx={{ fontWeight: 700, minWidth: 80 }}>
                {b.text}
              </Button>
            ))}
          </Stack>
        )}
      </Paper>
    );
  }

  /* ── Build / generic info popup ── */
  return (
    <Paper elevation={8} sx={{ p: 2, borderRadius: 2, border: '2px solid #42A5F5', animation: 'fadeInUp 0.3s ease-out' }}>
      {popup.line_items?.map((li, i) => (
        <Typography key={i} variant="body1" align="center" sx={{ color: li.color || '#fff', fontWeight: 600 }}>
          {li.text}
        </Typography>
      ))}
      {!!popup.buttons?.length && (
        <Stack direction="row" spacing={1} justifyContent="center" flexWrap="wrap" useFlexGap sx={{ mt: 2 }}>
          {popup.buttons.map(b => (
            <Button key={b.id} variant="contained" size="small" disabled={!b.enabled}
              onClick={() => send({ type: 'click_button', id: b.id })}
              sx={{ fontWeight: 700, minWidth: 70 }}>
              {b.text}
            </Button>
          ))}
        </Stack>
      )}
    </Paper>
  );
}

/* ════════════════════════ Main component ════════════════════════ */

type Props = {
  snapshot: Snapshot;
  seatLabel: (seat: number) => string;
  send: (obj: unknown) => void;
  playerColors: string[];
};

export default function MonopolyPanel({ snapshot, seatLabel, send, playerColors }: Props): React.ReactElement {
  if (snapshot.server_state !== 'monopoly' || !snapshot.monopoly) return <></>;

  const mono = snapshot.monopoly;
  const turnSeat = typeof mono.current_turn_seat === 'number' ? mono.current_turn_seat : null;
  const popup = snapshot.popup;
  const popupActive = !!popup?.active;

  /* ── Sorted players (current turn first, then by index) ── */
  const sortedPlayers = useMemo(() => {
    if (!mono.players) return [];
    return [...mono.players].sort((a, b) => {
      if (a.player_idx === turnSeat) return -1;
      if (b.player_idx === turnSeat) return 1;
      return a.player_idx - b.player_idx;
    });
  }, [mono.players, turnSeat]);

  /* ── Group properties by color group for compact display ── */
  const groupProperties = (props: Array<{ idx: number; name: string; color?: string | null; group?: string | null; houses?: number; mortgaged?: boolean }>) => {
    const groups: Record<string, typeof props> = {};
    for (const p of props) {
      const g = p.group || 'other';
      (groups[g] ??= []).push(p);
    }
    return groups;
  };

  return (
    <Stack spacing={1.5} sx={{ animation: 'fadeInUp 0.4s ease-out' }}>
      <GameBanner game="monopoly" />

      {/* ── Free Parking Pot ── */}
      {(mono.free_parking_pot ?? 0) > 0 && (
        <Paper variant="outlined" sx={{ p: 0.75, textAlign: 'center', bgcolor: '#1B5E2018', borderColor: '#4CAF50' }}>
          <Typography variant="caption" sx={{ fontWeight: 700, color: '#4CAF50' }}>
            🅿️ Free Parking Pot: <b>${(mono.free_parking_pot ?? 0).toLocaleString()}</b>
          </Typography>
        </Paper>
      )}

      {/* ── Dice display + Turn indicator ── */}
      <Paper
        variant="outlined"
        sx={{
          p: 1.25,
          borderColor: turnSeat !== null ? playerColors[turnSeat % playerColors.length] : '#555',
          borderWidth: 2,
          bgcolor: turnSeat !== null ? `${playerColors[turnSeat % playerColors.length]}15` : 'background.paper',
        }}
      >
        <Stack direction="row" justifyContent="center" alignItems="center" spacing={2}>
          {mono.dice_values && (
            <Stack direction="row" spacing={0.75} alignItems="center">
              <DiceFace value={mono.dice_values[0]} size={40} />
              <DiceFace value={mono.dice_values[1]} size={40} />
              {mono.dice_values[0] === mono.dice_values[1] && (
                <Chip label="DOUBLES!" size="small" color="warning" sx={{ fontWeight: 900, fontSize: '0.65rem', height: 20, animation: 'badgePop 0.3s ease-out' }} />
              )}
            </Stack>
          )}
          {turnSeat !== null && (
            <Typography variant="body1" sx={{ fontWeight: 800, color: playerColors[turnSeat % playerColors.length] }}>
              {TOKEN_EMOJIS[turnSeat] ?? '●'} {seatLabel(turnSeat)}&apos;s Turn
            </Typography>
          )}
        </Stack>
      </Paper>

      {/* ── Popup UI ── */}
      {popupActive && popup && (
        <MonopolyPopup popup={popup} seatLabel={seatLabel} send={send} playerColors={playerColors} />
      )}

      {/* ── Action buttons (only when no popup) ── */}
      {!!snapshot.panel_buttons?.length && !popupActive && (
        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
          {snapshot.panel_buttons.map((b, bIdx) => (
            <Button
              key={b.id}
              variant="contained"
              size="medium"
              disabled={!b.enabled}
              onClick={() => send({ type: 'click_button', id: b.id })}
              sx={{
                flex: '1 1 auto',
                minWidth: 100,
                fontWeight: 700,
                fontSize: '0.85rem',
                borderRadius: 2,
                textTransform: 'none',
                animation: `bounceIn 0.35s ease-out ${bIdx * 0.05}s both`,
              }}
            >
              {b.id === 'action' && '🎲 '}{b.id === 'trade' && '🤝 '}{b.id === 'build' && '🏗️ '}{b.id === 'mortgage' && '📜 '}
              {b.text || b.id}
            </Button>
          ))}
        </Stack>
      )}

      {/* ── Players ── */}
      {sortedPlayers.length > 0 && (
        <Stack spacing={1}>
          {sortedPlayers.map((p) => {
            const isTurn = p.player_idx === turnSeat;
            const color = playerColors[p.player_idx % playerColors.length];
            const pos = typeof p.position === 'number' ? p.position : null;
            const inJail = !!p.in_jail;
            const isBankrupt = !!p.is_bankrupt;
            const spaceName = pos !== null ? (MONOPOLY_SPACES[pos] ?? `Space ${pos}`) : null;
            const emoji = TOKEN_EMOJIS[p.player_idx] ?? '●';
            const grouped = groupProperties(p.properties);
            const netWorth = p.net_worth ?? p.money;

            if (isBankrupt) {
              return (
                <Paper key={p.player_idx} variant="outlined" sx={{ p: 1, opacity: 0.5, borderColor: '#555' }}>
                  <Typography variant="body2" sx={{ fontWeight: 700, textDecoration: 'line-through' }}>
                    {emoji} {seatLabel(p.player_idx)} — BANKRUPT 💸
                  </Typography>
                </Paper>
              );
            }

            return (
              <Paper
                key={p.player_idx}
                variant="outlined"
                sx={{
                  p: 1.5,
                  borderColor: isTurn ? color : `${color}66`,
                  borderWidth: isTurn ? 2 : 1,
                  bgcolor: isTurn ? `${color}15` : 'background.paper',
                  animation: isTurn ? 'turnGlow 2s ease-in-out infinite' : `fadeInUp 0.3s ease-out ${p.player_idx * 0.07}s both`,
                  transition: 'all 0.3s ease',
                }}
              >
                {/* Header row */}
                <Stack direction="row" justifyContent="space-between" alignItems="flex-start">
                  <Stack spacing={0.25} flex={1} minWidth={0}>
                    <Stack direction="row" spacing={0.75} alignItems="center" flexWrap="wrap">
                      <Typography variant="body2" sx={{ fontWeight: 800, color }}>
                        {emoji} {seatLabel(p.player_idx)}
                      </Typography>
                      {isTurn && (
                        <Chip label="🎲 Turn" size="small" sx={{
                          height: 20, fontSize: '0.65rem', fontWeight: 700,
                          bgcolor: color, color: '#fff',
                          animation: 'badgePop 0.3s ease-out',
                        }} />
                      )}
                      {inJail && (
                        <Chip label="⛓ Jail" size="small" sx={{
                          height: 20, fontSize: '0.65rem', fontWeight: 700,
                          bgcolor: '#C62828', color: '#fff',
                        }} />
                      )}
                    </Stack>
                    {spaceName && (
                      <Typography variant="caption" color="text.secondary">
                        📍 {spaceName}
                      </Typography>
                    )}
                  </Stack>
                  <Box sx={{ textAlign: 'right', ml: 1, flexShrink: 0 }}>
                    <Typography variant="h6" sx={{
                      fontWeight: 900,
                      color: '#66BB6A',
                      lineHeight: 1.1,
                      fontFamily: 'monospace',
                    }}>
                      ${p.money.toLocaleString()}
                    </Typography>
                    <Typography variant="caption" sx={{ color: 'text.secondary', fontSize: '0.6rem' }}>
                      Net: ${netWorth.toLocaleString()}
                    </Typography>
                  </Box>
                </Stack>

                {/* Stats row */}
                {(p.properties.length > 0 || (p.jail_free_cards ?? 0) > 0) && (
                  <Stack direction="row" spacing={1} sx={{ mt: 0.5, mb: 0.25 }} flexWrap="wrap">
                    <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                      📜{p.properties.length}
                    </Typography>
                    {(p.houses ?? 0) > 0 && (
                      <Typography variant="caption" sx={{ color: '#4CAF50' }}>
                        🏠{p.houses}
                      </Typography>
                    )}
                    {(p.hotels ?? 0) > 0 && (
                      <Typography variant="caption" sx={{ color: '#F44336' }}>
                        🏨{p.hotels}
                      </Typography>
                    )}
                    {(p.jail_free_cards ?? 0) > 0 && (
                      <Typography variant="caption" sx={{ color: '#FF9800' }}>
                        🗝×{p.jail_free_cards}
                      </Typography>
                    )}
                  </Stack>
                )}

                {/* Properties grouped by color */}
                {p.properties.length > 0 && (
                  <Box sx={{ mt: 0.75 }}>
                    {Object.entries(grouped).map(([group, gProps]) => (
                      <Box key={group} sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.4, mb: 0.4 }}>
                        {gProps.map(pp => <PropChip key={pp.idx} prop={pp} />)}
                      </Box>
                    ))}
                  </Box>
                )}

                {/* Net worth bar */}
                {p.properties.length > 0 && (
                  <Box sx={{ mt: 0.75 }}>
                    <LinearProgress
                      variant="determinate"
                      value={Math.min(100, (netWorth / Math.max(1, ...sortedPlayers.map(sp => sp.net_worth ?? sp.money))) * 100)}
                      sx={{
                        height: 4, borderRadius: 2,
                        bgcolor: '#333',
                        '& .MuiLinearProgress-bar': { bgcolor: color, borderRadius: 2 },
                      }}
                    />
                  </Box>
                )}
              </Paper>
            );
          })}
        </Stack>
      )}

      {/* ── History ── */}
      {!!snapshot.history?.length && (
        <Paper variant="outlined" sx={{ p: 1.25, maxHeight: 200, overflow: 'auto', borderColor: '#444' }}>
          <Typography variant="subtitle2" gutterBottom sx={{ fontWeight: 800, color: 'text.secondary' }}>
            📋 Game Log
          </Typography>
          <Stack spacing={0.25}>
            {snapshot.history
              .slice()
              .reverse()
              .map((h, i) => (
                <Typography
                  key={i}
                  variant="caption"
                  color="text.secondary"
                  display="block"
                  sx={i === 0 ? { animation: 'slideInRight 0.3s ease-out', fontWeight: 700, color: 'text.primary' } : { fontSize: '0.7rem' }}
                >
                  {h}
                </Typography>
              ))}
          </Stack>
        </Paper>
      )}
    </Stack>
  );
}

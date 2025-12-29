import React from 'react';
import { Box, Typography } from '@mui/material';

type ParsedCard = {
  rank: string;
  suit: string;
  isRed: boolean;
};

const SUIT_MAP: Record<string, string> = {
  S: '♠',
  H: '♥',
  D: '♦',
  C: '♣',
  '♠': '♠',
  '♥': '♥',
  '♦': '♦',
  '♣': '♣',
};

function parseCard(card: string): ParsedCard {
  const t = (card || '').trim();
  if (!t) return { rank: '', suit: '', isRed: false };

  const rawSuit = t.slice(-1);
  const suit = SUIT_MAP[rawSuit] || rawSuit;

  let rank = t.slice(0, -1);
  if (rank === 'T') rank = '10';

  const isRed = suit === '♥' || suit === '♦';
  return { rank, suit, isRed };
}

export type PlayingCardSize = 'sm' | 'md' | 'lg';

export default function PlayingCard({
  card,
  faceDown,
  size = 'sm',
}: {
  card?: string;
  faceDown?: boolean;
  size?: PlayingCardSize;
}): React.ReactElement {
  const c = card ? parseCard(card) : { rank: '', suit: '', isRed: false };

  const dims =
    size === 'lg'
      ? { width: 72, height: 100, cornerFont: 'caption' as const, centerFont: 'h5' as const }
      : size === 'md'
        ? { width: 56, height: 78, cornerFont: 'caption' as const, centerFont: 'h6' as const }
        : { width: 46, height: 64, cornerFont: 'caption' as const, centerFont: 'h6' as const };

  const showFace = !!card && !faceDown;

  return (
    <Box
      sx={(theme) => ({
        width: dims.width,
        height: dims.height,
        border: 1,
        borderColor: 'divider',
        borderRadius: 1.25,
        bgcolor: showFace ? 'background.paper' : 'primary.main',
        color: showFace ? 'text.primary' : 'primary.contrastText',
        position: 'relative',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        userSelect: 'none',
        boxShadow: theme.shadows[1],
        overflow: 'hidden',
      })}
    >
      {!showFace ? (
        <>
          <Typography variant="h6" sx={{ fontWeight: 900, lineHeight: 1 }}>
            🂠
          </Typography>
          <Typography
            variant="caption"
            sx={{
              position: 'absolute',
              bottom: 4,
              right: 6,
              fontWeight: 800,
              opacity: 0.9,
              lineHeight: 1,
            }}
          >
            POKER
          </Typography>
        </>
      ) : (
        <>
          <Typography
            variant={dims.cornerFont}
            sx={{
              position: 'absolute',
              top: 4,
              left: 6,
              fontWeight: 900,
              color: c.isRed ? 'error.main' : 'text.primary',
              lineHeight: 1,
            }}
          >
            {c.rank}
            {c.suit}
          </Typography>

          <Typography
            variant={dims.cornerFont}
            sx={{
              position: 'absolute',
              bottom: 4,
              right: 6,
              fontWeight: 900,
              color: c.isRed ? 'error.main' : 'text.primary',
              lineHeight: 1,
              transform: 'rotate(180deg)',
              transformOrigin: 'center',
            }}
          >
            {c.rank}
            {c.suit}
          </Typography>

          <Typography
            variant={dims.centerFont}
            sx={{
              fontWeight: 900,
              color: c.isRed ? 'error.main' : 'text.primary',
              lineHeight: 1,
            }}
          >
            {c.suit}
          </Typography>
        </>
      )}
    </Box>
  );
}

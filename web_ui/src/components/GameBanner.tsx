import React from 'react';
import { Box, Typography } from '@mui/material';

export interface GameTheme {
  gradient: string;
  emoji: string;
  tagline: string;
  accentColor: string;
}

export const GAME_THEMES: Record<string, GameTheme> = {
  blackjack: {
    gradient: 'linear-gradient(135deg, #0a2e0a 0%, #0d4a0d 60%, #1a5c1a 100%)',
    emoji: '🃏',
    tagline: 'Casino Style · Beat the Dealer',
    accentColor: '#ffd700',
  },
  texas_holdem: {
    gradient: "linear-gradient(135deg, #082008 0%, #0d3a0d 60%, #1a4a1a 100%)",
    emoji: '🎰',
    tagline: "No Limit Texas Hold'em",
    accentColor: '#c8a96e',
  },
  uno: {
    gradient: 'linear-gradient(135deg, #3a0010 0%, #1a0050 50%, #001a60 100%)',
    emoji: '🎴',
    tagline: 'Wild · Draw Two · Reverse · Skip',
    accentColor: '#e3263a',
  },
  exploding_kittens: {
    gradient: 'linear-gradient(135deg, #1a0008 0%, #2a0010 50%, #3a1000 100%)',
    emoji: '💥',
    tagline: "Don't Draw the Exploding Kitten",
    accentColor: '#ff6b35',
  },
  monopoly: {
    gradient: 'linear-gradient(135deg, #0a2a0a 0%, #0d3a0d 60%, #1a2a00 100%)',
    emoji: '🏦',
    tagline: 'Buy · Build · Bankrupt Your Rivals',
    accentColor: '#d4af37',
  },
  unstable_unicorns: {
    gradient: 'linear-gradient(135deg, #1a0028 0%, #2a0040 60%, #3a0028 100%)',
    emoji: '🦄',
    tagline: 'Magical Chaos Awaits',
    accentColor: '#c060ff',
  },
  catan: {
    gradient: 'linear-gradient(135deg, #1a0e00 0%, #2a1800 60%, #3a2400 100%)',
    emoji: '🏝️',
    tagline: 'Settle · Build · Trade · Conquer',
    accentColor: '#c8a050',
  },
  risk: {
    gradient: 'linear-gradient(135deg, #000818 0%, #000a28 60%, #000c38 100%)',
    emoji: '⚔️',
    tagline: 'World Domination',
    accentColor: '#4060ff',
  },
  cluedo: {
    gradient: 'linear-gradient(135deg, #1a0800 0%, #2a1000 60%, #1a0008 100%)',
    emoji: '🔍',
    tagline: 'Who? What? Where?',
    accentColor: '#c80000',
  },
  dnd: {
    gradient: 'linear-gradient(135deg, #0a0818 0%, #0a0a28 60%, #180a28 100%)',
    emoji: '🐉',
    tagline: 'Dungeons & Dragons',
    accentColor: '#9b59b6',
  },
};

export function normalizeGameKey(game: string): string {
  const g = (game || '').toLowerCase().replace(/\s+/g, '_');
  if (g === "d&d" || g === 'dnd') return 'dnd';
  return g;
}

export function getGameTheme(game: string): GameTheme {
  return (
    GAME_THEMES[normalizeGameKey(game)] || {
      gradient: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)',
      emoji: '🎮',
      tagline: 'Board Game',
      accentColor: '#4a90d9',
    }
  );
}

function humanize(game: string): string {
  return game
    .replace(/_/g, ' ')
    .replace(/&/g, '&')
    .replace(/\b\w/g, (c) => c.toUpperCase())
    .replace('Texas Holdem', "Texas Hold'em")
    .replace('D&D', 'D&D');
}

export default function GameBanner({
  game,
  compact = false,
}: {
  game: string;
  compact?: boolean;
}): React.ReactElement {
  const theme = getGameTheme(game);

  return (
    <Box
      sx={{
        borderRadius: compact ? 1.5 : 2,
        overflow: 'hidden',
        background: theme.gradient,
        border: `1px solid ${theme.accentColor}55`,
        boxShadow: `0 0 20px ${theme.accentColor}18, inset 0 1px 0 ${theme.accentColor}28`,
        mb: compact ? 0 : 2,
        position: 'relative',
      }}
    >
      {/* Top shimmer line */}
      <Box
        sx={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          height: 2,
          background: `linear-gradient(90deg, transparent 0%, ${theme.accentColor}dd 50%, transparent 100%)`,
        }}
      />
      {/* Bottom shimmer line */}
      <Box
        sx={{
          position: 'absolute',
          bottom: 0,
          left: 0,
          right: 0,
          height: 1,
          background: `linear-gradient(90deg, transparent 0%, ${theme.accentColor}66 50%, transparent 100%)`,
          opacity: 0.4,
        }}
      />

      <Box sx={{ p: compact ? 1.25 : 2, display: 'flex', alignItems: 'center', gap: 1.5 }}>
        <Typography sx={{ fontSize: compact ? '2rem' : '2.8rem', lineHeight: 1, flexShrink: 0 }}>
          {theme.emoji}
        </Typography>
        <Box sx={{ minWidth: 0 }}>
          <Typography
            variant={compact ? 'subtitle1' : 'h6'}
            sx={{
              fontWeight: 800,
              color: theme.accentColor,
              lineHeight: 1.1,
              letterSpacing: 0.5,
              textTransform: 'uppercase',
              textShadow: `0 0 12px ${theme.accentColor}80`,
            }}
          >
            {humanize(game)}
          </Typography>
          {!compact && (
            <Typography
              variant="caption"
              sx={{ color: 'rgba(255,255,255,0.5)', letterSpacing: 0.4, display: 'block', mt: 0.25 }}
            >
              {theme.tagline}
            </Typography>
          )}
        </Box>
      </Box>
    </Box>
  );
}

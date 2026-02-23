import React, { useCallback, useMemo, useRef, useState } from 'react';
import { Box, Paper, Popover, Stack, Typography } from '@mui/material';
import { useTheme } from '@mui/material/styles';

/** Count visible grapheme clusters (emoji) in a string. */
function countGraphemes(s: string): number {
  if (typeof Intl !== 'undefined' && 'Segmenter' in Intl) {
    // Modern browsers — accurate grapheme segmentation
    const seg = new (Intl as any).Segmenter(undefined, { granularity: 'grapheme' });
    return [...seg.segment(s)].length;
  }
  // Fallback: count surrogate pairs + variation selectors as 1
  return [...s].filter((c) => c !== '\uFE0F').length;
}

export default function EmojiCardTile({
  emoji,
  title,
  corner,
  accent,
  isBack,
  onClick,
  enabled = true,
  width = 74,
  desc,
}: {
  emoji: string;
  title: string;
  corner: string;
  accent?: string;
  isBack?: boolean;
  onClick?: () => void;
  enabled?: boolean;
  width?: number;
  desc?: string;
}): React.ReactElement {
  const theme = useTheme();
  const clickable = !!onClick && enabled;
  const hasDesc = !!desc && desc.length > 0;

  // Detect multi-emoji and scale font size down accordingly
  const emojiCount = useMemo(() => countGraphemes(emoji), [emoji]);
  const emojiFontSize = emojiCount >= 3 ? '0.85rem' : emojiCount === 2 ? '1.1rem' : undefined; // default h5 ~1.5rem

  // --- Hover tooltip (desktop) ---
  const [hovered, setHovered] = useState(false);

  // --- Mobile info-tap state ---
  const [popAnchor, setPopAnchor] = useState<HTMLElement | null>(null);
  const longPressTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const didLongPress = useRef(false);
  const cardRef = useRef<HTMLDivElement>(null);

  const handlePointerDown = useCallback(
    (e: React.PointerEvent<HTMLDivElement>) => {
      if (!hasDesc) return;
      didLongPress.current = false;
      longPressTimer.current = setTimeout(() => {
        didLongPress.current = true;
        setPopAnchor(cardRef.current || e.currentTarget);
      }, 500);
    },
    [hasDesc],
  );

  const handlePointerUp = useCallback(() => {
    if (longPressTimer.current) {
      clearTimeout(longPressTimer.current);
      longPressTimer.current = null;
    }
  }, []);

  const handlePointerCancel = handlePointerUp;

  const handleClick = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      if (didLongPress.current) {
        didLongPress.current = false;
        e.stopPropagation();
        return;
      }
      if (clickable) onClick?.();
    },
    [clickable, onClick],
  );

  const handleInfoTap = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      e.stopPropagation();
      e.preventDefault();
      setPopAnchor(cardRef.current);
    },
    [],
  );

  // ── Tooltip bubble (desktop only — hidden on touch via media query) ──
  const tooltipEl = hasDesc && hovered ? (
    <Box
      sx={{
        position: 'absolute',
        bottom: '100%',
        left: '50%',
        transform: 'translateX(-50%)',
        mb: 1,
        zIndex: 1500,
        pointerEvents: 'none',
        minWidth: 180,
        maxWidth: 260,
        bgcolor: '#212121',
        color: '#fff',
        borderRadius: 2,
        p: 1.5,
        boxShadow: '0 4px 20px rgba(0,0,0,0.45)',
        // Hide on touch devices
        '@media (hover: none)': { display: 'none' },
        '&::after': {
          content: '""',
          position: 'absolute',
          top: '100%',
          left: '50%',
          transform: 'translateX(-50%)',
          border: '6px solid transparent',
          borderTopColor: '#212121',
        },
      }}
    >
      <Typography variant="subtitle2" sx={{ fontWeight: 900, color: '#fff' }}>
        {emoji} {title}
      </Typography>
      <Typography variant="caption" sx={{ color: accent || '#aaa', fontWeight: 700, textTransform: 'uppercase', display: 'block', mb: 0.5 }}>
        {corner}
      </Typography>
      <Typography variant="body2" sx={{ lineHeight: 1.35, color: '#eee' }}>
        {desc}
      </Typography>
    </Box>
  ) : null;

  return (
    <Box
      sx={{ position: 'relative', display: 'inline-block' }}
      onMouseEnter={() => hasDesc && setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      {tooltipEl}
      <Paper
        ref={cardRef}
        variant="outlined"
        onClick={handleClick}
        onPointerDown={handlePointerDown}
        onPointerUp={handlePointerUp}
        onPointerCancel={handlePointerCancel}
        sx={{
          width,
          aspectRatio: '5 / 7',
          borderRadius: 1.25,
          overflow: 'hidden',
          userSelect: 'none',
          cursor: clickable ? 'pointer' : hasDesc ? 'help' : 'default',
          opacity: clickable ? 1 : enabled === false && !hasDesc ? 0.45 : enabled === false ? 0.72 : 1,
          borderColor: clickable ? theme.palette.text.primary : 'divider',
          bgcolor: isBack ? theme.palette.primary.main : theme.palette.background.paper,
          color: theme.palette.text.primary,
          position: 'relative',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          transition: 'transform 0.18s ease, box-shadow 0.18s ease',
          '&:hover': hasDesc
            ? {
                transform: 'scale(1.07)',
                boxShadow: `0 0 12px 2px ${accent || theme.palette.primary.main}66`,
                zIndex: 2,
              }
            : undefined,
        }}
      >
        {/* Accent border */}
        <Box
          sx={{
            position: 'absolute',
            inset: 0,
            border: `2px solid ${accent || theme.palette.divider}`,
            borderRadius: 1.25,
            pointerEvents: 'none',
            opacity: 0.9,
          }}
        />

        {/* Corners */}
        <Box sx={{ position: 'absolute', top: 6, left: 7, lineHeight: 1 }}>
          <Typography variant="caption" sx={{ fontWeight: 900, color: isBack ? theme.palette.common.white : theme.palette.text.primary }}>
            {corner}
          </Typography>
        </Box>
        <Box sx={{ position: 'absolute', bottom: 6, right: 7, lineHeight: 1, transform: 'rotate(180deg)' }}>
          <Typography variant="caption" sx={{ fontWeight: 900, color: isBack ? theme.palette.common.white : theme.palette.text.primary }}>
            {corner}
          </Typography>
        </Box>

        <Stack spacing={0.5} alignItems="center" sx={{ px: 1, textAlign: 'center' }}>
          <Typography
            variant="h5"
            sx={{ lineHeight: 1, ...(emojiFontSize ? { fontSize: emojiFontSize } : {}) }}
          >
            {emoji}
          </Typography>
          <Typography
            variant="caption"
            sx={{
              fontWeight: 900,
              letterSpacing: 0.3,
              color: isBack ? theme.palette.common.white : theme.palette.text.secondary,
              lineHeight: 1.1,
            }}
          >
            {title}
          </Typography>
        </Stack>

        {/* Info "i" button — mobile / tablet only (hidden when hover is available) */}
        {hasDesc && (
          <Box
            onClick={handleInfoTap}
            onPointerDown={(e) => e.stopPropagation()}
            sx={{
              position: 'absolute',
              bottom: 4,
              left: 4,
              width: 18,
              height: 18,
              borderRadius: '50%',
              bgcolor: `${accent || theme.palette.primary.main}cc`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: 'pointer',
              fontSize: 11,
              fontWeight: 900,
              color: '#fff',
              lineHeight: 1,
              zIndex: 3,
              // Hide on devices that support hover (desktop)
              '@media (hover: hover)': { display: 'none' },
              '&:hover': { bgcolor: accent || theme.palette.primary.main },
            }}
          >
            i
          </Box>
        )}
      </Paper>

      {/* Popover for mobile info tap / long-press */}
      {hasDesc && (
        <Popover
          open={!!popAnchor}
          anchorEl={popAnchor}
          onClose={() => setPopAnchor(null)}
          anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
          transformOrigin={{ vertical: 'bottom', horizontal: 'center' }}
          disableRestoreFocus
          slotProps={{ paper: { sx: { p: 1.5, maxWidth: 260, borderRadius: 2, bgcolor: theme.palette.background.paper } } }}
        >
          <Typography variant="subtitle2" sx={{ fontWeight: 900, mb: 0.5 }}>
            {emoji} {title}
          </Typography>
          <Typography variant="caption" sx={{ color: accent || theme.palette.text.secondary, fontWeight: 700, textTransform: 'uppercase' }}>
            {corner}
          </Typography>
          <Typography variant="body2" sx={{ mt: 0.75, lineHeight: 1.4 }}>
            {desc}
          </Typography>
        </Popover>
      )}
    </Box>
  );
}

import React from 'react';
import { Button, Stack, Typography } from '@mui/material';
import GameBanner from '../../components/GameBanner';

type Props = {
  send: (obj: unknown) => void;
};

export default function DndDicePanel({ send }: Props): React.ReactElement {
  return (
    <>
      <GameBanner game="dnd" />
      <Typography variant="subtitle2" sx={{ mt: 2 }}>
        Dice
      </Typography>
      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} sx={{ mt: 1 }}>
        {[4, 6, 8, 10, 12, 20].map((sides) => (
          <Button key={sides} variant="contained" onClick={() => send({ type: 'dnd_roll_dice', sides })}>
            d{sides}
          </Button>
        ))}
      </Stack>
    </>
  );
}

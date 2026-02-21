using System;
using System.Collections.Generic;

namespace ARPi2.Sharp.Core;

/// <summary>
/// Player selection screen with 8 player slots in circular layout.
/// Port of Python core/player_selection.py.
/// </summary>
public class PlayerSelectionUI
{
    public int ScreenWidth, ScreenHeight;
    public bool[] Selected = new bool[8];
    public bool StartReady;

    private readonly (int X, int Y, int R)[] _slots; // centre + radius
    private readonly Dictionary<string, float> _hoverStarts = new();
    public (int X, int Y) StartButtonPos;
    public int StartButtonRadius = 80;

    public PlayerSelectionUI(int screenW, int screenH)
    {
        ScreenWidth = screenW; ScreenHeight = screenH;
        int sx = screenW / 4, sy = screenH / 3;
        int sr = 55;
        StartButtonPos = (screenW / 2, screenH / 2);

        _slots = new (int, int, int)[]
        {
            (sx * 1, screenH - sy / 2, sr),
            (sx * 2, screenH - sy / 2, sr),
            (sx * 3, screenH - sy / 2, sr),
            (sx * 1, sy / 2, sr),
            (sx * 2, sy / 2, sr),
            (sx * 3, sy / 2, sr),
            (sx / 2, screenH / 2, sr),
            (screenW - sx / 2, screenH / 2, sr),
        };
    }

    public int SelectedCount() { int n = 0; foreach (bool s in Selected) if (s) n++; return n; }
    public List<int> GetSelectedIndices()
    {
        var list = new List<int>();
        for (int i = 0; i < 8; i++) if (Selected[i]) list.Add(i);
        return list;
    }

    public void Reset() { Array.Fill(Selected, false); _hoverStarts.Clear(); StartReady = false; }

    public void UpdateWithInputs(List<(int X, int Y, bool Click)> inputs, float currentTime, int minPlayers = 2)
    {
        var active = new HashSet<string>();

        foreach (var (ix, iy, click) in inputs)
        {
            // Start button
            if (SelectedCount() >= minPlayers)
            {
                var (scx, scy) = StartButtonPos;
                float dist = MathF.Sqrt((ix - scx) * (ix - scx) + (iy - scy) * (iy - scy));
                if (dist <= StartButtonRadius)
                {
                    if (click) { StartReady = true; continue; }
                    string key = "start";
                    active.Add(key);
                    if (!_hoverStarts.ContainsKey(key)) _hoverStarts[key] = currentTime;
                    if (currentTime - _hoverStarts[key] >= GameConfig.HoverTimeThreshold)
                    {
                        StartReady = true;
                        _hoverStarts.Remove(key);
                    }
                    continue;
                }
            }

            // Player slots
            for (int i = 0; i < 8; i++)
            {
                var (scx, scy, sr) = _slots[i];
                float dist = MathF.Sqrt((ix - scx) * (ix - scx) + (iy - scy) * (iy - scy));
                if (dist > sr) continue;

                if (click) { if (i != 7) Selected[i] = !Selected[i]; break; }
                string key = $"slot_{i}";
                active.Add(key);
                if (!_hoverStarts.ContainsKey(key)) _hoverStarts[key] = currentTime;
                if (currentTime - _hoverStarts[key] >= GameConfig.HoverTimeThreshold)
                {
                    if (i != 7) Selected[i] = !Selected[i];
                    _hoverStarts.Remove(key);
                }
                break;
            }
        }

        // Remove stale hovers
        var stale = new List<string>();
        foreach (var k in _hoverStarts.Keys) if (!active.Contains(k)) stale.Add(k);
        foreach (var k in stale) _hoverStarts.Remove(k);
    }

    public void Draw(Renderer r)
    {
        // Draw slots
        for (int i = 0; i < 8; i++)
        {
            var (cx, cy, sr) = _slots[i];
            var col = GameConfig.PlayerColors[i];
            if (Selected[i])
            {
                r.DrawCircle(col, (cx, cy), sr, alpha: 200);
                r.DrawCircle((255, 255, 255), (cx, cy), sr, width: 3, alpha: 255);
            }
            else
            {
                r.DrawCircle((60, 60, 70), (cx, cy), sr, alpha: 120);
                r.DrawCircle(col, (cx, cy), sr, width: 2, alpha: 180);
            }
            r.DrawText($"P{i + 1}", cx, cy, fontSize: 22, color: (255, 255, 255),
                       anchorX: "center", anchorY: "center", bold: true);
        }

        // Start button
        if (SelectedCount() >= GameConfig.MinPlayers)
        {
            var (sx, sy) = StartButtonPos;
            r.DrawCircle((40, 180, 60), (sx, sy), StartButtonRadius, alpha: 220);
            r.DrawCircle((255, 215, 0), (sx, sy), StartButtonRadius, width: 3);
            r.DrawText("START", sx, sy, fontSize: 28, color: (255, 255, 255),
                       anchorX: "center", anchorY: "center", bold: true);
        }
    }
}

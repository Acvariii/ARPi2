using System;
using System.Net;
using System.Net.Sockets;
using QRCoder;

namespace ARPi2.Sharp.Core;

/// <summary>
/// Generates and renders a QR code on the MonoGame screen using primitive rectangles.
/// Uses QRCoder for the matrix generation, then draws it using the game Renderer.
/// </summary>
public static class QRCodeRenderer
{
    // Cache the join URL and matrix
    private static string? _cachedUrl;
    private static bool[,]? _cachedMatrix;
    private static double _cacheAge = 999;

    /// <summary>
    /// Detect the local LAN IP and build the join URL.
    /// </summary>
    public static string GetJoinUrl()
    {
        try
        {
            using var s = new Socket(AddressFamily.InterNetwork, SocketType.Dgram, ProtocolType.Udp);
            s.Connect("8.8.8.8", 80);
            string? localIp = (s.LocalEndPoint as IPEndPoint)?.Address.ToString();
            if (!string.IsNullOrEmpty(localIp))
                return $"http://{localIp}:{GameConfig.HttpPort}";
        }
        catch { }
        return $"http://localhost:{GameConfig.HttpPort}";
    }

    /// <summary>
    /// Get or create the QR code boolean matrix for the join URL.
    /// </summary>
    private static bool[,] GetMatrix()
    {
        string url = GetJoinUrl();
        if (_cachedMatrix != null && _cachedUrl == url && _cacheAge < 30.0)
            return _cachedMatrix;

        using var gen = new QRCodeGenerator();
        using var data = gen.CreateQrCode(url, QRCodeGenerator.ECCLevel.M);
        var modules = data.ModuleMatrix;
        int size = modules.Count;
        var matrix = new bool[size, size];
        for (int y = 0; y < size; y++)
            for (int x = 0; x < size; x++)
                matrix[y, x] = modules[y][x];

        _cachedUrl = url;
        _cachedMatrix = matrix;
        _cacheAge = 0;
        return matrix;
    }

    /// <summary>
    /// Draw the QR code at a specific position on screen.
    /// </summary>
    /// <param name="r">The renderer</param>
    /// <param name="centerX">Center X position</param>
    /// <param name="centerY">Center Y position</param>
    /// <param name="totalSize">Total pixel size of the QR code square</param>
    /// <param name="fgColor">Foreground (dark module) color</param>
    /// <param name="bgColor">Background (light module) color</param>
    /// <param name="alpha">Opacity</param>
    public static void Draw(Renderer r, int centerX, int centerY, int totalSize,
        (int R, int G, int B)? fgColor = null,
        (int R, int G, int B)? bgColor = null,
        int alpha = 255)
    {
        var fg = fgColor ?? (20, 20, 20);
        var bg = bgColor ?? (255, 255, 255);
        var matrix = GetMatrix();
        int modules = matrix.GetLength(0);
        if (modules == 0) return;

        int qrSize = totalSize;
        float cellSize = qrSize / (float)modules;
        int x0 = centerX - qrSize / 2;
        int y0 = centerY - qrSize / 2;

        // Background with padding
        int pad = (int)(cellSize * 2);
        r.DrawRect(bg, (x0 - pad, y0 - pad, qrSize + 2 * pad, qrSize + 2 * pad), alpha: alpha);

        // Draw dark modules
        for (int my = 0; my < modules; my++)
        {
            for (int mx = 0; mx < modules; mx++)
            {
                if (matrix[my, mx])
                {
                    int px = x0 + (int)(mx * cellSize);
                    int py = y0 + (int)(my * cellSize);
                    int pw = Math.Max(1, (int)MathF.Ceiling(cellSize));
                    int ph = Math.Max(1, (int)MathF.Ceiling(cellSize));
                    r.DrawRect(fg, (px, py, pw, ph), alpha: alpha);
                }
            }
        }
    }

    /// <summary>
    /// Draw a styled QR code panel with title and URL text below.
    /// Amazon Luna-style presentation with rounded-corner feel.
    /// </summary>
    public static void DrawQRPanel(Renderer r, int centerX, int centerY, int qrSize,
        string title = "SCAN TO JOIN",
        (int R, int G, int B)? accentColor = null)
    {
        var accent = accentColor ?? (255, 140, 0);
        string url = GetJoinUrl();

        int panelW = qrSize + 60;
        int panelH = qrSize + 110;
        int px = centerX - panelW / 2;
        int py = centerY - panelH / 2;

        // Panel shadow
        r.DrawRect((0, 0, 0), (px + 6, py + 6, panelW, panelH), alpha: 100);

        // Panel background — dark with subtle gradient
        r.DrawRect((18, 14, 22), (px, py, panelW, panelH), alpha: 240);

        // Top accent band
        r.DrawRect(accent, (px, py, panelW, 4), alpha: 220);

        // Border
        r.DrawRect(accent, (px, py, panelW, panelH), width: 2, alpha: 160);

        // Inner glow
        r.DrawRect((40, 30, 50), (px + 3, py + 3, panelW - 6, panelH - 6), width: 1, alpha: 60);

        // Title
        r.DrawText(title, centerX, py + 22, 14, accent, bold: true,
            anchorX: "center", anchorY: "center");

        // QR code (white bg, dark modules)
        int qrY = py + 44 + qrSize / 2;
        Draw(r, centerX, qrY, qrSize,
            fgColor: (15, 10, 20),
            bgColor: (250, 248, 240));

        // URL text below QR
        int urlY = qrY + qrSize / 2 + 24;
        // Truncate URL for display
        string displayUrl = url.Replace("http://", "");
        r.DrawText(displayUrl, centerX, urlY, 11, (180, 170, 160),
            anchorX: "center", anchorY: "center");

        // Camera icon hint
        r.DrawText("📱", centerX, urlY + 18, 14, (180, 180, 180),
            anchorX: "center", anchorY: "center");
    }

    public static void UpdateCache(double dt)
    {
        _cacheAge += dt;
    }
}

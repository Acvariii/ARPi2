namespace ARPi2.Sharp;

/// <summary>Central configuration mirroring Python config.py.</summary>
public static class GameConfig
{
    // Network
    public const string ServerIP   = "0.0.0.0";
    public const int    ServerPort = 8765;
    public const int    HttpPort   = 8000;

    // Display
    public const int ScreenWidth  = 1920;
    public const int ScreenHeight = 1080;
    public const int TargetFPS    = 0; // 0 = unlimited / vsync

    // Interaction
    public const float HoverTimeThreshold = 0.9f; // seconds

    // Players
    public const int MaxPlayers = 8;
    public const int MinPlayers = 2;

    // Player Colours (8 distinct)
    public static readonly (int R, int G, int B)[] PlayerColors =
    {
        (220,  40,  40), // Red
        ( 40, 120, 200), // Blue
        ( 40, 200, 120), // Green
        (255, 200,  60), // Yellow
        (200,  40, 200), // Magenta
        ( 40, 220, 200), // Cyan
        (255, 120,  60), // Orange
        (140,  40, 220), // Purple
    };

    // UI Colours
    public static class Colors
    {
        public static readonly (int R, int G, int B) White        = (255, 255, 255);
        public static readonly (int R, int G, int B) Black        = (  0,   0,   0);
        public static readonly (int R, int G, int B) DarkBg       = ( 18,  18,  28);
        public static readonly (int R, int G, int B) Panel        = ( 24,  24,  34);
        public static readonly (int R, int G, int B) Accent       = (240, 200,  80);
        public static readonly (int R, int G, int B) Gold         = (255, 215,   0);
        public static readonly (int R, int G, int B) Shadow       = ( 10,  10,  10);
        public static readonly (int R, int G, int B) Disabled     = ( 80,  80,  80);
        public static readonly (int R, int G, int B) DisabledText = (160, 160, 160);
    }
}

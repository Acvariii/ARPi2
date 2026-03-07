using System;
using System.Diagnostics;
using System.IO;
using System.Text.RegularExpressions;
using System.Threading;
using Microsoft.Xna.Framework;
using Microsoft.Xna.Framework.Graphics;

namespace ARPi2.Sharp.Core;

/// <summary>
/// Plays an MP4 video by piping raw RGBA frames from ffmpeg.exe into a MonoGame Texture2D.
/// Scales to fill the entire screen.  For looping playback, a second ffmpeg instance
/// is launched ~1 s before the current stream ends and both run simultaneously while
/// the old frame dissolves into the new one — no flicker, no gap.
/// </summary>
public sealed class VideoPlayer : IDisposable
{
    // ─── Video metadata (shared across pipelines) ──────────────
    private int _videoWidth;
    private int _videoHeight;
    private double _fps;
    private double _duration;

    private readonly GraphicsDevice _gd;
    private bool _started;
    private bool _finished;
    private volatile bool _disposed;

    // Fade in / out (initial start & non-looping end)
    private const double FadeDuration = 0.5;
    private enum FadePhase { FadeIn, Playing, FadeOut, Done }
    private FadePhase _fadePhase = FadePhase.FadeIn;
    private double _fadeTimer;

    // Looping
    private bool _looping;
    private string? _mp4Path;

    // Cross-fade between old → new loop iteration
    private const double CrossFadeDuration = 1.0;
    private bool _crossFading;
    private double _crossFadeTimer;

    private const int RingSize = 8;

    // ═══════════════════════════════════════════════════════════════
    //  Pipeline — one self-contained ffmpeg → texture stream
    // ═══════════════════════════════════════════════════════════════
    private sealed class Pipeline : IDisposable
    {
        public Process? Ffmpeg;
        public Stream? Stdout;
        public Thread? Reader;
        public volatile bool ReaderDone;

        public readonly byte[][] Ring;
        public int RingWrite, RingRead;
        public int RingCount;

        public readonly byte[] FrameBuf;
        public Texture2D? Tex;

        public double Elapsed;
        public int FrameIdx;
        public double NextFrameTime;

        public Pipeline(GraphicsDevice gd, int w, int h, int ringSize)
        {
            int fb = w * h * 4;
            FrameBuf = new byte[fb];
            Tex = new Texture2D(gd, w, h, false, SurfaceFormat.Color);
            Ring = new byte[ringSize][];
            for (int i = 0; i < ringSize; i++)
                Ring[i] = new byte[fb];
        }

        public void Dispose()
        {
            try { Stdout?.Dispose(); } catch { }
            try
            {
                if (Ffmpeg is { HasExited: false }) Ffmpeg.Kill();
                Ffmpeg?.Dispose();
            }
            catch { }
            Ffmpeg = null;
            Stdout = null;
            Tex?.Dispose();
            Tex = null;
        }
    }

    private Pipeline? _cur;
    private Pipeline? _next;

    public bool IsPlaying => _started && !_finished;
    public bool IsFinished => _finished;

    public VideoPlayer(GraphicsDevice gd) { _gd = gd; }

    // ═══════════════════════════════════════════════════════════════
    //  Public API
    // ═══════════════════════════════════════════════════════════════

    /// <summary>Start playing the specified MP4 file. Call once to begin.</summary>
    public void Play(string mp4Path, bool loop = false)
    {
        if (_started) return;
        _looping = loop;
        _mp4Path = mp4Path;

        if (!File.Exists(mp4Path))
        {
            Console.WriteLine($"VideoPlayer: File not found: {mp4Path}");
            _finished = true;
            return;
        }

        if (!ProbeVideo(mp4Path)) { _finished = true; return; }

        _cur = CreatePipeline(mp4Path);
        if (_cur == null) { _finished = true; return; }

        _started = true;
        // Looping background videos skip fade-in (instant full alpha);
        // non-looping (intro) videos use the fade-in envelope.
        _fadePhase = loop ? FadePhase.Playing : FadePhase.FadeIn;
        _fadeTimer = 0;
    }

    /// <summary>Stop playback and release all resources.</summary>
    public void Stop()
    {
        _finished = true;
        Cleanup();
    }

    public void Dispose() => Stop();

    // ═══════════════════════════════════════════════════════════════
    //  Update — advance frames, manage cross-fade
    // ═══════════════════════════════════════════════════════════════

    public void Update(double dt)
    {
        if (!_started || _finished || _cur == null) return;

        _fadeTimer += dt;

        // Fade state machine (initial fade-in / final fade-out)
        switch (_fadePhase)
        {
            case FadePhase.FadeIn:
                if (_fadeTimer >= FadeDuration)
                {
                    _fadePhase = FadePhase.Playing;
                    _fadeTimer = 0;
                }
                break;
            case FadePhase.FadeOut:
                if (_fadeTimer >= FadeDuration)
                {
                    _fadePhase = FadePhase.Done;
                    _finished = true;
                    Cleanup();
                    return;
                }
                break;
        }

        // Advance current pipeline
        AdvanceFrames(_cur, dt);

        // ── Pre-emptive cross-fade: launch next pipeline 1 s before end ──
        if (_looping && !_crossFading && _mp4Path != null
            && _duration > CrossFadeDuration + 0.5
            && _cur.Elapsed >= _duration - CrossFadeDuration)
        {
            StartCrossFade();
        }

        // Fallback: stream ended before we could pre-empt (bad duration probe)
        if (_looping && !_crossFading && _mp4Path != null
            && _cur.ReaderDone && _cur.RingCount == 0)
        {
            StartCrossFade();
        }

        // Advance the next pipeline & tick cross-fade timer
        if (_crossFading && _next != null)
        {
            _crossFadeTimer += dt;
            AdvanceFrames(_next, dt);

            if (_crossFadeTimer >= CrossFadeDuration)
            {
                // Promote: next ➜ current
                _cur.Dispose();
                _cur = _next;
                _next = null;
                _crossFading = false;
                _crossFadeTimer = 0;
            }
        }

        // Non-looping: start fade-out when data ends
        if (!_looping && _cur.ReaderDone && _cur.RingCount == 0
            && _fadePhase != FadePhase.FadeOut)
        {
            _fadePhase = FadePhase.FadeOut;
            _fadeTimer = 0;
        }

        // Looping videos stay in Playing phase (never fade out)
    }

    // ═══════════════════════════════════════════════════════════════
    //  Draw — render current frame (+ cross-fade blend)
    // ═══════════════════════════════════════════════════════════════

    public void Draw(Renderer r, int screenW, int screenH)
    {
        if (_cur?.Tex == null || _finished) return;

        // Fade alpha (initial fade-in / final fade-out)
        int alpha = 255;
        switch (_fadePhase)
        {
            case FadePhase.FadeIn:
                alpha = (int)(255 * Math.Clamp(_fadeTimer / FadeDuration, 0, 1));
                break;
            case FadePhase.FadeOut:
                alpha = (int)(255 * (1.0 - Math.Clamp(_fadeTimer / FadeDuration, 0, 1)));
                break;
        }

        // Scale to cover entire screen (no black bars)
        float scaleX = screenW / (float)_videoWidth;
        float scaleY = screenH / (float)_videoHeight;
        float scale = Math.Max(scaleX, scaleY);
        int drawW = (int)(_videoWidth * scale);
        int drawH = (int)(_videoHeight * scale);
        var dest = new Rectangle((screenW - drawW) / 2, (screenH - drawH) / 2, drawW, drawH);

        // Only draw the darkening background rect for non-looping (intro) videos
        if (!_looping)
            r.DrawRect((0, 0, 0), (0, 0, screenW, screenH), alpha: alpha);

        // Cross-fade: draw outgoing at full alpha, incoming on top at increasing alpha
        // This avoids the brightness dip that (1-t) + t causes at mid-transition.
        if (_crossFading && _next?.Tex != null && _next.FrameIdx > 0)
        {
            double t = Math.Clamp(_crossFadeTimer / CrossFadeDuration, 0, 1);
            r.DrawTexture(_cur.Tex, dest, alpha: alpha);           // old stays full
            r.DrawTexture(_next.Tex, dest, alpha: (int)(alpha * t)); // new fades in on top
        }
        else
        {
            r.DrawTexture(_cur.Tex, dest, alpha: alpha);
        }
    }

    // ═══════════════════════════════════════════════════════════════
    //  Internals
    // ═══════════════════════════════════════════════════════════════

    /// <summary>Create a new pipeline: ffmpeg process + reader thread + buffers.</summary>
    private Pipeline? CreatePipeline(string mp4Path)
    {
        var p = new Pipeline(_gd, _videoWidth, _videoHeight, RingSize);

        var psi = new ProcessStartInfo
        {
            FileName = "ffmpeg",
            Arguments = $"-i \"{mp4Path}\" -f rawvideo -pix_fmt rgba -v quiet pipe:1",
            UseShellExecute = false,
            RedirectStandardOutput = true,
            RedirectStandardError = false,
            CreateNoWindow = true,
        };

        try
        {
            p.Ffmpeg = Process.Start(psi);
            p.Stdout = p.Ffmpeg?.StandardOutput.BaseStream;
            if (p.Stdout == null) { p.Dispose(); return null; }
        }
        catch (Exception ex)
        {
            Console.WriteLine($"VideoPlayer: Failed to start ffmpeg: {ex.Message}");
            p.Dispose();
            return null;
        }

        p.ReaderDone = false;
        p.Reader = new Thread(() => ReaderLoop(p)) { IsBackground = true, Name = "VideoReader" };
        p.Reader.Start();
        return p;
    }

    /// <summary>Background reader: ffmpeg stdout → ring buffer.</summary>
    private void ReaderLoop(Pipeline p)
    {
        try
        {
            int frameBytes = _videoWidth * _videoHeight * 4;
            while (!_disposed && p.Stdout != null)
            {
                // Wait for space in the ring buffer
                while (p.RingCount >= RingSize && !_disposed)
                    Thread.Sleep(1);

                var buf = p.Ring[p.RingWrite];
                int read = 0;
                while (read < frameBytes)
                {
                    int n = p.Stdout.Read(buf, read, frameBytes - read);
                    if (n <= 0) { p.ReaderDone = true; return; }
                    read += n;
                }

                p.RingWrite = (p.RingWrite + 1) % RingSize;
                Interlocked.Increment(ref p.RingCount);
            }
        }
        catch { }
        p.ReaderDone = true;
    }

    /// <summary>Consume decoded frames from a pipeline's ring buffer into its texture.</summary>
    private void AdvanceFrames(Pipeline p, double dt)
    {
        p.Elapsed += dt;
        double fd = 1.0 / _fps;
        while (p.Elapsed >= p.NextFrameTime)
        {
            if (p.RingCount > 0)
            {
                Buffer.BlockCopy(p.Ring[p.RingRead], 0, p.FrameBuf, 0, p.FrameBuf.Length);
                p.RingRead = (p.RingRead + 1) % RingSize;
                Interlocked.Decrement(ref p.RingCount);
                p.Tex?.SetData(p.FrameBuf);
                p.FrameIdx++;
            }
            else if (p.ReaderDone)
            {
                break;
            }
            p.NextFrameTime += fd;
        }
    }

    /// <summary>Launch the next pipeline and begin dissolving.</summary>
    private void StartCrossFade()
    {
        if (_crossFading || _mp4Path == null) return;
        _next = CreatePipeline(_mp4Path);
        if (_next == null) return;
        _crossFading = true;
        _crossFadeTimer = 0;
    }

    private void Cleanup()
    {
        _disposed = true;
        _cur?.Dispose(); _cur = null;
        _next?.Dispose(); _next = null;
    }

    // ═══════════════════════════════════════════════════════════════
    //  Probe video metadata
    // ═══════════════════════════════════════════════════════════════

    private bool ProbeVideo(string path)
    {
        try
        {
            var psi = new ProcessStartInfo
            {
                FileName = "ffprobe",
                Arguments = $"-v quiet -show_entries stream=width,height,r_frame_rate,duration " +
                            $"-show_entries format=duration -of flat \"{path}\"",
                UseShellExecute = false,
                RedirectStandardOutput = true,
                CreateNoWindow = true,
            };
            var proc = Process.Start(psi);
            if (proc == null) return FallbackProbe();

            string output = proc.StandardOutput.ReadToEnd();
            proc.WaitForExit(5000);

            var wMatch   = Regex.Match(output, @"width=(\d+)");
            var hMatch   = Regex.Match(output, @"height=(\d+)");
            var fpsMatch = Regex.Match(output, @"r_frame_rate=""?(\d+)/(\d+)""?");
            var durMatch = Regex.Match(output, @"duration=""?([\d.]+)""?");

            _videoWidth  = wMatch.Success   ? int.Parse(wMatch.Groups[1].Value) : 1088;
            _videoHeight = hMatch.Success   ? int.Parse(hMatch.Groups[1].Value) : 720;
            _fps = fpsMatch.Success
                ? double.Parse(fpsMatch.Groups[1].Value) / double.Parse(fpsMatch.Groups[2].Value)
                : 16.0;
            _duration = durMatch.Success ? double.Parse(durMatch.Groups[1].Value) : 5.0;

            Console.WriteLine($"VideoPlayer: {_videoWidth}x{_videoHeight} @ {_fps:F1} fps, {_duration:F2}s");
            return true;
        }
        catch
        {
            return FallbackProbe();
        }
    }

    private bool FallbackProbe()
    {
        _videoWidth = 1088;
        _videoHeight = 720;
        _fps = 16.0;
        _duration = 5.0;
        Console.WriteLine("VideoPlayer: Using fallback metadata (1088x720 @ 16fps)");
        return true;
    }
}

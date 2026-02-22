using System;
using System.Collections.Generic;
using System.IO;
using NAudio.Wave;

namespace ARPi2.Sharp.Core;

/// <summary>
/// Central audio manager for background music and sound effects.
/// Mirrors the Python server's audio handling (per-game BG music + one-shot SFX).
/// </summary>
public class AudioManager : IDisposable
{
    private readonly string _soundsDir;

    // Background music
    private WaveOutEvent? _bgPlayer;
    private AudioFileReader? _bgReader;
    private string? _bgTrack;
    private float _bgVolume = 0.35f;
    private float _sfxVolume = 0.5f;
    private bool _musicMuted;

    // Per-client volume overrides (0.0–1.0)
    private readonly Dictionary<string, float> _clientVolumes = new();

    // SFX cache
    private readonly Dictionary<string, byte[]> _sfxCache = new();

    // Mute voting
    private readonly Dictionary<string, bool> _muteVotes = new();

    // State → track mapping (matches Python exactly)
    private static readonly Dictionary<string, string> TrackMap = new()
    {
        ["menu"] = "LobbyBG.mp3",
        ["blackjack"] = "BlackjackBG.mp3",
        ["exploding_kittens"] = "ExplodingKittensBG.mp3",
        ["uno"] = "UnoBG.mp3",
        ["monopoly"] = "MonopolyBG.mp3",
        ["texas_holdem"] = "TexasHoldemBG.mp3",
        ["cluedo"] = "CluedoBG.mp3",
        ["risk"] = "RiskBG.mp3",
        ["catan"] = "CatanBG.mp3",
        ["unstable_unicorns"] = "TavernBG.mp3",
        ["dnd_creation"] = "TavernBG.mp3",
        ["dnd"] = "TavernBG.mp3",
    };

    public AudioManager(string? soundsDir = null)
    {
        // Default: look for sounds/ directory relative to the project root
        if (string.IsNullOrEmpty(soundsDir))
        {
            // Walk up from executable to find sounds/ directory
            var dir = AppDomain.CurrentDomain.BaseDirectory;
            for (int i = 0; i < 8; i++)
            {
                var candidate = Path.Combine(dir, "sounds");
                if (Directory.Exists(candidate))
                {
                    _soundsDir = candidate;
                    break;
                }
                var parent = Directory.GetParent(dir);
                if (parent == null) break;
                dir = parent.FullName;
            }
            _soundsDir ??= Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "sounds");
        }
        else
        {
            _soundsDir = soundsDir;
        }
    }

    /// <summary>Get the desired background track for a given game state.</summary>
    public string? DesiredTrackForState(string state)
    {
        return TrackMap.GetValueOrDefault(state?.Trim() ?? "");
    }

    /// <summary>Sync background music to current game state. Call from game loop tick.</summary>
    public void SyncBgMusic(string state)
    {
        var desired = DesiredTrackForState(state);
        if (_musicMuted) desired = null;

        if (desired == _bgTrack) return;
        SetBgMusic(desired);
    }

    /// <summary>Set (or stop) background music.</summary>
    private void SetBgMusic(string? filename)
    {
        StopBgMusic();
        _bgTrack = filename;

        if (string.IsNullOrEmpty(filename)) return;

        var path = Path.Combine(_soundsDir, filename);
        if (!File.Exists(path)) return;

        try
        {
            _bgReader = new AudioFileReader(path) { Volume = _bgVolume };
            var loop = new LoopStream(_bgReader);
            _bgPlayer = new WaveOutEvent();
            _bgPlayer.Init(loop);
            _bgPlayer.Play();
        }
        catch (Exception ex)
        {
            System.Diagnostics.Debug.WriteLine($"[Audio] Failed to play BG music '{filename}': {ex.Message}");
        }
    }

    /// <summary>Stop background music.</summary>
    private void StopBgMusic()
    {
        try
        {
            _bgPlayer?.Stop();
            _bgPlayer?.Dispose();
            _bgReader?.Dispose();
        }
        catch { }
        _bgPlayer = null;
        _bgReader = null;
        _bgTrack = null;
    }

    /// <summary>Play a one-shot sound effect.</summary>
    public void PlaySfx(string filename)
    {
        if (_musicMuted) return;

        var path = Path.Combine(_soundsDir, filename);
        if (!File.Exists(path)) return;

        try
        {
            // Each SFX gets its own player for overlapping sounds
            var reader = new AudioFileReader(path) { Volume = Math.Min(0.5f, EffectiveVolume) };
            var player = new WaveOutEvent();
            player.Init(reader);
            player.PlaybackStopped += (s, e) =>
            {
                player.Dispose();
                reader.Dispose();
            };
            player.Play();
        }
        catch (Exception ex)
        {
            System.Diagnostics.Debug.WriteLine($"[Audio] Failed to play SFX '{filename}': {ex.Message}");
        }
    }

    /// <summary>Handle music mute voting.</summary>
    public void SetMuteVote(string clientId, bool mute)
    {
        _muteVotes[clientId] = mute;
        RecomputeMute();
    }

    public void RemoveVoter(string clientId) => _muteVotes.Remove(clientId);

    private void RecomputeMute()
    {
        if (_muteVotes.Count == 0) { _musicMuted = false; return; }
        int muteCount = 0;
        foreach (var v in _muteVotes.Values) if (v) muteCount++;
        _musicMuted = muteCount > _muteVotes.Count / 2.0;

        if (_musicMuted) StopBgMusic();
    }

    public bool IsMuted => _musicMuted;
    public int MuteVotes => _muteVotes.Values.Count(v => v);
    public int MuteRequired => Math.Max(1, (int)Math.Ceiling(_muteVotes.Count / 2.0));
    public bool HasVotedMute(string clientId) => _muteVotes.GetValueOrDefault(clientId, false);

    /// <summary>Set volume for a specific client (player 1 = seat 0). Range: 0.0–1.0.</summary>
    public void SetClientVolume(string clientId, float volume)
    {
        volume = Math.Clamp(volume, 0f, 1f);
        _clientVolumes[clientId] = volume;
        ApplyVolume();
    }

    /// <summary>Get the effective volume (uses the lowest client volume if any are set).</summary>
    public float EffectiveVolume
    {
        get
        {
            if (_clientVolumes.Count == 0) return _bgVolume;
            float minVol = _bgVolume;
            foreach (var v in _clientVolumes.Values)
                minVol = Math.Min(minVol, v);
            return minVol;
        }
    }

    public float GetClientVolume(string clientId)
        => _clientVolumes.GetValueOrDefault(clientId, _bgVolume);

    private void ApplyVolume()
    {
        float vol = EffectiveVolume;
        try
        {
            if (_bgReader != null)
                _bgReader.Volume = vol;
        }
        catch { }
    }

    public void Dispose()
    {
        StopBgMusic();
    }
}

/// <summary>Simple WaveStream wrapper that loops playback.</summary>
internal class LoopStream : WaveStream
{
    private readonly WaveStream _source;
    public LoopStream(WaveStream source) { _source = source; }
    public override WaveFormat WaveFormat => _source.WaveFormat;
    public override long Length => _source.Length;
    public override long Position
    {
        get => _source.Position;
        set => _source.Position = value;
    }

    public override int Read(byte[] buffer, int offset, int count)
    {
        int totalRead = 0;
        while (totalRead < count)
        {
            int read = _source.Read(buffer, offset + totalRead, count - totalRead);
            if (read == 0)
            {
                if (_source.Position == 0) break; // empty stream
                _source.Position = 0;
            }
            totalRead += read;
        }
        return totalRead;
    }
}

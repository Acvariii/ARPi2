using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Microsoft.Xna.Framework.Audio;
using NLayer;

namespace ARPi2.Sharp.Core;

/// <summary>
/// Cross-platform audio manager for background music and sound effects.
/// Uses NLayer (managed MP3 decoder) + MonoGame SoundEffect (SDL2/OpenAL output).
/// Works on Windows, Linux x64, and Raspberry Pi (ARM64).
/// </summary>
public class AudioManager : IDisposable
{
    private readonly string _soundsDir;
    private bool _audioAvailable = true;

    // Background music
    private SoundEffectInstance? _bgInstance;
    private SoundEffect? _bgEffect;
    private string? _bgTrack;
    private float _bgVolume = 1.0f;
    private float _sfxVolume = 0.5f;
    private bool _musicMuted;

    // Per-client volume overrides (0.0–1.0)
    private readonly Dictionary<string, float> _clientVolumes = new();

    // SFX cache (decoded SoundEffects, ready to play)
    private readonly Dictionary<string, SoundEffect> _sfxCache = new();

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

    // ═══════════════════════════════════════════════════════════════════════
    //  MP3 → SoundEffect decoder (NLayer — pure managed, cross-platform)
    // ═══════════════════════════════════════════════════════════════════════

    /// <summary>Decode an MP3 file to a MonoGame SoundEffect (16-bit PCM).</summary>
    private SoundEffect? DecodeMp3(string path)
    {
        if (!_audioAvailable) return null;
        try
        {
            using var mpegFile = new MpegFile(path);
            int sampleRate = mpegFile.SampleRate;
            int channels = mpegFile.Channels;

            // Read float samples in chunks → convert to 16-bit PCM
            var floatBuf = new float[16384];
            using var pcmStream = new MemoryStream();
            int samplesRead;
            while ((samplesRead = mpegFile.ReadSamples(floatBuf, 0, floatBuf.Length)) > 0)
            {
                for (int i = 0; i < samplesRead; i++)
                {
                    short s = (short)(Math.Clamp(floatBuf[i], -1f, 1f) * 32767);
                    pcmStream.WriteByte((byte)(s & 0xFF));
                    pcmStream.WriteByte((byte)((s >> 8) & 0xFF));
                }
            }

            var pcmData = pcmStream.ToArray();
            if (pcmData.Length == 0) return null;

            return new SoundEffect(pcmData, sampleRate,
                channels == 1 ? AudioChannels.Mono : AudioChannels.Stereo);
        }
        catch (Exception ex)
        {
            System.Diagnostics.Debug.WriteLine($"[Audio] Failed to decode '{path}': {ex.Message}");
            return null;
        }
    }

    // ═══════════════════════════════════════════════════════════════════════
    //  Background music
    // ═══════════════════════════════════════════════════════════════════════

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
            _bgEffect = DecodeMp3(path);
            if (_bgEffect == null) return;

            _bgInstance = _bgEffect.CreateInstance();
            _bgInstance.IsLooped = true;
            _bgInstance.Volume = EffectiveVolume;
            _bgInstance.Play();
        }
        catch (NoAudioHardwareException)
        {
            _audioAvailable = false;
            System.Diagnostics.Debug.WriteLine("[Audio] No audio hardware available — audio disabled.");
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
            _bgInstance?.Stop();
            _bgInstance?.Dispose();
            _bgEffect?.Dispose();
        }
        catch { }
        _bgInstance = null;
        _bgEffect = null;
        _bgTrack = null;
    }

    // ═══════════════════════════════════════════════════════════════════════
    //  Sound effects (one-shot, supports overlapping)
    // ═══════════════════════════════════════════════════════════════════════

    /// <summary>Play a one-shot sound effect. Decoded SFX are cached for reuse.</summary>
    public void PlaySfx(string filename)
    {
        if (_musicMuted || !_audioAvailable) return;

        var path = Path.Combine(_soundsDir, filename);
        if (!File.Exists(path)) return;

        try
        {
            if (!_sfxCache.TryGetValue(filename, out var sfx))
            {
                sfx = DecodeMp3(path);
                if (sfx == null) return;
                _sfxCache[filename] = sfx;
            }

            // Play() is fire-and-forget; MonoGame manages the pooled instance lifecycle
            sfx.Play(Math.Min(0.5f, EffectiveVolume), 0f, 0f);
        }
        catch (NoAudioHardwareException)
        {
            _audioAvailable = false;
        }
        catch (Exception ex)
        {
            System.Diagnostics.Debug.WriteLine($"[Audio] Failed to play SFX '{filename}': {ex.Message}");
        }
    }

    // ═══════════════════════════════════════════════════════════════════════
    //  Mute voting & volume
    // ═══════════════════════════════════════════════════════════════════════

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
            if (_bgInstance != null)
                _bgInstance.Volume = vol;
        }
        catch { }
    }

    public void Dispose()
    {
        StopBgMusic();
        foreach (var sfx in _sfxCache.Values)
        {
            try { sfx.Dispose(); } catch { }
        }
        _sfxCache.Clear();
    }
}

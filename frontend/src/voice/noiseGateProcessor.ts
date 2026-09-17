import type {
  AudioProcessorOptions,
  Track,
  TrackProcessor,
} from 'livekit-client'


export const DEFAULT_VOICE_NOISE_GATE_THRESHOLD_DB = -45
export const MIN_VOICE_NOISE_GATE_THRESHOLD_DB = -60
export const MAX_VOICE_NOISE_GATE_THRESHOLD_DB = -20


export function normalizeVoiceNoiseGateThresholdDb(
  value: number | null,
): number | null {
  if (value === null) {
    return null
  }

  if (!Number.isFinite(value)) {
    return DEFAULT_VOICE_NOISE_GATE_THRESHOLD_DB
  }

  return Math.min(
    MAX_VOICE_NOISE_GATE_THRESHOLD_DB,
    Math.max(
      MIN_VOICE_NOISE_GATE_THRESHOLD_DB,
      Math.round(value),
    ),
  )
}


export function voiceNoiseGateSupported(): boolean {
  return (
    typeof window !== 'undefined'
    && 'AudioContext' in window
  )
}


export class VoiceNoiseGateProcessor
implements TrackProcessor<
  Track.Kind.Audio,
  AudioProcessorOptions
> {
  readonly name =
    'communication-platform-noise-gate'

  processedTrack?: MediaStreamTrack

  private source:
    MediaStreamAudioSourceNode | null = null

  private analyser:
    AnalyserNode | null = null

  private gain:
    GainNode | null = null

  private destination:
    MediaStreamAudioDestinationNode | null = null

  private samples:
    Uint8Array<ArrayBuffer> | null = null

  private monitorTimer:
    number | null = null

  private audioContext:
    AudioContext | null = null

  private thresholdDb:
    number | null

  private gateOpen = true

  private lastAboveThresholdAt = 0


  constructor(
    thresholdDb: number | null,
  ) {
    this.thresholdDb =
      normalizeVoiceNoiseGateThresholdDb(
        thresholdDb,
      )
  }


  setThresholdDb(
    thresholdDb: number | null,
  ): void {
    this.thresholdDb =
      normalizeVoiceNoiseGateThresholdDb(
        thresholdDb,
      )

    if (this.thresholdDb === null) {
      this.gateOpen = true
      this.setGain(1, true)
    }
  }


  async init(
    options: AudioProcessorOptions,
  ): Promise<void> {
    this.buildGraph(options)
  }


  async restart(
    options: AudioProcessorOptions,
  ): Promise<void> {
    this.destroyGraph()
    this.buildGraph(options)
  }


  async destroy(): Promise<void> {
    this.destroyGraph()
  }


  private buildGraph(
    options: AudioProcessorOptions,
  ): void {
    const {
      track,
      audioContext,
    } = options

    this.audioContext = audioContext

    const source =
      audioContext
        .createMediaStreamSource(
          new MediaStream([track]),
        )

    const analyser =
      audioContext.createAnalyser()

    analyser.fftSize = 512
    analyser.smoothingTimeConstant = 0.15

    const gain =
      audioContext.createGain()

    const destination =
      audioContext
        .createMediaStreamDestination()

    source.connect(analyser)
    analyser.connect(gain)
    gain.connect(destination)

    this.source = source
    this.analyser = analyser
    this.gain = gain
    this.destination = destination
    this.samples = new Uint8Array(
      analyser.fftSize,
    )

    this.processedTrack =
      destination.stream
        .getAudioTracks()[0]

    this.gateOpen = true
    this.lastAboveThresholdAt =
      performance.now()

    this.setGain(1, true)

    this.monitorTimer =
      window.setInterval(
        () => {
          this.updateGate()
        },
        30,
      )
  }


  private updateGate(): void {
    const thresholdDb =
      this.thresholdDb

    const analyser = this.analyser
    const samples = this.samples

    if (
      thresholdDb === null
      || !analyser
      || !samples
    ) {
      if (!this.gateOpen) {
        this.gateOpen = true
        this.setGain(1)
      }
      return
    }

    analyser.getByteTimeDomainData(
      samples,
    )

    let sumSquares = 0

    for (
      let index = 0;
      index < samples.length;
      index += 1
    ) {
      const sample =
        (samples[index] - 128) / 128
      sumSquares += sample * sample
    }

    const rms = Math.sqrt(
      sumSquares / samples.length,
    )

    const levelDb =
      20 * Math.log10(
        Math.max(rms, 1e-7),
      )

    const now = performance.now()

    if (levelDb >= thresholdDb) {
      this.lastAboveThresholdAt = now

      if (!this.gateOpen) {
        this.gateOpen = true
        this.setGain(1)
      }
      return
    }

    /*
     * Keep the gate open briefly after speech drops
     * below the threshold so word endings are not
     * chopped off. A little hysteresis also keeps the
     * gate from rapidly fluttering around the cutoff.
     */
    const belowCloseThreshold =
      levelDb < thresholdDb - 3

    if (
      this.gateOpen
      && belowCloseThreshold
      && now - this.lastAboveThresholdAt > 180
    ) {
      this.gateOpen = false
      this.setGain(0)
    }
  }


  private setGain(
    value: number,
    immediate = false,
  ): void {
    const gain = this.gain
    const context = this.audioContext

    if (!gain || !context) {
      return
    }

    if (immediate) {
      gain.gain.setValueAtTime(
        value,
        context.currentTime,
      )
      return
    }

    gain.gain.cancelScheduledValues(
      context.currentTime,
    )

    gain.gain.setTargetAtTime(
      value,
      context.currentTime,
      value > 0
        ? 0.006
        : 0.035,
    )
  }


  private destroyGraph(): void {
    if (this.monitorTimer !== null) {
      window.clearInterval(
        this.monitorTimer,
      )
      this.monitorTimer = null
    }

    this.source?.disconnect()
    this.analyser?.disconnect()
    this.gain?.disconnect()
    this.destination?.disconnect()

    this.processedTrack?.stop()

    this.source = null
    this.analyser = null
    this.gain = null
    this.destination = null
    this.samples = null
    this.audioContext = null
    this.processedTrack = undefined
  }
}

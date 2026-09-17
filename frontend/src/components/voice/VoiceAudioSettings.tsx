import {
  useEffect,
  useRef,
  useState,
} from 'react'
import {
  createPortal,
} from 'react-dom'

import {
  useVoice,
} from '../../voice/useVoice'


type VoiceAudioSettingsProps = {
  buttonSize?: 'sm' | 'md'
}


function VoiceAudioSettings({
  buttonSize = 'sm',
}: VoiceAudioSettingsProps) {
  const {
    mediaStatus,
    audioOutputVolume,
    audioOutputDeviceId,
    audioOutputDevices,
    audioOutputSelectionSupported,
    audioOutputPromptSupported,
    setAudioOutputVolume,
    refreshAudioOutputDevices,
    setAudioOutputDevice,
    chooseAudioOutputDevice,
  } = useVoice()

  const [open, setOpen] =
    useState(false)

  const [busy, setBusy] =
    useState(false)

  const [localError, setLocalError] =
    useState<string | null>(null)

  const rootRef =
    useRef<HTMLDivElement | null>(null)

  const panelRef =
    useRef<HTMLDivElement | null>(null)

  const connected =
    mediaStatus === 'connected'

  const volumePercent =
    Math.round(
      audioOutputVolume * 100,
    )

  const selectedDeviceKnown =
    !audioOutputDeviceId
    || audioOutputDevices.some(
      (device) =>
        device.device_id ===
          audioOutputDeviceId,
    )


  useEffect(
    () => {
      if (!open) {
        return
      }

      function handlePointerDown(
        event: PointerEvent,
      ) {
        if (
          event.target instanceof Node
          && !rootRef.current
            ?.contains(event.target)
          && !panelRef.current
            ?.contains(event.target)
        ) {
          setOpen(false)
        }
      }

      function handleKeyDown(
        event: KeyboardEvent,
      ) {
        if (event.key === 'Escape') {
          setOpen(false)
        }
      }

      document.addEventListener(
        'pointerdown',
        handlePointerDown,
      )
      document.addEventListener(
        'keydown',
        handleKeyDown,
      )

      return () => {
        document.removeEventListener(
          'pointerdown',
          handlePointerDown,
        )
        document.removeEventListener(
          'keydown',
          handleKeyDown,
        )
      }
    },
    [open],
  )


  async function refreshDevices() {
    if (
      !audioOutputSelectionSupported
    ) {
      return
    }

    try {
      await refreshAudioOutputDevices()
    } catch (error) {
      setLocalError(
        error instanceof Error
          ? error.message
          : 'Could not list audio outputs.',
      )
    }
  }


  async function switchDevice(
    deviceId: string,
  ) {
    setBusy(true)
    setLocalError(null)

    try {
      await setAudioOutputDevice(
        deviceId,
      )
      await refreshAudioOutputDevices()
    } catch (error) {
      setLocalError(
        error instanceof Error
          ? error.message
          : 'Could not switch audio output.',
      )
    } finally {
      setBusy(false)
    }
  }


  async function chooseDevice() {
    setBusy(true)
    setLocalError(null)

    try {
      await chooseAudioOutputDevice()
    } catch (error) {
      setLocalError(
        error instanceof Error
          ? error.message
          : 'Could not choose audio output.',
      )
    } finally {
      setBusy(false)
    }
  }


  const settingsPanel =
    open
    && typeof document !== 'undefined'
      ? createPortal(
        <div
          className="voice-audio-settings-layer"
          role="presentation"
        >
          <div
            className="voice-audio-settings-popover"
            role="dialog"
            aria-modal="false"
            aria-label="Voice audio settings"
            ref={panelRef}
          >
            <div className="voice-audio-settings-heading-row">
              <div className="voice-audio-settings-heading">
                Audio output
              </div>

              <button
                className="btn-close"
                type="button"
                aria-label="Close audio settings"
                onClick={() => {
                  setOpen(false)
                }}
              />
            </div>

            <label className="voice-audio-settings-field">
              <span className="d-flex justify-content-between gap-3">
                <span>Output volume</span>
                <span className="text-secondary">
                  {volumePercent}%
                </span>
              </span>

              <input
                className="form-range m-0"
                type="range"
                min="0"
                max="100"
                step="5"
                value={volumePercent}
                aria-label="Voice output volume"
                onChange={(event) => {
                  setAudioOutputVolume(
                    Number(
                      event.target.value,
                    ) / 100,
                  )
                }}
              />
            </label>

            {audioOutputSelectionSupported ? (
              <div className="voice-audio-settings-field">
                <label
                  className="form-label small mb-1"
                  htmlFor="voice-audio-output-device"
                >
                  Output device
                </label>

                <select
                  id="voice-audio-output-device"
                  className="form-select form-select-sm"
                  value={audioOutputDeviceId}
                  disabled={busy}
                  onChange={(event) => {
                    void switchDevice(
                      event.target.value,
                    )
                  }}
                >
                  <option value="">
                    System default
                  </option>

                  {!selectedDeviceKnown && (
                    <option
                      value={audioOutputDeviceId}
                    >
                      Previously selected output
                    </option>
                  )}

                  {audioOutputDevices.map(
                    (device) => (
                      <option
                        key={device.device_id}
                        value={device.device_id}
                      >
                        {device.label}
                      </option>
                    ),
                  )}
                </select>

                {audioOutputPromptSupported && (
                  <button
                    className="btn btn-sm btn-link px-0 mt-1"
                    type="button"
                    disabled={busy}
                    onClick={() => {
                      void chooseDevice()
                    }}
                  >
                    Choose another output…
                  </button>
                )}

                {!connected && (
                  <div className="small text-secondary mt-1">
                    Your preferred output will be used when voice connects.
                  </div>
                )}
              </div>
            ) : (
              <div className="small text-secondary">
                Speaker, earpiece, and Bluetooth routing are controlled by your browser or device on this platform.
              </div>
            )}

            {localError && (
              <div
                className="small text-danger"
                role="alert"
              >
                {localError}
              </div>
            )}
          </div>
        </div>,
        document.body,
      )
      : null


  return (
    <div
      className="voice-audio-settings"
      ref={rootRef}
    >
      <button
        className={
          `btn ${
            buttonSize === 'sm'
              ? 'btn-sm '
              : ''
          }btn-outline-secondary text-nowrap`
        }
        type="button"
        aria-expanded={open}
        onClick={() => {
          const nextOpen = !open

          setOpen(nextOpen)
          setLocalError(null)

          if (nextOpen) {
            void refreshDevices()
          }
        }}
      >
        Audio
      </button>

      {settingsPanel}
    </div>
  )
}


export default VoiceAudioSettings

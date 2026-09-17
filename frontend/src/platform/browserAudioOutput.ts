export type BrowserAudioOutputDevice = {
  deviceId: string
  label: string
}


type MediaDevicesWithAudioOutput =
  MediaDevices & {
    selectAudioOutput?: (
      options?: {
        deviceId?: string
      },
    ) => Promise<MediaDeviceInfo>
  }


function mediaDevices():
MediaDevicesWithAudioOutput | null {
  if (
    typeof navigator === 'undefined'
    || !navigator.mediaDevices
  ) {
    return null
  }

  return navigator.mediaDevices as MediaDevicesWithAudioOutput
}


export function browserAudioOutputSelectionSupported():
boolean {
  if (
    typeof HTMLMediaElement
      === 'undefined'
    || typeof window === 'undefined'
    || !window.isSecureContext
  ) {
    return false
  }

  return (
    mediaDevices() !== null
    && 'setSinkId'
      in HTMLMediaElement.prototype
  )
}


export function browserAudioOutputPromptSupported():
boolean {
  const devices = mediaDevices()

  return (
    browserAudioOutputSelectionSupported()
    && typeof devices?.selectAudioOutput
      === 'function'
  )
}


export async function listBrowserAudioOutputDevices():
Promise<BrowserAudioOutputDevice[]> {
  const devices = mediaDevices()

  if (
    !devices
    || !browserAudioOutputSelectionSupported()
  ) {
    return []
  }

  const available =
    await devices.enumerateDevices()

  return available
    .filter(
      (device) =>
        device.kind === 'audiooutput',
    )
    .map(
      (device, index) => ({
        deviceId: device.deviceId,
        label:
          device.label
          || `Audio output ${index + 1}`,
      }),
    )
}


export async function requestBrowserAudioOutputDevice(
  currentDeviceId?: string,
): Promise<BrowserAudioOutputDevice> {
  const devices = mediaDevices()

  if (
    !devices
    || typeof devices.selectAudioOutput
      !== 'function'
  ) {
    throw new Error(
      'Audio output selection is not supported by this browser.',
    )
  }

  const selected =
    await devices.selectAudioOutput(
      currentDeviceId
        ? {
            deviceId:
              currentDeviceId,
          }
        : undefined,
    )

  return {
    deviceId: selected.deviceId,
    label:
      selected.label
      || 'Selected audio output',
  }
}

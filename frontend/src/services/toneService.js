import * as Tone from 'tone'

let isInitialized = false
let synth = null
let distortion = null
let autoFilter = null
let droneGain = null
let hallucinationLoop = null

// Callback fired by the hallucination loop — set by the consumer
let onHallucination = null

export function setHallucinationCallback(cb) {
  onHallucination = cb
}

export async function initAudio(getCurrentState) {
  if (isInitialized) return
  await Tone.start()

  Tone.getTransport().bpm.value = 60

  distortion = new Tone.Distortion(0).toDestination()
  autoFilter = new Tone.AutoFilter('4n').connect(distortion)
  droneGain = new Tone.Gain(0).connect(autoFilter)

  synth = new Tone.FMSynth({
    harmonicity: 1.5,
    modulationIndex: 2,
    oscillator: { type: 'triangle' },
    modulation: { type: 'square' },
  }).connect(droneGain)

  synth.triggerAttack('C1')
  autoFilter.start()

  hallucinationLoop = new Tone.Loop((time) => {
    if (getCurrentState() === 3) {
      Tone.getDraw().schedule(() => {
        if (onHallucination) onHallucination()
      }, time)
    }
  }, '2m').start(0)

  Tone.getTransport().start()
  isInitialized = true
}

export function updateAudioIntensity(currentState, maxStates) {
  if (!isInitialized) return
  const intensity = currentState / maxStates

  droneGain.gain.rampTo(intensity * 0.6, 1)
  distortion.distortion = intensity * 0.8
  synth.modulationIndex.rampTo(2 + intensity * 20, 1)
  autoFilter.frequency.value = `${intensity * 8}n`
}

export function escalateHallucination() {
  if (!hallucinationLoop) return

  const currentBpm = Tone.getTransport().bpm.value
  if (currentBpm < 120) {
    Tone.getTransport().bpm.rampTo(currentBpm + 2, 4)
  }

  const interval = hallucinationLoop.interval
  if (interval === '2m') hallucinationLoop.interval = '1m'
  else if (interval === '1m') hallucinationLoop.interval = '30s'
  else if (interval === '30s') hallucinationLoop.interval = '10s'
}

export function dispose() {
  if (!isInitialized) return
  Tone.getTransport().stop()
  hallucinationLoop?.dispose()
  synth?.dispose()
  autoFilter?.dispose()
  distortion?.dispose()
  droneGain?.dispose()

  synth = null
  distortion = null
  autoFilter = null
  droneGain = null
  hallucinationLoop = null
  isInitialized = false
}

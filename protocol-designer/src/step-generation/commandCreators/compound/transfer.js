// @flow
import zip from 'lodash/zip'
import {getPipetteNameSpecs} from '@opentrons/shared-data'
import * as errorCreators from '../../errorCreators'
import {getPipetteWithTipMaxVol} from '../../robotStateSelectors'
import type {TransferFormData, RobotState, CommandCreator, CompoundCommandCreator} from '../../types'
import {blowoutUtil} from '../../utils'
import {aspirate, dispense, replaceTip, touchTip} from '../atomic'
import {mixUtil} from './mix'

const transfer = (data: TransferFormData): CompoundCommandCreator => (prevRobotState: RobotState) => {
  /**
    Transfer will iterate through a set of 1 or more source and destination wells.
    For each pair, it will aspirate from the source well, then dispense into the destination well.
    This pair of 1 source well and 1 dest well is internally called a "sub-transfer".

    If the volume to aspirate from a source well exceeds the max volume of the pipette,
    then each sub-transfer will be chunked into multiple asp-disp, asp-disp commands.

    A single uniform volume will be aspirated from every source well and dispensed into every dest well.
    In other words, all the sub-transfers will use the same uniform volume.

    =====

    For transfer, changeTip means:
    * 'always': before each aspirate, get a fresh tip
    * 'once': get a new tip at the beginning of the transfer step, and use it throughout
    * 'never': reuse the tip from the last step
    * 'perSource': change tip each time you encounter a new source well (including the first one)
    * 'perDest': change tip each time you encounter a new destination well (including the first one)
    NOTE: In some situations, different changeTip options have equivalent outcomes. That's OK.
  */

  // TODO Ian 2018-04-02 following ~10 lines are identical to first lines of consolidate.js...
  const actionName = 'transfer'

  const pipetteData = prevRobotState.pipettes[data.pipette]
  const pipetteSpec = pipetteData && pipetteData.name && getPipetteNameSpecs(pipetteData.name)

  if (!pipetteData || !pipetteSpec) {
    // bail out before doing anything else
    return [(_robotState) => ({
      errors: [errorCreators.pipetteDoesNotExist({actionName, pipette: data.pipette})],
    })]
  }

  const {
    aspirateFlowRateUlSec,
    dispenseFlowRateUlSec,
    aspirateOffsetFromBottomMm,
    dispenseOffsetFromBottomMm,
  } = data

  const effectiveTransferVol = getPipetteWithTipMaxVol(data.pipette, prevRobotState)
  const pipetteMinVol = pipetteSpec.minVolume

  const chunksPerSubTransfer = Math.ceil(
    data.volume / effectiveTransferVol
  )
  const lastSubTransferVol = data.volume - ((chunksPerSubTransfer - 1) * effectiveTransferVol)

  // volume of each chunk in a sub-transfer
  let subTransferVolumes: Array<number> = Array(chunksPerSubTransfer - 1)
    .fill(effectiveTransferVol)
    .concat(lastSubTransferVol)

  if (chunksPerSubTransfer > 1 && lastSubTransferVol < pipetteMinVol) {
    // last chunk volume is below pipette min, split the last
    const splitLastVol = (effectiveTransferVol + lastSubTransferVol) / 2
    subTransferVolumes = Array(chunksPerSubTransfer - 2)
      .fill(effectiveTransferVol)
      .concat(splitLastVol)
      .concat(splitLastVol)
  }

  const sourceDestPairs = zip(data.sourceWells, data.destWells)
  let prevSourceWell = null
  let prevDestWell = null
  const commandCreators = sourceDestPairs.reduce(
    (outerAcc: Array<CommandCreator>, wellPair: [string, string], pairIdx: number): Array<CommandCreator> => {
      const [sourceWell, destWell] = wellPair

      const commands = subTransferVolumes.reduce(
        (innerAcc: Array<CommandCreator>, subTransferVol: number, chunkIdx: number): Array<CommandCreator> => {
          const isInitialSubtransfer = (pairIdx === 0 && chunkIdx === 0)
          let changeTipNow = false // 'never' by default

          if (data.changeTip === 'always') {
            changeTipNow = true
          } else if (data.changeTip === 'once') {
            changeTipNow = isInitialSubtransfer
          } else if (data.changeTip === 'perSource') {
            changeTipNow = sourceWell !== prevSourceWell
          } else if (data.changeTip === 'perDest') {
            changeTipNow = isInitialSubtransfer || destWell !== prevDestWell
          }

          const tipCommands: Array<CommandCreator> = changeTipNow
            ? [replaceTip(data.pipette)]
            : []

          const preWetTipCommands = (data.preWetTip && chunkIdx === 0)
            ? mixUtil({
              pipette: data.pipette,
              labware: data.sourceLabware,
              well: sourceWell,
              volume: Math.max(subTransferVol),
              times: 1,
              aspirateOffsetFromBottomMm,
              dispenseOffsetFromBottomMm,
              aspirateFlowRateUlSec,
              dispenseFlowRateUlSec,
            })
            : []

          const mixBeforeAspirateCommands = (data.mixBeforeAspirate)
            ? mixUtil({
              pipette: data.pipette,
              labware: data.sourceLabware,
              well: sourceWell,
              volume: data.mixBeforeAspirate.volume,
              times: data.mixBeforeAspirate.times,
              aspirateOffsetFromBottomMm,
              dispenseOffsetFromBottomMm,
              aspirateFlowRateUlSec,
              dispenseFlowRateUlSec,
            })
            : []

          const touchTipAfterAspirateCommands = (data.touchTipAfterAspirate)
            ? [touchTip({
              pipette: data.pipette,
              labware: data.sourceLabware,
              well: sourceWell,
              offsetFromBottomMm: data.touchTipAfterAspirateOffsetMmFromBottom,
            })]
            : []

          const touchTipAfterDispenseCommands = (data.touchTipAfterDispense)
            ? [touchTip({
              pipette: data.pipette,
              labware: data.destLabware,
              well: destWell,
              offsetFromBottomMm: data.touchTipAfterDispenseOffsetMmFromBottom,
            })]
            : []

          const mixInDestinationCommands = (data.mixInDestination)
            ? mixUtil({
              pipette: data.pipette,
              labware: data.destLabware,
              well: destWell,
              volume: data.mixInDestination.volume,
              times: data.mixInDestination.times,
              aspirateOffsetFromBottomMm,
              dispenseOffsetFromBottomMm,
              aspirateFlowRateUlSec,
              dispenseFlowRateUlSec,
            })
            : []

          const blowoutCommand = blowoutUtil(
            data.pipette,
            data.sourceLabware,
            sourceWell,
            data.destLabware,
            destWell,
            data.blowoutLocation,
          )

          const nextCommands = [
            ...tipCommands,
            ...preWetTipCommands,
            ...mixBeforeAspirateCommands,
            aspirate({
              pipette: data.pipette,
              volume: subTransferVol,
              labware: data.sourceLabware,
              well: sourceWell,
              'flow-rate': aspirateFlowRateUlSec,
              offsetFromBottomMm: aspirateOffsetFromBottomMm,
            }),
            ...touchTipAfterAspirateCommands,
            dispense({
              pipette: data.pipette,
              volume: subTransferVol,
              labware: data.destLabware,
              well: destWell,
              'flow-rate': dispenseFlowRateUlSec,
              offsetFromBottomMm: dispenseOffsetFromBottomMm,
            }),
            ...touchTipAfterDispenseCommands,
            ...mixInDestinationCommands,
            ...blowoutCommand,
          ]

          // NOTE: side-effecting
          prevSourceWell = sourceWell
          prevDestWell = destWell

          return [...innerAcc, ...nextCommands]
        }, [])

      return [...outerAcc, ...commands]
    }, [])
  return commandCreators
}

export default transfer
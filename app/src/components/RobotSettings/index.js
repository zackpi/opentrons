// @flow
// robot status panel with connect button
import * as React from 'react'
import { useSelector } from 'react-redux'

import { CardContainer, CardRow } from '../layout'
import { StatusCard } from './StatusCard'
import { InformationCard } from './InformationCard'
import { ControlsCard } from './ControlsCard'
import { ConnectionCard } from './ConnectionCard'
import { AdvancedSettingsCard } from './AdvancedSettingsCard'
import { CalibrationCard } from './CalibrationCard'
import type { ViewableRobot } from '../../discovery/types'
import { getFeatureFlags } from '../../config'

export { ConnectAlertModal } from './ConnectAlertModal'

export type RobotSettingsProps = {|
  robot: ViewableRobot,
  updateUrl: string,
  calibrateDeckUrl: string,
  resetUrl: string,
  pipettesPageUrl: string,
|}

// TODO BC 2020-03-20 all of the buttons in these settings are disabled for
// various reasons.  We should surface those reasons to users in hover tooltips
// on the buttons, this is currently limited by the existing LabeledButton component.
export function RobotSettings(props: RobotSettingsProps): React.Node {
  const {
    robot,
    updateUrl,
    calibrateDeckUrl,
    resetUrl,
    pipettesPageUrl,
  } = props
  const ff = useSelector(getFeatureFlags)
  return (
    <CardContainer key={robot.name}>
      <CardRow>
        <StatusCard robot={robot} />
      </CardRow>
      <CardRow>
        <InformationCard robot={robot} updateUrl={updateUrl} />
      </CardRow>
      {ff.enableCalibrationOverhaul && (
        <CardRow>
          <CalibrationCard robot={robot} pipettesPageUrl={pipettesPageUrl} />
        </CardRow>
      )}
      <CardRow>
        <ControlsCard robot={robot} calibrateDeckUrl={calibrateDeckUrl} />
      </CardRow>
      <CardRow>
        <ConnectionCard robot={robot} />
      </CardRow>
      <CardRow>
        <AdvancedSettingsCard robot={robot} resetUrl={resetUrl} />
      </CardRow>
    </CardContainer>
  )
}

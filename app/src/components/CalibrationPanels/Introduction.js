// @flow
import * as React from 'react'
import { css } from 'styled-components'
import { getLabwareDisplayName } from '@opentrons/shared-data'
import {
  Box,
  Flex,
  SPACING_2,
  SPACING_3,
  DIRECTION_ROW,
  DIRECTION_COLUMN,
  ALIGN_CENTER,
  ALIGN_FLEX_START,
  JUSTIFY_CENTER,
  POSITION_RELATIVE,
  FONT_HEADER_DARK,
  FONT_BODY_2_DARK,
  TEXT_TRANSFORM_UPPERCASE,
  TEXT_ALIGN_CENTER,
  Link,
  PrimaryBtn,
  Text,
  FONT_SIZE_BODY_1,
  FONT_SIZE_BODY_2,
  BORDER_SOLID_MEDIUM,
  C_NEAR_WHITE,
} from '@opentrons/components'

import * as Sessions from '../../sessions'
import { labwareImages } from './labwareImages'
import type { SessionType } from '../../sessions/types'
import type { CalibrationPanelProps } from './types'

const LABWARE_LIBRARY_PAGE_PATH = 'https://labware.opentrons.com'

const DECK_CAL_HEADER = 'deck calibration'
const DECK_CAL_BODY =
  'Deck calibration ensures positional accuracy so that your robot moves as expected. It will accurately establish the OT-2’s deck orientation relative to the gantry.'

const HEALTH_CHECK_HEADER = 'calibration health check'
const HEALTH_CHECK_BODY =
  'Checking the OT-2’s calibration is a first step towards diagnosing and troubleshooting common pipette positioning problems you may be experiencing.'
const HEALTH_CHECK_PROCEDURE = 'to calibration health check'

const PIP_OFFSET_CAL_HEADER = 'pipette offset calibration'
const PIP_OFFSET_CAL_BODY =
  'Calibrating pipette offset enables robot to accurately establish the location of the mounted pipette’s nozzle, relative to the deck.'

const TIP_LENGTH_CAL_HEADER = 'tip length calibration'
const TIP_LENGTH_CAL_BODY =
  "Tip length calibration measures the length of the pipette's tip separately from the pipette's nozzle."

const START = 'start'
const LABWARE_REQS = 'For this process you will require:'
const NOTE_HEADER = 'Please note:'
const IT_IS = "It's"
const EXTREMELY = 'extremely'
const NOTE_BODY_OUTSIDE_PROTOCOL =
  'important you perform this calibration using the Opentrons tips and tip racks specified above, as the robot determines accuracy based on the measurements of these tips.'
const NOTE_BODY_PRE_PROTOCOL =
  'important you perform this calibration using the exact tips specified in your protocol, as the robot uses the corresponding labware definition data to find the tip.'
const NOTE_HEALTH_CHECK_OUTCOMES =
  'If the difference between the two coordinates falls within the acceptable tolerance range for the given pipette, the check will pass. Otherwise, it will fail and you’ll be provided with troubleshooting guidance. You may exit at any point or continue through to the end to check the overall calibration status of your robot.'
const VIEW_TIPRACK_MEASUREMENTS = 'View measurements'

const contentsBySessionType: {
  [SessionType]: {
    headerText: string,
    bodyText: string,
    continueButtonText: string,
    noteBody: string,
  },
} = {
  [Sessions.SESSION_TYPE_DECK_CALIBRATION]: {
    headerText: DECK_CAL_HEADER,
    bodyText: DECK_CAL_BODY,
    continueButtonText: `${START} ${DECK_CAL_HEADER}`,
    noteBody: NOTE_BODY_OUTSIDE_PROTOCOL,
  },
  [Sessions.SESSION_TYPE_PIPETTE_OFFSET_CALIBRATION]: {
    headerText: PIP_OFFSET_CAL_HEADER,
    bodyText: PIP_OFFSET_CAL_BODY,
    continueButtonText: `${START} ${PIP_OFFSET_CAL_HEADER}`,
    noteBody: NOTE_BODY_OUTSIDE_PROTOCOL,
  },
  [Sessions.SESSION_TYPE_TIP_LENGTH_CALIBRATION]: {
    headerText: TIP_LENGTH_CAL_HEADER,
    bodyText: TIP_LENGTH_CAL_BODY,
    continueButtonText: `${START} ${TIP_LENGTH_CAL_HEADER}`,
    noteBody: NOTE_BODY_PRE_PROTOCOL,
  },
  [Sessions.SESSION_TYPE_CALIBRATION_HEALTH_CHECK]: {
    headerText: HEALTH_CHECK_HEADER,
    bodyText: HEALTH_CHECK_BODY,
    continueButtonText: `${START} ${HEALTH_CHECK_HEADER}`,
    continuingToText: HEALTH_CHECK_PROCEDURE,
    noteBody: NOTE_HEALTH_CHECK_OUTCOMES,
  },
}

export function Introduction(props: CalibrationPanelProps): React.Node {
  const {
    tipRack,
    calBlock,
    sendCommands,
    sessionType,
    shouldPerformTipLength,
  } = props

  const isExtendedPipOffset =
    sessionType === Sessions.SESSION_TYPE_PIPETTE_OFFSET_CALIBRATION &&
    shouldPerformTipLength

  const lookupType = isExtendedPipOffset
    ? Sessions.SESSION_TYPE_TIP_LENGTH_CALIBRATION
    : sessionType
  const isHealthCheck =
    sessionType === Sessions.SESSION_TYPE_CALIBRATION_HEALTH_CHECK

  const proceed = () =>
    sendCommands({ command: Sessions.sharedCalCommands.LOAD_LABWARE })

  const {
    headerText,
    bodyText,
    continueButtonText,
    noteBody,
  } = contentsBySessionType[lookupType]

  const isKnownTiprack = tipRack.loadName in labwareImages
  return (
    <>
      <Flex
        marginY={SPACING_2}
        flexDirection={DIRECTION_COLUMN}
        alignItems={ALIGN_FLEX_START}
        position={POSITION_RELATIVE}
      >
        <Text
          css={FONT_HEADER_DARK}
          marginBottom={SPACING_3}
          textTransform={TEXT_TRANSFORM_UPPERCASE}
        >
          {headerText}
        </Text>
        <Text marginBottom={SPACING_3} css={FONT_BODY_2_DARK}>
          {bodyText}
        </Text>
        <h5>{LABWARE_REQS}</h5>
        <Flex flexDirection={DIRECTION_ROW} marginTop={SPACING_3}>
          <RequiredLabwareCard
            loadName={tipRack.loadName}
            displayName={getLabwareDisplayName(tipRack.definition)}
            linkToMeasurements={isKnownTiprack}
          />
          {calBlock && (
            <>
              <Box width={SPACING_2} />
              <RequiredLabwareCard
                loadName={calBlock.loadName}
                displayName={getLabwareDisplayName(calBlock.definition)}
                linkToMeasurements={false}
              />
            </>
          )}
        </Flex>
        <Box fontSize={FONT_SIZE_BODY_1} marginY={SPACING_3}>
          {!isHealthCheck ? (
            <Text>
              <b
                css={css`
                  text-transform: uppercase;
                `}
              >{`${NOTE_HEADER} `}</b>
              {IT_IS}
              <u>{` ${EXTREMELY} `}</u>
              {noteBody}
            </Text>
          ) : (
            <Text>
              <b
                css={css`
                  text-transform: uppercase;
                `}
              >{`${NOTE_HEADER} `}</b>
              {noteBody}
            </Text>
          )}
        </Box>
      </Flex>
      <Flex width="100%" justifyContent={JUSTIFY_CENTER}>
        <PrimaryBtn
          data-test="continueButton"
          onClick={proceed}
          flex="1"
          margin="1.5rem 5rem 1rem"
        >
          {continueButtonText}
        </PrimaryBtn>
      </Flex>
    </>
  )
}

type RequiredLabwareCardProps = {|
  loadName: string,
  displayName: string,
  linkToMeasurements?: boolean,
|}

const linkStyles = css`
  &:hover {
    background-color: ${C_NEAR_WHITE};
  }
`

function RequiredLabwareCard(props: RequiredLabwareCardProps) {
  const { loadName, displayName, linkToMeasurements } = props
  const imageSrc =
    loadName in labwareImages
      ? labwareImages[loadName]
      : labwareImages['generic_custom_tiprack']

  return (
    <Flex
      width="50%"
      border={BORDER_SOLID_MEDIUM}
      paddingX={SPACING_3}
      flexDirection={DIRECTION_COLUMN}
      alignItems={ALIGN_CENTER}
    >
      <Flex
        paddingY={SPACING_3}
        height="70%"
        flexDirection={DIRECTION_COLUMN}
        justifyContent={JUSTIFY_CENTER}
      >
        <img
          css={css`
            width: 100%;
            max-height: 100%;
          `}
          src={imageSrc}
        />
      </Flex>
      <Text fontSize={FONT_SIZE_BODY_2}>{displayName}</Text>
      {linkToMeasurements && (
        <Link
          external
          padding={`${SPACING_3} ${SPACING_2}`}
          flex="0.6"
          textTransform={TEXT_TRANSFORM_UPPERCASE}
          textAlign={TEXT_ALIGN_CENTER}
          fontSize={FONT_SIZE_BODY_1}
          color="inherit"
          css={linkStyles}
          href={`${LABWARE_LIBRARY_PAGE_PATH}/${loadName}`}
        >
          {VIEW_TIPRACK_MEASUREMENTS}
        </Link>
      )}
    </Flex>
  )
}

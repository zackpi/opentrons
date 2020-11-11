// @flow
import * as React from 'react'
import { Provider } from 'react-redux'
import { mount } from 'enzyme'
import { act } from 'react-dom/test-utils'
import * as Calibration from '../../../calibration'
import { mockCalibrationStatus } from '../../../calibration/__fixtures__'
import * as Fixtures from '../../../sessions/__fixtures__'
import * as Sessions from '../../../sessions'
import type { State } from '../../../types'
import { ResultsSummary } from '../ResultsSummary'
import { saveAs } from 'file-saver'
import { Box, PrimaryBtn } from '@opentrons/components'

jest.mock('file-saver')
jest.mock('../../../calibration/selectors')

const mockSaveAs: JestMockFn<
  [Blob, string],
  $Call<typeof saveAs, Blob, string>
> = saveAs

const mockGetCalibrationStatus: JestMockFn<
  [State, string],
  $Call<typeof Calibration.getCalibrationStatus, State, string>
> = Calibration.getCalibrationStatus

const mockSessionDetails = Fixtures.mockRobotCalibrationCheckSessionDetails

describe('ResultsSummary', () => {
  let render
  let mockStore
  let dispatch
  let mockDeleteSession

  const getExitButton = wrapper => wrapper.find(PrimaryBtn)

  const getSaveLink = wrapper =>
    wrapper.find('[children="Download JSON summary"]').find('a')
  const getResultsParent = wrapper => wrapper.children(Box).at(0)
  const getDeckParent = wrapper =>
    getResultsParent(wrapper)
      .children()
      .at(0)
      .children()
      .at(0)
  const getPipParent = wrapper =>
    getResultsParent(wrapper)
      .children()
      .at(0)
      .children()
      .at(1)
  const getLeftPipParent = wrapper =>
    getPipParent(wrapper)
      .children()
      .at(0)
      .children()
      .at(0)
  const getRightPipParent = wrapper =>
    getPipParent(wrapper)
      .children()
      .at(0)
      .children()
      .at(1)
  beforeEach(() => {
    mockDeleteSession = jest.fn()
    const mockSendCommands = jest.fn()
    mockGetCalibrationStatus.mockReturnValue(mockCalibrationStatus)
    dispatch = jest.fn()
    mockStore = {
      subscribe: () => {},
      getState: () => ({
        robotApi: {},
      }),
      dispatch,
    }
    render = (
      props: $Shape<React.ElementProps<typeof ResultsSummary>> = {}
    ) => {
      const {
        pipMount = 'left',
        isMulti = false,
        tipRack = Fixtures.mockDeckCalTipRack,
        calBlock = null,
        sendCommands = mockSendCommands,
        cleanUpAndExit = mockDeleteSession,
        currentStep = Sessions.CHECK_STEP_RESULTS_SUMMARY,
        sessionType = Sessions.SESSION_TYPE_CALIBRATION_HEALTH_CHECK,
        comparisonsByPipette = mockSessionDetails.comparisonsByPipette,
        instruments = mockSessionDetails.instruments,
      } = props
      return mount(
        <ResultsSummary
          isMulti={isMulti}
          mount={pipMount}
          tipRack={tipRack}
          calBlock={calBlock}
          sendCommands={sendCommands}
          cleanUpAndExit={cleanUpAndExit}
          currentStep={currentStep}
          sessionType={sessionType}
          comparisonsByPipette={comparisonsByPipette}
          instruments={instruments}
        />,
        {
          wrappingComponent: Provider,
          wrappingComponentProps: { store: mockStore },
        }
      )
    }
  })

  afterEach(() => {
    jest.resetAllMocks()
  })

  it('displays good deck calibration result', () => {
    const wrapper = render()
    const deckParent = getDeckParent(wrapper)
    expect(deckParent.text()).toEqual(
      expect.stringContaining('robot deck calibration')
    )
    expect(deckParent.find('RenderResult').text()).toEqual(
      expect.stringContaining('Good calibration')
    )
  })

  it('summarizes both pipettes & tip length calibrations if comparisons have been made', () => {
    const wrapper = render()
    const leftPipParent = getLeftPipParent(wrapper)
    const rightPipParent = getRightPipParent(wrapper)
    // left pipette & tip length comparison
    expect(leftPipParent.text()).toEqual(
      expect.stringContaining('left pipette')
    )
    expect(leftPipParent.text()).toEqual(
      expect.stringContaining('pipette offset calibration')
    )
    expect(
      leftPipParent
        .find('RenderResult')
        .at(0)
        .text()
    ).toEqual(expect.stringContaining('Good calibration'))
    expect(leftPipParent.text()).toEqual(
      expect.stringContaining('tip length calibration')
    )
    expect(
      leftPipParent
        .find('RenderResult')
        .at(1)
        .text()
    ).toEqual(expect.stringContaining('Good calibration'))

    // right pipette & tip length comparison
    expect(rightPipParent.text()).toEqual(
      expect.stringContaining('pipette offset calibration')
    )
    expect(
      rightPipParent
        .find('RenderResult')
        .at(0)
        .text()
    ).toEqual(expect.stringContaining('Recalibration recommended'))
    expect(rightPipParent.text()).toEqual(
      expect.stringContaining('tip length calibration')
    )
    expect(
      rightPipParent
        .find('RenderResult')
        .at(1)
        .text()
    ).toEqual(expect.stringContaining('Recalibration recommended'))
  })

  it('summarizes neither pipette if no comparisons have been made', () => {
    const emptyComparison = {
      first: {},
      second: {},
    }
    const wrapper = render({
      comparisonsByPipette: emptyComparison,
    })
    const leftPipParent = getLeftPipParent(wrapper)
    const rightPipParent = getRightPipParent(wrapper)
    expect(leftPipParent.exists()).toBe(false)
    expect(rightPipParent.exists()).toBe(false)
  })

  it('does not summarize second pipette if none present', () => {
    const wrapper = render({
      instruments: [mockSessionDetails.instruments[0]],
    })
    const leftPipParent = getLeftPipParent(wrapper)
    const rightPipParent = getRightPipParent(wrapper)

    expect(leftPipParent.exists()).toBe(true)
    expect(rightPipParent.exists()).toBe(false)
  })

  it('exits when button is clicked', () => {
    const wrapper = render()
    act(() => getExitButton(wrapper).invoke('onClick')())
    wrapper.update()

    expect(mockDeleteSession).toHaveBeenCalled()
  })

  it('saves the calibration report when the button is clicked', () => {
    const wrapper = render()
    act(() => getSaveLink(wrapper).invoke('onClick')())
    wrapper.update()
    expect(mockSaveAs).toHaveBeenCalled()
  })
})

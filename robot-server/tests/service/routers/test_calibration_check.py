import pytest
from unittest.mock import MagicMock
import asyncio
from uuid import UUID

from opentrons.hardware_control import HardwareAPILike, ThreadManager, API
from opentrons.server.endpoints.calibration.session \
    import CheckCalibrationSession, CalibrationCheckState, CalibrationCheckTrigger
from starlette.testclient import TestClient
from opentrons import types

from robot_server.service.app import app
from robot_server.service.dependencies import get_hardware,\
    get_calibration_session_manager
from robot_server.service.models.calibration_check import SessionType


@pytest.fixture
def mock_cal_session():
    m = MagicMock(spec=CheckCalibrationSession)

    m.current_state_name = CalibrationCheckState.preparingPipette
    m.get_potential_triggers.return_value = {
        CalibrationCheckTrigger.jog,
        CalibrationCheckTrigger.pick_up_tip,
        CalibrationCheckTrigger.exit
    }

    get_calibration_session_manager().sessions[SessionType.check] = m
    yield m
    del get_calibration_session_manager().sessions[SessionType.check]


@pytest.mark.parametrize(
    argnames=("path", "method",),
    argvalues=(
        ("session", "GET",),
        ("session/loadLabware", "POST",),
        ("session/preparePipette", "POST"),
        ("session/pickUpTip", "POST"),
        ("session/invalidateTip", "POST"),
        ("session/confirmTip", "POST"),
        ("session/jog", "POST"),
        ("session/confirmStep", "POST"),
        ("session", "DELETE"),
    )
)
def test_get_api_needs_session(api_client, path, method):
    """Test that api requiring a current session fail"""
    r = api_client.request(method=method, url=f"/calibration/check/{path}")
    assert r.status_code == 404
    assert r.json() == {
        "errors": [{
            "title": "No session",
            "status": "404",
            "detail":  "No check session exists. Please create one.",
            "links": {"createSession": "/calibration/check/session"}
        }]
    }


@pytest.mark.parametrize(
    argnames=("path", "method",),
    argvalues=(
            ("session", "GET",),
            ("session/loadLabware", "POST",),
            ("session/preparePipette", "POST"),
            ("session/pickUpTip", "POST"),
            ("session/invalidateTip", "POST"),
            ("session/confirmTip", "POST"),
            ("session/jog", "POST"),
            ("session/confirmStep", "POST"),
            ("session", "DELETE"),
    )
)
def test_api_return_session_status(api_client, mock_cal_session, path, method):
    """Test that each endpoint returns the session status"""
    resp = api_client.request(method=method, url=f"/calibration/check/{path}")

    assert resp.status_code == 200
    # Result of mock data
    assert resp.json() == {
        'data': {
            'attributes': {
                'currentStep': 'preparingPipette',
                'instruments': {},
                'labware': []
            },
            'type': 'a'
        },
        'links': {
            'delete_session': {
                'href': '/calibration/check/session',
                'meta': {'params': {}}
            },
            'jog': {
                'href': '/calibration/check/session/jog',
                'meta': {'params': {}}
            },
            'pick_up_tip': {
                'href': '/calibration/check/session/pickUpTip',
                'meta': {'params': {}}}
        }
    }


########################################
# Below are ports of the aiohttp tests.
########################################

@pytest.fixture
def calibration_check_hardware():
    hardware = ThreadManager(API.build_hardware_simulator)

    hw = hardware._backend
    hw._attached_instruments[types.Mount.LEFT] = {
        'model': 'p10_single_v1', 'id': 'fake10pip'
    }
    hw._attached_instruments[types.Mount.RIGHT] = {
        'model': 'p300_single_v1', 'id': 'fake300pip'
    }

    # old_config = config.robot_configs.load()
    try:
        yield hardware
    finally:
        # config.robot_configs.clear()
        # hardware.set_config(old_config)
        hardware.clean_up()


@pytest.fixture
def cal_check_api_client(calibration_check_hardware) -> TestClient:
    async def get_hardware_override() -> HardwareAPILike:
        """Override for get_hardware dependency"""
        return calibration_check_hardware

    app.dependency_overrides[get_hardware] = get_hardware_override
    return TestClient(app)


@pytest.fixture
def cal_check_session(calibration_check_hardware) -> CheckCalibrationSession:
    new_session = asyncio.get_event_loop().run_until_complete(
        CheckCalibrationSession.build(calibration_check_hardware)
    )
    get_calibration_session_manager().sessions[SessionType.check] = new_session
    return new_session


def test_load_labware(cal_check_api_client, cal_check_session):
    resp = cal_check_api_client.post('/calibration/check/session/loadLabware')
    assert resp.status_code == 200
 
    # check that params exist
    assert cal_check_session._deck['8']
    assert cal_check_session._deck['8'].name == 'opentrons_96_tiprack_10ul'
    assert cal_check_session._deck['6']
    assert cal_check_session._deck['6'].name == 'opentrons_96_tiprack_300ul'


async def test_move_to_position(cal_check_api_client, cal_check_session):
    # load labware on deck to enable move
    resp = cal_check_api_client.post('/calibration/check/session/loadLabware')
    status = resp.json()

    pip_id = list(status['instruments'].keys())[0]

    mount = types.Mount.LEFT
    tiprack_id = status['instruments'][pip_id]['tiprack_id']
    # temporarily convert back to UUID to access well location
    uuid_tiprack = UUID(tiprack_id)
    uuid_pipette = UUID(pip_id)

    well = cal_check_session._moves.preparingPipette[uuid_tiprack][uuid_pipette].well

    resp = cal_check_api_client.post(
        '/calibration/check/session/preparePipette',
        json={'pipetteId': pip_id})

    assert resp.status_code == 200

    curr_pos = await cal_check_session.hardware.gantry_position(mount)
    assert curr_pos == (well.top()[0] + types.Point(0, 0, 10))


async def test_jog_pipette(cal_check_api_client, cal_check_session):
    cal_check_session._set_current_state('preparingPipette')

    pipette_id = list(cal_check_session.pipette_status.keys())[0]
    mount = types.Mount.LEFT

    old_pos = await cal_check_session.hardware.gantry_position(mount)
    resp = cal_check_api_client.post(
        '/calibration/check/session/jog',
        json={'pipetteId': pipette_id, 'vector': [0, -1, 0]})

    assert resp.status_code == 200

    new_pos = await cal_check_session.hardware.gantry_position(mount)

    assert (new_pos - old_pos) == types.Point(0, -1, 0)


async def test_pickup_tip(cal_check_api_client, cal_check_session):
    cal_check_api_client.post('/calibration/check/session/loadLabware')

    cal_check_session._set_current_state('preparingPipette')

    pipette_id = list(cal_check_session.pipette_status.keys())[0]
    resp = cal_check_api_client.post(
        '/calibration/check/session/pickUpTip',
        json={'pipetteId': pipette_id})

    text = resp.json()
    assert resp.status_code == 200
    assert text['instruments'][pipette_id]['has_tip'] is True
    assert text['instruments'][pipette_id]['tip_length'] > 0.0


def test_invalidate_tip(cal_check_api_client, cal_check_session):
    cal_check_api_client.post('/calibration/check/session/loadLabware')

    cal_check_session._set_current_state('preparingPipette')
    pipette_id = list(cal_check_session.pipette_status.keys())[0]
    resp = cal_check_api_client.post(
        '/calibration/check/session/invalidateTip',
        json={'pipetteId': pipette_id})
    assert resp.status_code == 409
    resp = cal_check_api_client.post(
        '/calibration/check/session/pickUpTip',
        json={'pipetteId': pipette_id})
    text = resp.json()
    assert text['instruments'][pipette_id]['has_tip'] is True

    resp = cal_check_api_client.post(
        '/calibration/check/session/invalidateTip',
        json={'pipetteId': pipette_id})
    text = resp.json()
    assert text['instruments'][pipette_id]['has_tip'] is False
    assert resp.status_code == 200


def test_drop_tip(cal_check_api_client, cal_check_session):
    cal_check_api_client.post('/calibration/check/session/loadLabware')

    pipette_id = list(cal_check_session.pipette_status.keys())[0]
    resp = cal_check_api_client.post(
        '/calibration/check/session/preparePipette',
        json={'pipetteId': pipette_id})
    assert resp.status_code == 200
    resp = cal_check_api_client.post(
        '/calibration/check/session/pickUpTip',
        json={'pipetteId': pipette_id})
    assert resp.status_code == 200
    resp = cal_check_api_client.post(
        '/calibration/check/session/confirmTip',
        json={'pipetteId': pipette_id})
    assert resp.status_code == 200

    text = resp.json()

    assert text['instruments'][pipette_id]['has_tip'] is True

    cal_check_session._set_current_state('checkingHeight')
    resp = cal_check_api_client.post(
        '/calibration/check/session/confirmStep',
        json={'pipetteId': pipette_id})
    assert resp.status_code == 200
    text = resp.json()
    assert text['instruments'][pipette_id]['has_tip'] is False


def _interpret_status_results(status, next_step, curr_pip):
    next_request = status['nextSteps']['links'][next_step]
    next_data = next_request.get('params', {})
    next_url = next_request.get('url', '')
    return next_data[curr_pip], next_url


def _get_pipette(instruments, pip_name):
    for name, data in instruments.items():
        if pip_name == data['model']:
            return name
    return ''


def test_integrated_calibration_check(cal_check_api_client):
    # TODO: Add in next move steps once they are completed
    resp = cal_check_api_client.post('/calibration/check/session')
    assert resp.status_code == 201
    status = resp.json()

    assert set(status['nextSteps']['links'].keys()) == \
        {'loadLabware', 'sessionExit'}
    curr_pip = _get_pipette(status['instruments'], 'p300_multi_v1')

    next_data, url = _interpret_status_results(status, 'loadLabware', curr_pip)

    # Load labware
    resp = cal_check_api_client.post(url, json=next_data)
    status = resp.json()
    assert set(status['nextSteps']['links'].keys()) == \
        {'preparePipette', 'sessionExit'}
    next_data, url = _interpret_status_results(
        status, 'preparePipette', curr_pip)

    # Preparing pipette
    resp = cal_check_api_client.post(url, json=next_data)
    status = resp.json()
    assert set(status['nextSteps']['links'].keys()) == \
        {'jog', 'pickUpTip', 'sessionExit'}
    next_data, url = _interpret_status_results(status, 'jog', curr_pip)

    # Preparing pipette
    resp = cal_check_api_client.post(url, json=next_data)
    status = resp.json()
    assert set(status['nextSteps']['links'].keys()) == \
        {'jog', 'pickUpTip', 'sessionExit'}
    next_data, url = _interpret_status_results(status, 'pickUpTip', curr_pip)

    # Inspecting Tip
    resp = cal_check_api_client.post(url, json=next_data)
    status = resp.json()
    assert set(status['nextSteps']['links'].keys()) == \
        {'confirmTip', 'invalidateTip', 'sessionExit'}
    next_data, url = _interpret_status_results(
        status, 'confirmTip', curr_pip)

    # Checking point one
    resp = cal_check_api_client.post(url, json=next_data)
    status = resp.json()
    assert set(status['nextSteps']['links'].keys()) == \
        {'jog', 'confirmStep', 'sessionExit'}
    next_data, url = _interpret_status_results(
        status, 'confirmStep', curr_pip)

    # Checking point two
    resp = cal_check_api_client.post(url, json=next_data)
    status = resp.json()
    assert set(status['nextSteps']['links'].keys()) == \
        {'jog', 'confirmStep', 'sessionExit'}
    next_data, url = _interpret_status_results(
        status, 'confirmStep', curr_pip)

    # checking point three
    resp = cal_check_api_client.post(url, json=next_data)
    status = resp.json()
    assert set(status['nextSteps']['links'].keys()) == \
        {'jog', 'confirmStep', 'sessionExit'}
    next_data, url = _interpret_status_results(status, 'confirmStep', curr_pip)

    # checking height
    resp = cal_check_api_client.post(url, json=next_data)
    status = resp.json()
    assert set(status['nextSteps']['links'].keys()) == \
        {'confirmStep', 'jog', 'sessionExit'}
    next_data, url = _interpret_status_results(status, 'confirmStep', curr_pip)

    # checkingPoint three
    resp = cal_check_api_client.post(url, json=next_data)
    status = resp.json()
    assert set(status['nextSteps']['links'].keys()) == {'sessionExit'}

    # # TODO make the test work for a second pipette
    # curr_pip = _get_pipette(status['instruments'], 'p10_single_v1')
    #
    # next_data, url = _interpret_status_results(
    #     status, 'jog', curr_pip)
    #
    # # checkingPointOne
    # resp = await cal_check_api_client.post(url, json=next_data)
    # status = await resp.json()
    # assert set(status['nextSteps']['links'].keys()) == \
    #        {'jog', 'sessionExit', 'confirmStep'}
    # next_data, url = _interpret_status_results(status, 'jog', curr_pip)
    #
    # # checkingPointOne
    # resp = await cal_check_api_client.post(url, json=next_data)
    # status = await resp.json()
    # assert set(status['nextSteps']['links'].keys()) == \
    #        {'confirmStep', 'jog', 'sessionExit'}
    # next_data, url = _interpret_status_results(status, 'confirmStep',
    #                                            curr_pip)
    #
    # # checkingPointTwo
    # resp = await cal_check_api_client.post(url, json=next_data)
    # status = await resp.json()
    # assert set(status['nextSteps']['links'].keys()) == \
    #        {'jog', 'confirmStep', 'sessionExit'}
    # next_data, url = _interpret_status_results(
    #     status, 'confirmStep', curr_pip)
    #
    # # checking point three
    # resp = await cal_check_api_client.post(url, json=next_data)
    # status = await resp.json()
    # assert set(status['nextSteps']['links'].keys()) == \
    #     {'jog', 'confirmStep', 'sessionExit'}
    # next_data, url = _interpret_status_results(
    #     status, 'confirmStep', curr_pip)
    #
    # # Checking height
    # resp = await cal_check_api_client.post(url, json=next_data)
    # status = await resp.json()
    # assert set(status['nextSteps']['links'].keys()) == \
    #       {'jog', 'confirmStep', 'sessionExit'}
    # next_data, url = _interpret_status_results(
    #     status, 'confirmStep', curr_pip)
    #
    # # returning tip
    # resp = await cal_check_api_client.post(url, json=next_data)
    # status = await resp.json()
    # assert set(status['nextSteps']['links'].keys()) == {'sessionExit'}
    #
    # next_data, url = _interpret_status_results(status,
    #                               'checkHeight', curr_pip)
    # resp = await cal_check_api_client.post(url, json=next_data)
    # status = await resp.json()
    # assert set(status['nextSteps']['links'].keys()) == {'dropTip'}
    #
    # next_data, url = _interpret_status_results(status, 'dropTip', curr_pip)
    # resp = await cal_check_api_client.post(url, json=next_data)
    # status = await resp.json()
    # assert set(status['nextSteps']['links'].keys()) == {'moveToTipRack'}

    resp = cal_check_api_client.delete('/calibration/check/session')
    assert resp.status_code == 200

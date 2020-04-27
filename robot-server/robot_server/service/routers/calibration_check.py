import typing
from starlette import status as http_status_codes
from fastapi import APIRouter, Depends
from opentrons.server.endpoints.calibration.session import SessionManager, \
    CheckCalibrationSession, CalibrationSession, CalibrationCheckTrigger
from starlette.requests import Request

from robot_server.service.dependencies import get_calibration_session_manager
from robot_server.service.models import calibration_check as model
from robot_server.service.errors import RobotServerError, Error
from robot_server.service.models.json_api.resource_links import ResourceLink
from robot_server.service.models.json_api.response import ResponseDataModel, ResponseModel
from robot_server.service.models.json_api import ResourceTypes

CalibrationSessionStatusResponseM = ResponseDataModel[model.CalibrationSessionStatus]
CalibrationSessionStatusResponse = ResponseModel[CalibrationSessionStatusResponseM]

router = APIRouter()


def get_current_session(session_type: model.SessionType,
                        api_router: APIRouter) -> CalibrationSession:
    """Get the current session or raise a RobotServerError"""
    manager = get_calibration_session_manager()
    session = manager.sessions.get(session_type.value)
    if not session:
        # There is no session raise error
        raise RobotServerError(
            status_code=http_status_codes.HTTP_404_NOT_FOUND,
            error=Error(
                title="No session",
                detail=f"No {session_type} session exists. Please create one.",
                links={
                    "createSession": api_router.url_path_for(
                        create_session.__name__,
                        session_type=session_type.value)
                     }
                 )
        )
    return session


def get_check_session() -> CheckCalibrationSession:
    """
    A dependency for handlers that require a current session.

    Get the current active check calibration session
    """
    from robot_server.service.app import app
    # Return an upcasted CalibrationSession
    return get_current_session(session_type=model.SessionType.check,
                               api_router=app)


@router.get('/{session_type}/session',
            response_model=CalibrationSessionStatusResponse,
            response_model_exclude_unset=True,)
async def get_session(
        request: Request,
        session_type: model.SessionType,
        session: CheckCalibrationSession = Depends(
            get_check_session)) -> CalibrationSessionStatusResponse:
    return create_session_response(session, request)


@router.post('/{session_type}/session',
             response_model=CalibrationSessionStatusResponse,
             status_code=http_status_codes.HTTP_201_CREATED,
             response_model_exclude_unset=True)
async def create_session(
        request: Request,
        session_type: model.SessionType,
        session_manager: SessionManager = Depends(
            get_calibration_session_manager))\
        -> CalibrationSessionStatusResponse:
    pass

# @router.post('/{session_type}/session/move')
# async def move(session_type: model.SessionType,
#                session_manager: SessionManager = Depends(
#                    get_calibration_session_manager)):
#     pass


@router.post('/{session_type}/session/loadLabware',
             response_model=CalibrationSessionStatusResponse,
             response_model_exclude_unset=True)
async def load_labware(
        request: Request,
        session_type: model.SessionType,
        session: CheckCalibrationSession = Depends(get_check_session)) -> CalibrationSessionStatusResponse:
    return create_session_response(session, request)


@router.post('/{session_type}/session/preparePipette',
             response_model=CalibrationSessionStatusResponse,
             response_model_exclude_unset=True)
async def prepare_pipette(
        request: Request,
        session_type: model.SessionType,
        session: CheckCalibrationSession = Depends(get_check_session)) -> CalibrationSessionStatusResponse:
    return create_session_response(session, request)


@router.post('/{session_type}/session/pickUpTip',
             response_model=CalibrationSessionStatusResponse,
             response_model_exclude_unset=True)
async def pick_up_tip(
        request: Request,
        session_type: model.SessionType,
        session: CheckCalibrationSession = Depends(get_check_session)) -> CalibrationSessionStatusResponse:
    return create_session_response(session, request)


@router.post('/{session_type}/session/invalidateTip',
             response_model=CalibrationSessionStatusResponse,
             response_model_exclude_unset=True)
async def invalidate_tip(
        request: Request,
        session_type: model.SessionType,
        session: CheckCalibrationSession = Depends(get_check_session))-> CalibrationSessionStatusResponse:
    return create_session_response(session, request)


@router.post('/{session_type}/session/confirmTip',
             response_model=CalibrationSessionStatusResponse,
             response_model_exclude_unset=True)
async def confirm_tip(
        request: Request,
        session_type: model.SessionType,
        session: CheckCalibrationSession = Depends(get_check_session)) -> CalibrationSessionStatusResponse:
    return create_session_response(session, request)


@router.post('/{session_type}/session/jog',
             response_model=CalibrationSessionStatusResponse,
             response_model_exclude_unset=True)
async def jog(
        request: Request,
        session_type: model.SessionType,
        session: CheckCalibrationSession = Depends(get_check_session))-> CalibrationSessionStatusResponse:
    return create_session_response(session, request)


@router.post('/{session_type}/session/confirmStep',
             response_model=CalibrationSessionStatusResponse,
             response_model_exclude_unset=True)
async def confirm_step(
        request: Request,
        session_type: model.SessionType,
        session: CheckCalibrationSession = Depends(get_check_session))-> CalibrationSessionStatusResponse:
    return create_session_response(session, request)


@router.delete('/{session_type}/session',
               response_model=CalibrationSessionStatusResponse,
               response_model_exclude_unset=True)
async def delete_session(
        request: Request,
        session_type: model.SessionType,
        session: CheckCalibrationSession = Depends(get_check_session)) -> CalibrationSessionStatusResponse:
    return create_session_response(session, request)


TRIGGER_TO_NAME = {
    CalibrationCheckTrigger.load_labware: load_labware.__name__,
    CalibrationCheckTrigger.prepare_pipette: prepare_pipette.__name__,
    CalibrationCheckTrigger.jog: jog.__name__,
    CalibrationCheckTrigger.pick_up_tip: pick_up_tip.__name__,
    CalibrationCheckTrigger.confirm_tip_attached: confirm_tip.__name__,
    CalibrationCheckTrigger.invalidate_tip: invalidate_tip.__name__,
    CalibrationCheckTrigger.confirm_step: confirm_step.__name__,
    CalibrationCheckTrigger.exit: delete_session.__name__,
    # CalibrationCheckTrigger.reject_calibration: "reject_calibration",
    # CalibrationCheckTrigger.no_pipettes: "no_pipettes",
}


def create_next_step_links(session: 'CheckCalibrationSession',
                           potential_triggers: typing.Set[str],
                           api_router: APIRouter) \
        -> typing.Dict[str, ResourceLink]:
    """Create the links for next steps in the process"""
    links = {}
    for trigger in potential_triggers:
        route_name = TRIGGER_TO_NAME.get(trigger)
        if route_name:
            url = api_router.url_path_for(
                route_name,
                session_type=model.SessionType.check.value)

            params = session.format_params(trigger)
            if url:
                links[route_name] = ResourceLink(
                    href=url,
                    meta={
                        'params': params
                    }
                )
    return links


def create_session_response(session: CheckCalibrationSession,
                            request: Request) \
        -> CalibrationSessionStatusResponse:
    """Create session response"""
    links = create_next_step_links(session,
                                   session.get_potential_triggers(),
                                   request.app)
    instruments = {
        str(k): model.AttachedPipette(model=v.model,
                                      name=v.name,
                                      tip_length=v.tip_length,
                                      has_tip=v.has_tip,
                                      tiprack_id=v.tiprack_id)
        for k, v in session.pipette_status().items()
    }
    labware = [
            model.LabwareStatus(alternatives=data.alternatives,
                                slot=data.slot,
                                id=data.id,
                                forPipettes=data.forPipettes,
                                loadName=data.loadName,
                                namespace=data.namespace,
                                version=data.version) for data in
            session.labware_status.values()
        ]

    status = model.CalibrationSessionStatus(
        instruments=instruments,
        currentStep=session.current_state_name,
        labware=labware
    )
    return CalibrationSessionStatusResponse(
        data=CalibrationSessionStatusResponseM(
            attributes=status,
            type=ResourceTypes.a
        ),
        links=links,
    )

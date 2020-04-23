from fastapi import APIRouter, Depends
from opentrons.server.endpoints.calibration.session import SessionManager

from robot_server.service.dependencies import get_calibration_session_manager
from robot_server.service.models import calibration_check as model

router = APIRouter()


@router.get('/{session_type}/session')
async def get_session(
        session_type=model.SessionTypes,
        session_manager: SessionManager = Depends(
            get_calibration_session_manager)):
    pass


@router.post('/{session_type}/session')
async def create_session(
        session_type=model.SessionTypes,
        session_manager: SessionManager = Depends(
            get_calibration_session_manager)):
    pass


@router.post('/{session_type}/session/move')
async def move(session_type=model.SessionTypes,
               session_manager: SessionManager = Depends(
                   get_calibration_session_manager)):
    pass


@router.post('/{session_type}/session/loadLabware')
async def load_labware(session_type=model.SessionTypes,
                       session_manager: SessionManager = Depends(
                           get_calibration_session_manager)):
    pass


@router.post('/{session_type}/session/preparePipette')
async def prepare_pipette(session_type=model.SessionTypes,
                          session_manager: SessionManager = Depends(
                              get_calibration_session_manager)):
    pass


@router.post('/{session_type}/session/pickUpTip')
async def pick_up_tip(session_type=model.SessionTypes,
                      session_manager: SessionManager = Depends(
                          get_calibration_session_manager)):
    pass


@router.post('/{session_type}/session/invalidateTip')
async def invalidate_tip(session_type=model.SessionTypes,
                         session_manager: SessionManager = Depends(
                             get_calibration_session_manager)):
    pass


@router.post('/{session_type}/session/confirmTip')
async def confirm_tip(session_type=model.SessionTypes,
                      session_manager: SessionManager = Depends(
                          get_calibration_session_manager)):
    pass


@router.post('/{session_type}/session/jog')
async def jog(session_type=model.SessionTypes,
              session_manager: SessionManager = Depends(
                  get_calibration_session_manager)):
    pass


@router.post('/{session_type}/session/confirmStep')
async def confirm_step(session_type=model.SessionTypes,
                       session_manager: SessionManager = Depends(
                           get_calibration_session_manager)):
    pass


@router.delete('/{session_type}/session')
async def delete_session(session_type=model.SessionTypes,
                         session_manager: SessionManager = Depends(
                             get_calibration_session_manager)):
    pass

from uuid import UUID
from fastapi import APIRouter, HTTPException
from starlette.status import HTTP_400_BAD_REQUEST, \
    HTTP_422_UNPROCESSABLE_ENTITY
from pydantic import ValidationError

from robot_server.service.models.item import Item
from robot_server.service.models.json_api.request import RequestModel, RequestDataModel
from robot_server.service.models.json_api.response import ResponseModel, ResponseDataModel
from robot_server.service.models.json_api.errors import ErrorResponse

router = APIRouter()

ItemRequest = RequestModel[Item]
ItemResponse = ResponseModel[Item]


@router.get("/items/{item_id}",
            description="Get an individual item by its ID",
            summary="Get an individual item",
            response_model=ItemResponse,
            response_model_exclude_unset=True,
            responses={
                HTTP_422_UNPROCESSABLE_ENTITY: {"model": ErrorResponse},
            })
async def get_item(item_id: str) -> ItemResponse:
    try:
        # NOTE(isk: 3/10/20): mock DB / robot response
        item = Item(name="apple", quantity=10, price=1.20)
        data = RequestDataModel(id=item_id, attributes=item, type=Item.__name__)
        return ItemResponse(data=data, links={"self": f'/items/{item_id}'})
    except ValidationError as e:
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE_ENTITY,
            detail=e
        )


@router.post("/items",
             description="Create an item",
             summary="Create an item via post route",
             response_model=ItemResponse,
             response_model_exclude_unset=True,
             responses={
                 HTTP_400_BAD_REQUEST: {"model": ErrorResponse},
                 HTTP_422_UNPROCESSABLE_ENTITY: {"model": ErrorResponse},
             })
async def create_item(
    item_request: ItemRequest
) -> ItemResponse:
    item = item_request.data.attributes
    # NOTE(isk: 3/10/20): mock DB / robot response
    data = ResponseDataModel(id="33", attributes=item, type=Item.__name__)
    return ItemResponse(data=data, links={"self": f'/items/{data.id}'})

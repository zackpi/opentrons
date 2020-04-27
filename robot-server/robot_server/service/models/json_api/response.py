from typing import Generic, TypeVar, Optional, Dict, Union, List
from pydantic import Field, BaseModel
from pydantic.generics import GenericModel

from .resource_links import ResourceLinks


DataT = TypeVar('DataT')


class ResponseDataModel(GenericModel, Generic[DataT]):
    """
    """
    id: Optional[str] = \
        Field(None,
              description="id member represents a resource object.")
    type: str = \
        Field(...,
              description="type member is used to describe resource objects"
                          " that share common attributes.")
    attributes: DataT = \
        Field({},
              description="an attributes object representing some of the"
                          " resource’s data.")

    # Note(isk: 3/13/20): Need this to validate attribute default
    # see here: https://pydantic-docs.helpmanual.io/usage/model_config/
    class Config:
        validate_all = True


class BaseResponseModel(BaseModel):
    """Basic response model schema"""

    meta: Optional[Dict] = \
        Field(None,
              description="a meta object that contains non-standard"
                          " meta-information.")

    links: Optional[ResourceLinks] = \
        Field(None,
              description="a links object related to the primary data.")


class ResponseModel(GenericModel, Generic[DataT], BaseResponseModel):
    """Response with a single entity"""
    data: ResponseDataModel[DataT] = \
        Field(...,
              description="the document’s 'primary data'",)


class MultiResponseModel(GenericModel, Generic[DataT], BaseResponseModel):
    """Response with a multiple entities"""
    data: List[ResponseDataModel[DataT]] = \
        Field(...,
              description="the document’s 'primary data'",)
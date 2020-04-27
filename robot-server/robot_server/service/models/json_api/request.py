from typing import Generic, TypeVar, Optional, Any, Type
from pydantic import Field
from pydantic.generics import GenericModel


DataT = TypeVar('DataT')


class RequestDataModel(GenericModel, Generic[DataT]):
    """
    """
    id: Optional[str] = \
        Field(None,
              description="id member represents a resource object and is not"
                          " required when the resource object originates at"
                          " the client and represents a new resource to be"
                          " created on the server.")
    type: str = \
        Field(...,
              description="type member is used to describe resource objects"
                          " that share common attributes.")
    attributes: DataT = \
        Field(...,
              description="an attributes object representing some of the"
                          " resource’s data.")


class RequestModel(GenericModel, Generic[DataT]):
    """
    """
    data: RequestDataModel[DataT] = \
        Field(...,
              description="the document’s 'primary data'")

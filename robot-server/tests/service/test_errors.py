import pytest

from pydantic import ValidationError, BaseModel
from starlette.status import HTTP_422_UNPROCESSABLE_ENTITY
from starlette.exceptions import HTTPException

from robot_server.service import errors


class TestModel(BaseModel):
    a: int
    b: str


def test_transform_validation_error_to_json_api_errors():
    with pytest.raises(ValidationError) as e:
        TestModel(**{
            'a': 'woof'
        })
    assert errors.transform_validation_error_to_json_api_errors(
        HTTP_422_UNPROCESSABLE_ENTITY,
        e.value
    ).dict(exclude_unset=True) == {
        'errors': [
            {
                'status': str(HTTP_422_UNPROCESSABLE_ENTITY),
                'detail': "value is not a valid integer",
                'source': {
                    'pointer': '/a'
                },
                'title': 'type_error.integer'
            },
            {
                'status': str(HTTP_422_UNPROCESSABLE_ENTITY),
                'detail': 'field required',
                'source': {
                    'pointer': '/b'
                },
                'title': 'value_error.missing'
            },
        ]
    }


def test_transform_http_exception_to_json_api_errors():
    exc = HTTPException(status_code=404, detail="i failed")
    err = errors.transform_http_exception_to_json_api_errors(
        exc
    ).dict(
        exclude_unset=True
    )
    assert err == {
        'errors': [{
            'status': str(exc.status_code),
            'detail': exc.detail,
            'title': 'Bad Request',
        }]
    }

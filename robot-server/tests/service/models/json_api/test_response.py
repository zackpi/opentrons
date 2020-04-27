from typing import List

from pytest import raises
from pydantic import BaseModel, ValidationError

from robot_server.service.models.json_api.response import ResponseModel, \
    ResponseDataModel, MultiResponseModel
from robot_server.service.models.item import Item


def test_attributes_as_dict():
    MyResponse = ResponseModel[dict]
    obj_to_validate = {
        'data': {'id': '123', 'type': 'item', 'attributes': {}},
    }
    my_response_object = MyResponse(**obj_to_validate)
    assert my_response_object.dict() == {
        'meta': None,
        'links': None,
        'data': {
            'id': '123',
            'type': 'item',
            'attributes': {},
        }
    }


def test_missing_attributes_dict():
    MyResponse = ResponseModel[dict]
    obj_to_validate = {
        'data': {'id': '123', 'type': 'item'}
    }
    my_response_object = MyResponse(**obj_to_validate)
    assert my_response_object.dict() == {
        'meta': None,
        'links': None,
        'data': {
            'id': '123',
            'type': 'item',
            'attributes': {},
        }
    }


def test_missing_attributes_empty_model():
    class EmptyModel(BaseModel):
        pass

    MyResponse = ResponseModel[EmptyModel]
    obj_to_validate = {
        'data': {'id': '123', 'type': 'item'}
    }
    my_response_object = MyResponse(**obj_to_validate)
    assert my_response_object.dict() == {
        'meta': None,
        'links': None,
        'data': {
            'id': '123',
            'type': 'item',
            'attributes': {},
        }
    }
    assert isinstance(my_response_object.data.attributes, EmptyModel)


def test_attributes_as_item_model():
    ItemResponse = ResponseModel[Item]
    obj_to_validate = {
        'meta': None,
        'links': None,
        'data': {
            'id': '123',
            'type': 'item',
            'attributes': {
                'name': 'apple',
                'quantity': 10,
                'price': 1.20
            }
        }
    }
    my_response_obj = ItemResponse(**obj_to_validate)
    assert my_response_obj.dict() == {
        'meta': None,
        'links': None,
        'data': {
            'id': '123',
            'type': 'item',
            'attributes': {
                'name': 'apple',
                'quantity': 10,
                'price': 1.20,
            }
        }
    }


def test_list_item_model():
    ItemResponse = MultiResponseModel[Item]
    obj_to_validate = {
        'meta': None,
        'links': None,
        'data': [
            {
                'id': '123',
                'type': 'item',
                'attributes': {
                    'name': 'apple',
                    'quantity': 10,
                    'price': 1.20
                },
            },
            {
                'id': '321',
                'type': 'item',
                'attributes': {
                    'name': 'banana',
                    'quantity': 20,
                    'price': 2.34
                },
            },
        ],
    }
    my_response_obj = ItemResponse(**obj_to_validate)
    assert my_response_obj.dict() == {
        'meta': None,
        'links': None,
        'data': [
            {
                'id': '123',
                'type': 'item',
                'attributes': {
                    'name': 'apple',
                    'quantity': 10,
                    'price': 1.20,
                },
            },
            {
                'id': '321',
                'type': 'item',
                'attributes': {
                    'name': 'banana',
                    'quantity': 20,
                    'price': 2.34,
                },
            },
        ],
    }


def test_attributes_required():
    ItemResponse = ResponseModel[Item]
    obj_to_validate = {
        'data': {'id': '123', 'type': 'item', 'attributes': None}
    }
    with raises(ValidationError) as e:
        ItemResponse(**obj_to_validate)

    assert e.value.errors() == [
        {
            'loc': ('data', 'attributes'),
            'msg': 'none is not an allowed value',
            'type': 'type_error.none.not_allowed',
        },
    ]


def test_attributes_as_item_model_empty_dict():
    ItemResponse = ResponseModel[Item]
    obj_to_validate = {
        'data': {
            'id': '123',
            'type': 'item',
            'attributes': {}
        }
    }
    with raises(ValidationError) as e:
        ItemResponse(**obj_to_validate)

    assert e.value.errors() == [
        {
            'loc': ('data', 'attributes', 'name'),
            'msg': 'field required',
            'type': 'value_error.missing'
        }, {
            'loc': ('data', 'attributes', 'quantity'),
            'msg': 'field required',
            'type': 'value_error.missing'
        }, {
            'loc': ('data', 'attributes', 'price'),
            'msg': 'field required',
            'type': 'value_error.missing'
        },
    ]


def test_resource_object_constructor():
    ItemResponse = ResponseModel[Item]
    item = Item(name='pear', price=1.2, quantity=10)
    document = ItemResponse(
        data=ResponseDataModel[Item](
            id='abc123',
            type="item",
            attributes=item
        )
    ).dict()

    assert document == {
        'data': {
            'id': 'abc123',
            'type': 'item',
            'attributes': {
                'name': 'pear',
                'price': 1.2,
                'quantity': 10,
            }
        },
        'meta': None,
        'links': None
    }


def test_resource_object_constructor_no_attributes():
    IdentifierResponse = ResponseModel[dict]
    document = IdentifierResponse(
        data=ResponseDataModel[dict](id='abc123', type='item')
    ).dict()

    assert document == {
        'data': {
            'id': 'abc123',
            'type': 'item',
            'attributes': {},
        },
        'meta': None,
        'links': None
    }


def test_resource_object_constructor_with_list_response():
    ItemResponse = MultiResponseModel[Item]
    item = Item(name='pear', price=1.2, quantity=10)
    document = ItemResponse(data=[
        ResponseDataModel[Item](
            id='abc123',
            attributes=item,
            type='item'
        )
    ]).dict()

    assert document == {
        'data':[{
            'id': 'abc123',
            'type': 'item',
            'attributes': {
                'name': 'pear',
                'price': 1.2,
                'quantity': 10,
            }
        }],
        'links': None,
        'meta': None
    }


def test_response_constructed_with_resource_object():
    ItemResponse = ResponseModel[Item]
    item = Item(name='pear', price=1.2, quantity=10)
    data = ItemResponse(data=ResponseDataModel[Item](
        id='abc123',
        type='item',
        attributes=item
    ))

    assert data.dict() == {
        'meta': None,
        'links': None,
        "data": {
            'id': 'abc123',
            "type": 'item',
            "attributes": {
                'name': 'pear',
                'price': 1.2,
                'quantity': 10,
            },
        }
    }


def test_response_constructed_with_resource_object_list():
    ItemResponse = MultiResponseModel[Item]
    items = (
        (1, Item(name='apple', price=1.5, quantity=3),),
        (2, Item(name='pear', price=1.2, quantity=10),),
        (3, Item(name='orange', price=2.2, quantity=5),)
    )
    response = ItemResponse(
        data=[
            ResponseDataModel[Item](id=item[0], attributes=item[1], type='item')
            for item in items
        ]
    )
    assert response.dict() == {
        'meta': None,
        'links': None,
        'data': [
            {
                'id': '1',
                'type': 'item',
                'attributes': {
                    'name': 'apple',
                    'price': 1.5,
                    'quantity': 3,
                },
            },
            {
                'id': '2',
                'type': 'item',
                'attributes': {
                    'name': 'pear',
                    'price': 1.2,
                    'quantity': 10,
                },
            },
            {
                'id': '3',
                'type': 'item',
                'attributes': {
                    'name': 'orange',
                    'price': 2.2,
                    'quantity': 5,
                },
            },
        ]
    }

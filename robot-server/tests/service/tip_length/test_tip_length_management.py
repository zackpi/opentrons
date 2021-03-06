PIPETTE_ID = 'pip_1'
LW_HASH = 'fakehash'
FAKE_PIPETTE_ID = 'fake_pip'
WRONG_LW_HASH = 'wronghash'


def test_access_tip_length_calibration(
        api_client, set_up_tip_length_temp_directory):
    expected = {
        'tipLength': 30.5,
        'pipette': PIPETTE_ID,
        'tiprack': LW_HASH,
        'lastModified': None,
        'source': 'unknown',
        'status': {
            'markedAt': None, 'markedBad': False, 'source': None}
    }

    resp = api_client.get(
        f'/calibration/tip_length?pipette_id={PIPETTE_ID}&'
        f'tiprack_hash={LW_HASH}')
    assert resp.status_code == 200
    data = resp.json()['data'][0]
    assert data['type'] == 'TipLengthCalibration'
    data['attributes']['lastModified'] = None
    assert data['attributes'] == expected

    resp = api_client.get(
        f'/calibration/tip_length?pipette_id={FAKE_PIPETTE_ID}&'
        f'tiprack_hash={WRONG_LW_HASH}')
    assert resp.status_code == 200
    assert resp.json()['data'] == []


def test_delete_tip_length_calibration(
        api_client, set_up_pipette_offset_temp_directory):
    resp = api_client.delete(
        f'/calibration/tip_length?pipette_id={FAKE_PIPETTE_ID}&'
        f'tiprack_hash={WRONG_LW_HASH}')
    assert resp.status_code == 404
    body = resp.json()
    assert body == {
        'errors': [{
            'status': '404',
            'title': 'Resource Not Found',
            'detail': "Resource type 'TipLengthCalibration' with id "
                      "'wronghash&fake_pip' was not found"
        }]}

    resp = api_client.delete(
        f'/calibration/tip_length?pipette_id={PIPETTE_ID}&'
        f'tiprack_hash={LW_HASH}')
    assert resp.status_code == 200

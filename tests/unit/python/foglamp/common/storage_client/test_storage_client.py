# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" Test foglamp/common/storage_client/storage_client.py """
import pytest

from unittest.mock import MagicMock, patch
import json
import asyncio
from aiohttp import web
from aiohttp.test_utils import unused_port
from functools import partial

from foglamp.common.service_record import ServiceRecord
from foglamp.common.storage_client.storage_client import _LOGGER, StorageClient, ReadingsStorageClient
from foglamp.common.storage_client.exceptions import *

__copyright__ = "Copyright (c) 2018 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

HOST = '127.0.0.1'
PORT = unused_port()


class FakeFoglampStorageSrvr:

    def __init__(self, *, loop):
        self.loop = loop
        self.app = web.Application(loop=loop)
        self.app.router.add_routes([
            # common table operations
            web.post('/storage/table/{tbl_name}', self.query_with_payload_insert_into_or_update_tbl_handler),
            web.put('/storage/table/{tbl_name}', self.query_with_payload_insert_into_or_update_tbl_handler),
            web.delete('/storage/table/{tbl_name}', self.delete_from_tbl_handler),
            web.get('/storage/table/{tbl_name}', self.query_tbl_handler),
            web.put('/storage/table/{tbl_name}/query', self.query_with_payload_insert_into_or_update_tbl_handler),

            # readings table
            web.post('/storage/reading', self.readings_append),
            web.get('/storage/reading', self.readings_fetch),
            web.put('/storage/reading/query', self.readings_query),
            web.put('/storage/reading/purge', self.readings_purge)
        ])
        self.handler = None
        self.server = None

    async def start(self):

        self.handler = self.app.make_handler()
        self.server = await self.loop.create_server(self.handler, HOST, PORT, ssl=None)

    async def stop(self):
        self.server.close()
        await self.server.wait_closed()
        await self.app.shutdown()
        await self.handler.shutdown()
        await self.app.cleanup()

    async def query_with_payload_insert_into_or_update_tbl_handler(self, request):
        payload = await request.json()

        if payload.get("bad_request", None):
            return web.HTTPBadRequest(reason="bad data", text='{"key": "value"}')

        if payload.get("internal_server_err", None):
            return web.HTTPInternalServerError(reason="something wrong", text='{"key": "value"}')

        return web.json_response({
           "called": payload
        })

    async def delete_from_tbl_handler(self, request):
        try:
            payload = await request.json()

            if payload.get("bad_request", None):
                return web.HTTPBadRequest(reason="bad data", text='{"key": "value"}')

            if payload.get("internal_server_err", None):
                return web.HTTPInternalServerError(reason="something wrong", text='{"key": "value"}')
        except:
            payload = 1

        return web.json_response({
            "called": payload
        })

    async def query_tbl_handler(self, request):

        # add side effect based on query param foo `?foo=`

        res = 1
        if request.query.get('foo', None):
            res = 'foo passed'

        if request.query.get("bad_foo", None):
            return web.HTTPBadRequest(reason="bad data", text='{"key": "value"}')

        if request.query.get("internal_server_err_foo", None):
            return web.HTTPInternalServerError(reason="something wrong", text='{"key": "value"}')

        return web.json_response({
            "called": res
        })

    async def readings_append(self, request):
        payload = await request.json()

        if payload.get("readings", None) is None:
            return web.HTTPBadRequest(reason="bad data", text='{"key": "value"}')

        if payload.get("internal_server_err", None):
            return web.HTTPInternalServerError(reason="something wrong", text='{"key": "value"}')

        return web.json_response({
            "appended": payload
        })

    async def readings_fetch(self, request):
        if request.query.get("id") == "bad_data":
            return web.HTTPBadRequest(reason="bad data", text='{"key": "value"}')

        if request.query.get("id") == "internal_server_err":
            return web.HTTPInternalServerError(reason="something wrong", text='{"key": "value"}')

        return web.json_response({"readings": [],
                                  "start": request.query.get('id'),
                                  "count": request.query.get('count')
                                  })

    async def readings_query(self, request):
        payload = await request.json()

        if payload.get("bad_request", None):
            return web.HTTPBadRequest(reason="bad data", text='{"key": "value"}')

        if payload.get("internal_server_err", None):
            return web.HTTPInternalServerError(reason="something wrong", text='{"key": "value"}')

        return web.json_response({
           "called": payload
        })

    async def readings_purge(self, request):

        if request.query.get('age', None) == "-1":
            return web.HTTPBadRequest(reason="age should not be less than 0", text='{"key": "value"}')

        if request.query.get('size', None) == "4294967296":
            return web.HTTPInternalServerError(reason="unsigned int range", text='{"key": "value"}')

        return web.json_response({
            "called": 1
        })


@pytest.allure.feature("unit")
@pytest.allure.story("common", "storage_client")
class TestStorageClient:

    def test_init(self):
        svc = {"id": 1, "name": "foo", "address": "local", "service_port": 1000, "management_port": 2000,
               "type": "Storage", "protocol": "http"}
        with patch.object(StorageClient, '_get_storage_service', return_value=svc):
            sc = StorageClient(1, 2)
            assert "local:1000" == sc.base_url
            assert "local:2000" == sc.management_api_url

    def test_init_with_invalid_storage_service(self):
        svc = {"id": 1, "name": "foo", "address": "local", "service_port": 1000, "management_port": 2000,
               "type": "xStorage", "protocol": "http"}
        with pytest.raises(Exception) as excinfo:
            with patch.object(StorageClient, '_get_storage_service', return_value=svc):
                sc = StorageClient(1, 2)
        assert excinfo.type is InvalidServiceInstance

    def test_init_with_service_record(self):
        mockServiceRecord = MagicMock(ServiceRecord)
        mockServiceRecord._address = "local"
        mockServiceRecord._type = "Storage"
        mockServiceRecord._port = 1000
        mockServiceRecord._management_port = 2000

        sc = StorageClient(1, 2, mockServiceRecord)
        assert "local:1000" == sc.base_url
        assert "local:2000" == sc.management_api_url

    def test_init_with_invalid_service_record(self):
        with pytest.raises(Exception) as excinfo:
            with patch.object(_LOGGER, "warning") as log:
                sc = StorageClient(1, 2, "blah")
        log.assert_called_once_with("Storage should be a valid FogLAMP micro-service instance")
        assert excinfo.type is InvalidServiceInstance

    def test_init_with_service_record_non_storage_type(self):
        mockServiceRecord = MagicMock(ServiceRecord)
        mockServiceRecord._address = "local"
        mockServiceRecord._type = "xStorage"
        mockServiceRecord._port = 1000
        mockServiceRecord._management_port = 2000

        with pytest.raises(Exception) as excinfo:
            with patch.object(_LOGGER, "warning") as log:
                sc = StorageClient(1, 2, mockServiceRecord)
        log.assert_called_once_with("Storage should be a valid *Storage* micro-service instance")
        assert excinfo.type is InvalidServiceInstance

    @pytest.mark.asyncio
    async def test_insert_into_tbl(self, event_loop):
        # 'POST', '/storage/table/{tbl_name}', data

        fake_storage_srvr = FakeFoglampStorageSrvr(loop=event_loop)
        await fake_storage_srvr.start()

        mockServiceRecord = MagicMock(ServiceRecord)
        mockServiceRecord._address = HOST
        mockServiceRecord._type = "Storage"
        mockServiceRecord._port = PORT
        mockServiceRecord._management_port = 2000

        sc = StorageClient(1, 2, mockServiceRecord)
        assert "{}:{}".format(HOST, PORT) == sc.base_url

        with pytest.raises(Exception) as excinfo:
            args = None, '{"k": "v"}'
            futures = [event_loop.run_in_executor(None, sc.insert_into_tbl, *args)]
            for response in await asyncio.gather(*futures):
                pass
        assert excinfo.type is ValueError
        assert "Table name is missing" in str(excinfo.value)

        with pytest.raises(Exception) as excinfo:
            args = "aTable", None
            futures = [event_loop.run_in_executor(None, sc.insert_into_tbl, *args)]
            for response in await asyncio.gather(*futures):
                pass
        assert excinfo.type is ValueError
        assert "Data to insert is missing" in str(excinfo.value)

        with pytest.raises(Exception) as excinfo:
            args = "aTable", {"k": "v"}
            futures = [event_loop.run_in_executor(None, sc.insert_into_tbl, *args)]
            for response in await asyncio.gather(*futures):
                pass
        assert excinfo.type is TypeError
        assert "Provided data to insert must be a valid JSON" in str(excinfo.value)

        args = "aTable", json.dumps({"k": "v"})
        futures = [event_loop.run_in_executor(None, sc.insert_into_tbl, *args)]
        for response in await asyncio.gather(*futures):
            assert {"k": "v"} == response["called"]

        with pytest.raises(Exception) as excinfo:
            with patch.object(_LOGGER, "error") as log_e:
                with patch.object(_LOGGER, "info") as log_i:
                    args = "aTable", json.dumps({"bad_request": "v"})
                    futures = [event_loop.run_in_executor(None, sc.insert_into_tbl, *args)]
                    for response in await asyncio.gather(*futures):
                        pass
        log_i.assert_called_once_with("POST %s, with payload: %s", '/storage/table/aTable', '{"bad_request": "v"}')
        log_e.assert_called_once_with("Error code: %d, reason: %s", 400, 'bad data')
        assert excinfo.type is StorageServerError

        with pytest.raises(Exception) as excinfo:
            with patch.object(_LOGGER, "error") as log_e:
                with patch.object(_LOGGER, "info") as log_i:
                    args = "aTable", json.dumps({"internal_server_err": "v"})
                    futures = [event_loop.run_in_executor(None, sc.insert_into_tbl, *args)]
                    for response in await asyncio.gather(*futures):
                        pass
        log_i.assert_called_once_with("POST %s, with payload: %s", '/storage/table/aTable', '{"internal_server_err": "v"}')
        log_e.assert_called_once_with("Error code: %d, reason: %s", 500, 'something wrong')
        assert 500 == excinfo.value.code
        assert "something wrong" == excinfo.value.reason
        assert {"key": "value"} == excinfo.value.error
        assert excinfo.type is StorageServerError

        await fake_storage_srvr.stop()

    @pytest.mark.asyncio
    async def test_update_tbl(self, event_loop):
        # PUT, '/storage/table/{tbl_name}', data

        fake_storage_srvr = FakeFoglampStorageSrvr(loop=event_loop)
        await fake_storage_srvr.start()

        mockServiceRecord = MagicMock(ServiceRecord)
        mockServiceRecord._address = HOST
        mockServiceRecord._type = "Storage"
        mockServiceRecord._port = PORT
        mockServiceRecord._management_port = 2000

        sc = StorageClient(1, 2, mockServiceRecord)
        assert "{}:{}".format(HOST, PORT) == sc.base_url

        with pytest.raises(Exception) as excinfo:
            args = None, json.dumps({"k": "v"})
            futures = [event_loop.run_in_executor(None, sc.update_tbl, *args)]
            for response in await asyncio.gather(*futures):
                pass
        assert excinfo.type is ValueError
        assert "Table name is missing" in str(excinfo.value)

        with pytest.raises(Exception) as excinfo:
            args = "aTable", None
            futures = [event_loop.run_in_executor(None, sc.update_tbl, *args)]
            for response in await asyncio.gather(*futures):
                pass
        assert excinfo.type is ValueError
        assert "Data to update is missing" in str(excinfo.value)

        with pytest.raises(Exception) as excinfo:
            args = "aTable", {"k": "v"}
            futures = [event_loop.run_in_executor(None, sc.update_tbl, *args)]
            for response in await asyncio.gather(*futures):
                pass
        assert excinfo.type is TypeError
        assert "Provided data to update must be a valid JSON" in str(excinfo.value)

        args = "aTable", json.dumps({"k": "v"})
        futures = [event_loop.run_in_executor(None, sc.update_tbl, *args)]
        for response in await asyncio.gather(*futures):
            assert {"k": "v"} == response["called"]

        with pytest.raises(Exception) as excinfo:
            with patch.object(_LOGGER, "error") as log_e:
                with patch.object(_LOGGER, "info") as log_i:
                    args = "aTable", json.dumps({"bad_request": "v"})
                    futures = [event_loop.run_in_executor(None, sc.update_tbl, *args)]
                    for response in await asyncio.gather(*futures):
                        pass
        log_i.assert_called_once_with("PUT %s, with payload: %s", '/storage/table/aTable', '{"bad_request": "v"}')
        log_e.assert_called_once_with("Client error code: %d, reason: %s", 400, 'bad data')

        assert excinfo.type is BadRequest

        with pytest.raises(Exception) as excinfo:
            with patch.object(_LOGGER, "error") as log_e:
                with patch.object(_LOGGER, "info") as log_i:
                    args = "aTable", json.dumps({"internal_server_err": "v"})
                    futures = [event_loop.run_in_executor(None, sc.update_tbl, *args)]
                    for response in await asyncio.gather(*futures):
                        pass
        log_i.assert_called_once_with("PUT %s, with payload: %s", '/storage/table/aTable',
                                      '{"internal_server_err": "v"}')
        log_e.assert_called_once_with("Server error code: %d, reason: %s", 500, 'something wrong')
        assert excinfo.type is StorageServerInternalError

        await fake_storage_srvr.stop()

    @pytest.mark.asyncio
    async def test_delete_from_tbl(self, event_loop):
        # 'DELETE', '/storage/table/{tbl_name}', condition (optional)

        fake_storage_srvr = FakeFoglampStorageSrvr(loop=event_loop)
        await fake_storage_srvr.start()

        mockServiceRecord = MagicMock(ServiceRecord)
        mockServiceRecord._address = HOST
        mockServiceRecord._type = "Storage"
        mockServiceRecord._port = PORT
        mockServiceRecord._management_port = 2000

        sc = StorageClient(1, 2, mockServiceRecord)
        assert "{}:{}".format(HOST, PORT) == sc.base_url

        with pytest.raises(Exception) as excinfo:
            futures = [event_loop.run_in_executor(None, sc.delete_from_tbl, None)]
            for response in await asyncio.gather(*futures):
                pass
        assert excinfo.type is ValueError
        assert "Table name is missing" in str(excinfo.value)

        args = "aTable", None  # delete without condition is allowed
        futures = [event_loop.run_in_executor(None, sc.delete_from_tbl, *args)]
        for response in await asyncio.gather(*futures):
            assert 1 == response["called"]

        with pytest.raises(Exception) as excinfo:
            args = "aTable", {"condition": "v"}
            futures = [event_loop.run_in_executor(None, sc.delete_from_tbl, *args)]
            for response in await asyncio.gather(*futures):
                pass
        assert excinfo.type is TypeError
        assert "condition payload must be a valid JSON" in str(excinfo.value)

        args = "aTable", json.dumps({"condition": "v"})
        futures = [event_loop.run_in_executor(None, sc.delete_from_tbl, *args)]
        for response in await asyncio.gather(*futures):
            assert {"condition": "v"} == response["called"]

        with pytest.raises(Exception) as excinfo:
            with patch.object(_LOGGER, "error") as log_e:
                with patch.object(_LOGGER, "info") as log_i:
                    args = "aTable", json.dumps({"bad_request": "v"})
                    futures = [event_loop.run_in_executor(None, sc.delete_from_tbl, *args)]
                    for response in await asyncio.gather(*futures):
                        pass
        log_i.assert_called_once_with("DELETE %s, with payload: %s", '/storage/table/aTable', '{"bad_request": "v"}')
        log_e.assert_called_once_with("Client error code: %d, reason: %s", 400, 'bad data')
        assert excinfo.type is BadRequest

        with pytest.raises(Exception) as excinfo:
            with patch.object(_LOGGER, "error") as log_e:
                with patch.object(_LOGGER, "info") as log_i:
                    args = "aTable", json.dumps({"internal_server_err": "v"})
                    futures = [event_loop.run_in_executor(None, sc.delete_from_tbl, *args)]
                    for response in await asyncio.gather(*futures):
                        pass
        log_i.assert_called_once_with("DELETE %s, with payload: %s", '/storage/table/aTable',
                                      '{"internal_server_err": "v"}')
        log_e.assert_called_once_with("Server error code: %d, reason: %s", 500, 'something wrong')
        assert excinfo.type is StorageServerInternalError

        await fake_storage_srvr.stop()

    @pytest.mark.asyncio
    async def test_query_tbl(self, event_loop):
        # 'GET', '/storage/table/{tbl_name}', *allows query params

        fake_storage_srvr = FakeFoglampStorageSrvr(loop=event_loop)
        await fake_storage_srvr.start()

        mockServiceRecord = MagicMock(ServiceRecord)
        mockServiceRecord._address = HOST
        mockServiceRecord._type = "Storage"
        mockServiceRecord._port = PORT
        mockServiceRecord._management_port = 2000

        sc = StorageClient(1, 2, mockServiceRecord)
        assert "{}:{}".format(HOST, PORT) == sc.base_url

        with pytest.raises(Exception) as excinfo:
            futures = [event_loop.run_in_executor(None, sc.query_tbl, None)]
            for response in await asyncio.gather(*futures):
                pass
        assert excinfo.type is ValueError
        assert "Table name is missing" in str(excinfo.value)

        args = "aTable", None  # query_tbl without query param is == SELECT *
        futures = [event_loop.run_in_executor(None, sc.query_tbl, *args)]
        for response in await asyncio.gather(*futures):
            assert 1 == response["called"]

        args = "aTable", 'foo=v1&bar=v2'
        futures = [event_loop.run_in_executor(None, sc.query_tbl, *args)]
        for response in await asyncio.gather(*futures):
            assert 'foo passed' == response["called"]

        with pytest.raises(Exception) as excinfo:
            with patch.object(_LOGGER, "error") as log_e:
                with patch.object(_LOGGER, "info") as log_i:
                    args = "aTable", 'bad_foo=1'
                    futures = [event_loop.run_in_executor(None, sc.query_tbl, *args)]
                    for response in await asyncio.gather(*futures):
                        pass
        log_i.assert_called_once_with("GET %s", '/storage/table/aTable?bad_foo=1')
        log_e.assert_called_once_with("Client error code: %d, reason: %s", 400, 'bad data')

        assert excinfo.type is BadRequest

        with pytest.raises(Exception) as excinfo:
            with patch.object(_LOGGER, "error") as log_e:
                with patch.object(_LOGGER, "info") as log_i:
                    args = "aTable", 'internal_server_err_foo=1'
                    futures = [event_loop.run_in_executor(None, sc.query_tbl, *args)]
                    for response in await asyncio.gather(*futures):
                        pass
        log_i.assert_called_once_with("GET %s", '/storage/table/aTable?internal_server_err_foo=1')
        log_e.assert_called_once_with("Server error code: %d, reason: %s", 500, 'something wrong')

        assert excinfo.type is StorageServerInternalError

        await fake_storage_srvr.stop()

    @pytest.mark.asyncio
    async def test_query_tbl_with_payload(self, event_loop):
        # 'PUT', '/storage/table/{tbl_name}/query', query_payload

        fake_storage_srvr = FakeFoglampStorageSrvr(loop=event_loop)
        await fake_storage_srvr.start()

        mockServiceRecord = MagicMock(ServiceRecord)
        mockServiceRecord._address = HOST
        mockServiceRecord._type = "Storage"
        mockServiceRecord._port = PORT
        mockServiceRecord._management_port = 2000

        sc = StorageClient(1, 2, mockServiceRecord)
        assert "{}:{}".format(HOST, PORT) == sc.base_url

        with pytest.raises(Exception) as excinfo:
            args = None, json.dumps({"k": "v"})
            futures = [event_loop.run_in_executor(None, sc.query_tbl_with_payload, *args)]
            for response in await asyncio.gather(*futures):
                pass
        assert excinfo.type is ValueError
        assert "Table name is missing" in str(excinfo.value)

        with pytest.raises(Exception) as excinfo:
            args = "aTable", None
            futures = [event_loop.run_in_executor(None, sc.query_tbl_with_payload, *args)]
            for response in await asyncio.gather(*futures):
                pass
        assert excinfo.type is ValueError
        assert "Query payload is missing" in str(excinfo.value)

        with pytest.raises(Exception) as excinfo:
            args = "aTable", {"k": "v"}
            futures = [event_loop.run_in_executor(None, sc.query_tbl_with_payload, *args)]
            for response in await asyncio.gather(*futures):
                pass
        assert excinfo.type is TypeError
        assert "Query payload must be a valid JSON" in str(excinfo.value)

        args = "aTable", json.dumps({"k": "v"})
        futures = [event_loop.run_in_executor(None, sc.query_tbl_with_payload, *args)]
        for response in await asyncio.gather(*futures):
            assert {"k": "v"} == response["called"]

        with pytest.raises(Exception) as excinfo:
            with patch.object(_LOGGER, "error") as log_e:
                with patch.object(_LOGGER, "info") as log_i:
                    args = "aTable", json.dumps({"bad_request": "v"})
                    futures = [event_loop.run_in_executor(None, sc.query_tbl_with_payload, *args)]
                    for response in await asyncio.gather(*futures):
                        pass
        log_i.assert_called_once_with("PUT %s, with query payload: %s", '/storage/table/aTable/query',
                                      '{"bad_request": "v"}')
        log_e.assert_called_once_with("Client error code: %d, reason: %s", 400, 'bad data')
        assert excinfo.type is BadRequest

        with pytest.raises(Exception) as excinfo:
            with patch.object(_LOGGER, "error") as log_e:
                with patch.object(_LOGGER, "info") as log_i:
                    args = "aTable", json.dumps({"internal_server_err": "v"})
                    futures = [event_loop.run_in_executor(None, sc.query_tbl_with_payload, *args)]
                    for response in await asyncio.gather(*futures):
                        pass
        log_i.assert_called_once_with("PUT %s, with query payload: %s", '/storage/table/aTable/query',
                                      '{"internal_server_err": "v"}')
        log_e.assert_called_once_with("Server error code: %d, reason: %s", 500, 'something wrong')
        assert excinfo.type is StorageServerInternalError

        await fake_storage_srvr.stop()


@pytest.allure.feature("unit")
@pytest.allure.story("common", "storage_client")
class TestReadingsStorageClient:

    def test_init(self):
        mockServiceRecord = MagicMock(ServiceRecord)
        mockServiceRecord._address = HOST
        mockServiceRecord._type = "Storage"
        mockServiceRecord._port = PORT
        mockServiceRecord._management_port = 2000

        rsc = ReadingsStorageClient(1, 2, mockServiceRecord)
        assert "{}:{}".format(HOST, PORT) == rsc.base_url

    @pytest.mark.asyncio
    async def test_append(self, event_loop):
        # 'POST', '/storage/reading', readings

        fake_storage_srvr = FakeFoglampStorageSrvr(loop=event_loop)
        await fake_storage_srvr.start()

        mockServiceRecord = MagicMock(ServiceRecord)
        mockServiceRecord._address = HOST
        mockServiceRecord._type = "Storage"
        mockServiceRecord._port = PORT
        mockServiceRecord._management_port = 2000

        rsc = ReadingsStorageClient(1, 2, mockServiceRecord)
        assert "{}:{}".format(HOST, PORT) == rsc.base_url

        with pytest.raises(Exception) as excinfo:
            futures = [event_loop.run_in_executor(None, rsc.append, None)]
            for response in await asyncio.gather(*futures):
                pass
        assert excinfo.type is ValueError
        assert "Readings payload is missing" in str(excinfo.value)

        with pytest.raises(Exception) as excinfo:
            futures = [event_loop.run_in_executor(None, rsc.append, "blah")]
            for response in await asyncio.gather(*futures):
                pass
        assert excinfo.type is TypeError
        assert "Readings payload must be a valid JSON" in str(excinfo.value)

        with pytest.raises(Exception) as excinfo:
            with patch.object(_LOGGER, "error") as log_e:
                readings_bad_payload = json.dumps({"Xreadings": []})
                futures = [event_loop.run_in_executor(None, rsc.append, readings_bad_payload)]
                for response in await asyncio.gather(*futures):
                    pass
        log_e.assert_called_once_with("POST url %s with payload: %s, Client error code: %d | reason: %s",
                                      '/storage/reading', '{"Xreadings": []}', 400, 'bad data')
        assert excinfo.type is BadRequest

        with pytest.raises(Exception) as excinfo:
            with patch.object(_LOGGER, "error") as log_e:
                r = '{"readings": [], "internal_server_err": 1}'
                futures = [event_loop.run_in_executor(None, rsc.append, r)]
                for response in await asyncio.gather(*futures):
                    pass
        log_e.assert_called_once_with("POST url %s with payload: %s, Server error code: %d | reason: %s",
                                      '/storage/reading', '{"readings": [], "internal_server_err": 1}',
                                      500, 'something wrong')
        assert excinfo.type is StorageServerInternalError

        readings = json.dumps({"readings": []})
        futures = [event_loop.run_in_executor(None, rsc.append, readings)]
        for response in await asyncio.gather(*futures):
            assert {'readings': []} == response['appended']

        await fake_storage_srvr.stop()

    @pytest.mark.asyncio
    async def test_fetch(self, event_loop):
        # GET, '/storage/reading?id={}&count={}'

        fake_storage_srvr = FakeFoglampStorageSrvr(loop=event_loop)
        await fake_storage_srvr.start()

        mockServiceRecord = MagicMock(ServiceRecord)
        mockServiceRecord._address = HOST
        mockServiceRecord._type = "Storage"
        mockServiceRecord._port = PORT
        mockServiceRecord._management_port = 2000

        rsc = ReadingsStorageClient(1, 2, mockServiceRecord)
        assert "{}:{}".format(HOST, PORT) == rsc.base_url

        with pytest.raises(Exception) as excinfo:
            args = None, 3
            futures = [event_loop.run_in_executor(None, rsc.fetch, *args)]
            for response in await asyncio.gather( * futures):
                pass
        assert excinfo.type is ValueError
        assert "first reading id to retrieve the readings block is required" in str(excinfo.value)

        with pytest.raises(Exception) as excinfo:
            args = 2, None
            futures = [event_loop.run_in_executor(None, rsc.fetch, *args)]
            for response in await asyncio.gather(*futures):
                pass
        assert excinfo.type is ValueError
        assert "count is required to retrieve the readings block" in str(excinfo.value)

        with pytest.raises(Exception) as excinfo:
            args = 2, "1s"
            futures = [event_loop.run_in_executor(None, rsc.fetch, *args)]
            for response in await asyncio.gather(*futures):
                pass
        assert excinfo.type is ValueError
        assert "invalid literal for int() with base 10" in str(excinfo.value)

        with pytest.raises(Exception) as excinfo:
            with patch.object(_LOGGER, "error") as log_e:
                args = "bad_data", 3
                futures = [event_loop.run_in_executor(None, rsc.fetch, *args)]
                for response in await asyncio.gather(*futures):
                    pass
        log_e.assert_called_once_with('GET url: %s, Client error code: %d | reason: %s',
                                      '/storage/reading?id=bad_data&count=3', 400, 'bad data')
        assert excinfo.type is BadRequest

        with pytest.raises(Exception) as excinfo:
            with patch.object(_LOGGER, "error") as log_e:
                args = "internal_server_err", 3
                futures = [event_loop.run_in_executor(None, rsc.fetch, *args)]
                for response in await asyncio.gather(*futures):
                    pass
        log_e.assert_called_once_with('GET url: %s, Server error code: %d | reason: %s',
                                      '/storage/reading?id=internal_server_err&count=3', 500, 'something wrong')
        assert excinfo.type is StorageServerInternalError

        args = 2, 3
        futures = [event_loop.run_in_executor(None, rsc.fetch, *args)]
        for response in await asyncio.gather(*futures):
            assert {'readings': [], 'start': '2', 'count': '3'} == response

        await fake_storage_srvr.stop()

    @pytest.mark.asyncio
    async def test_query(self, event_loop):
        # 'PUT', '/storage/reading/query' query_payload

        fake_storage_srvr = FakeFoglampStorageSrvr(loop=event_loop)
        await fake_storage_srvr.start()

        mockServiceRecord = MagicMock(ServiceRecord)
        mockServiceRecord._address = HOST
        mockServiceRecord._type = "Storage"
        mockServiceRecord._port = PORT
        mockServiceRecord._management_port = 2000

        rsc = ReadingsStorageClient(1, 2, mockServiceRecord)
        assert "{}:{}".format(HOST, PORT) == rsc.base_url

        with pytest.raises(Exception) as excinfo:
            futures = [event_loop.run_in_executor(None, rsc.query, None)]
            for response in await asyncio.gather(*futures):
                pass
        assert excinfo.type is ValueError
        assert "Query payload is missing" in str(excinfo.value)

        with pytest.raises(Exception) as excinfo:
            futures = [event_loop.run_in_executor(None, rsc.query, "blah")]
            for response in await asyncio.gather(*futures):
                pass
        assert excinfo.type is TypeError
        assert "Query payload must be a valid JSON" in str(excinfo.value)

        futures = [event_loop.run_in_executor(None, rsc.query, json.dumps({"k": "v"}))]
        for response in await asyncio.gather(*futures):
            assert {"k": "v"} == response["called"]

        with pytest.raises(Exception) as excinfo:
            with patch.object(_LOGGER, "error") as log_e:
                futures = [event_loop.run_in_executor(None, rsc.query, json.dumps({"bad_request": "v"}))]
                for response in await asyncio.gather(*futures):
                    pass
        log_e.assert_called_once_with("PUT url %s with query payload: %s, Client error code: %d | %s",
                                      '/storage/reading/query', '{"bad_request": "v"}', 400, 'bad data')
        assert excinfo.type is BadRequest

        with pytest.raises(Exception) as excinfo:
            with patch.object(_LOGGER, "error") as log_e:
                futures = [event_loop.run_in_executor(None, rsc.query, json.dumps({"internal_server_err": "v"}))]
                for response in await asyncio.gather(*futures):
                    pass
        log_e.assert_called_once_with("PUT url %s with query payload: %s, Server error code: %d | %s",
                                      '/storage/reading/query', '{"internal_server_err": "v"}', 500, 'something wrong')
        assert excinfo.type is StorageServerInternalError

        await fake_storage_srvr.stop()

    @pytest.mark.asyncio
    async def test_purge(self, event_loop):
        # 'PUT', url=put_url, /storage/reading/purge?age=&sent=&flags

        fake_storage_srvr = FakeFoglampStorageSrvr(loop=event_loop)
        await fake_storage_srvr.start()

        mockServiceRecord = MagicMock(ServiceRecord)
        mockServiceRecord._address = HOST
        mockServiceRecord._type = "Storage"
        mockServiceRecord._port = PORT
        mockServiceRecord._management_port = 2000

        rsc = ReadingsStorageClient(1, 2, mockServiceRecord)
        assert "{}:{}".format(HOST, PORT) == rsc.base_url

        with pytest.raises(Exception) as excinfo:
            kwargs = dict(flag='blah', age=1, sent_id=0, size=None)
            func = partial(rsc.purge, **kwargs)
            futures = [event_loop.run_in_executor(None, func)]
            for response in await asyncio.gather(*futures):
                pass
        assert excinfo.type is InvalidReadingsPurgeFlagParameters
        assert "Purge flag valid options are retain or purge only" in str(excinfo.value)

        with pytest.raises(Exception) as excinfo:
            kwargs = dict(age=1, sent_id=0, size=1, flag='retain')
            func = partial(rsc.purge, **kwargs)
            futures = [event_loop.run_in_executor(None, func)]
            for response in await asyncio.gather(*futures):
                pass
        assert excinfo.type is PurgeOnlyOneOfAgeAndSize
        assert "Purge must specify only one of age or size" in str(excinfo.value)

        with pytest.raises(Exception) as excinfo:
            kwargs = dict(age=None, sent_id=0, size=None, flag='retain')
            func = partial(rsc.purge, **kwargs)
            futures = [event_loop.run_in_executor(None, func)]
            for response in await asyncio.gather(*futures):
                pass
        assert excinfo.type is PurgeOneOfAgeAndSize
        assert "Purge must specify one of age or size" in str(excinfo.value)

        with pytest.raises(Exception) as excinfo:
            kwargs = dict(age=0, sent_id=0, size=0, flag='retain')
            func = partial(rsc.purge, **kwargs)
            futures = [event_loop.run_in_executor(None, func)]
            for response in await asyncio.gather(*futures):
                pass
        assert excinfo.type is PurgeOneOfAgeAndSize
        assert "Purge must specify one of age or size" in str(excinfo.value)

        # age int
        with pytest.raises(Exception) as excinfo:
            kwargs = dict(age="1b", sent_id=0, size=None, flag='retain')
            func = partial(rsc.purge, **kwargs)
            futures = [event_loop.run_in_executor(None, func)]
            for response in await asyncio.gather(*futures):
                pass
        assert excinfo.type is ValueError
        assert "invalid literal for int() with base 10" in str(excinfo.value)

        # size int
        with pytest.raises(Exception) as excinfo:
            kwargs = dict(age=None, sent_id=0, size="1b", flag='retain')
            func = partial(rsc.purge, **kwargs)
            futures = [event_loop.run_in_executor(None, func)]
            for response in await asyncio.gather(*futures):
                pass
        assert excinfo.type is ValueError
        assert "invalid literal for int() with base 10" in str(excinfo.value)

        # sent_id int
        with pytest.raises(Exception) as excinfo:
            kwargs = dict(age=1, sent_id="1b", size=None, flag='retain')
            func = partial(rsc.purge, **kwargs)
            futures = [event_loop.run_in_executor(None, func)]
            for response in await asyncio.gather(*futures):
                pass
        assert excinfo.type is ValueError
        assert "invalid literal for int() with base 10" in str(excinfo.value)

        with pytest.raises(Exception) as excinfo:
            with patch.object(_LOGGER, "error") as log_e:
                kwargs = dict(age=-1, sent_id=1, size=None, flag='retain')
                func = partial(rsc.purge, **kwargs)
                futures = [event_loop.run_in_executor(None, func)]
                for response in await asyncio.gather(*futures):
                    pass
        log_e.assert_called_once_with('PUT url %s, Client error code: %d | %s',
                                      '/storage/reading/purge?age=-1&sent=1&flags=retain', 400, 'age should not be less than 0')
        assert excinfo.type is BadRequest

        with pytest.raises(Exception) as excinfo:
            with patch.object(_LOGGER, "error") as log_e:
                kwargs = dict(age=None, sent_id=1, size=4294967296, flag='retain')
                func = partial(rsc.purge, **kwargs)
                futures = [event_loop.run_in_executor(None, func)]
                for response in await asyncio.gather(*futures):
                    pass
        log_e.assert_called_once_with('PUT url %s, Client error code: %d | %s',
                                      '/storage/reading/purge?size=4294967296&sent=1&flags=retain', 500, 'unsigned int range')
        assert excinfo.type is StorageServerInternalError

        kwargs = dict(age=1, sent_id=1, size=0, flag='retain')
        func = partial(rsc.purge, **kwargs)
        futures = [event_loop.run_in_executor(None, func)]
        for response in await asyncio.gather(*futures):
            assert 1 == response["called"]

        kwargs = dict(age=0, sent_id=1, size=1, flag='retain')
        func = partial(rsc.purge, **kwargs)
        futures = [event_loop.run_in_executor(None, func)]
        for response in await asyncio.gather(*futures):
            assert 1 == response["called"]

        kwargs = dict(age=1, sent_id=1, size=None, flag='retain')
        func = partial(rsc.purge, **kwargs)
        futures = [event_loop.run_in_executor(None, func)]
        for response in await asyncio.gather(*futures):
            assert 1 == response["called"]

        kwargs = dict(age=None, sent_id=1, size=1, flag='retain')
        func = partial(rsc.purge, **kwargs)
        futures = [event_loop.run_in_executor(None, func)]
        for response in await asyncio.gather(*futures):
            assert 1 == response["called"]

        await fake_storage_srvr.stop()

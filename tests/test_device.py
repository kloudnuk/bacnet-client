
# import pytest
import json
import configparser
from src.bacnet_client.Device import BacnetDevice

config = configparser.ConfigParser()


def test_device_eq():
    global config
    config.read('tests.ini')
    apex_graph = json.loads(config.get("devices", "apex-graph"))
    apex1: BacnetDevice = BacnetDevice(apex_graph['id'],
                                       apex_graph['address'],
                                       apex_graph['properties'],
                                       False)
    apex2: BacnetDevice = BacnetDevice(apex_graph['id'],
                                       apex_graph['address'],
                                       apex_graph['properties'],
                                       False)
    assert apex1 == apex2


def test_device_ne():
    global config
    config.read('tests.ini')
    apex_graph = json.loads(config.get("devices", "apex-graph"))
    bos_graph = json.loads(config.get("devices", "bos-graph"))
    apex: BacnetDevice = BacnetDevice(apex_graph['id'],
                                      apex_graph['address'],
                                      apex_graph['properties'],
                                      False)
    bos: BacnetDevice = BacnetDevice(bos_graph['id'],
                                     bos_graph['address'],
                                     bos_graph['properties'],
                                     False)
    assert apex != bos


def test_device_lt():
    global config
    config.read('tests.ini')
    apex_graph = json.loads(config.get("devices", "apex-graph"))
    bos_graph = json.loads(config.get("devices", "bos-graph"))
    apex: BacnetDevice = BacnetDevice(apex_graph['id'],
                                      apex_graph['address'],
                                      apex_graph['properties'],
                                      False)
    bos: BacnetDevice = BacnetDevice(bos_graph['id'],
                                     bos_graph['address'],
                                     bos_graph['properties'],
                                     False)
    assert bos < apex


def test_device_gt():
    global config
    config.read('tests.ini')
    ecy_top_graph = json.loads(config.get("devices", "ecy-top-graph"))
    bos_graph = json.loads(config.get("devices", "bos-graph"))
    ecy_top: BacnetDevice = BacnetDevice(ecy_top_graph['id'],
                                         ecy_top_graph['address'],
                                         ecy_top_graph['properties'],
                                         False)
    bos: BacnetDevice = BacnetDevice(bos_graph['id'],
                                     bos_graph['address'],
                                     bos_graph['properties'],
                                     False)
    assert ecy_top > bos


def test_device_merge():
    global config
    config.read('tests.ini')
    ecy_graph_old = json.loads(config.get("devices", "ecy-top-graph"))
    ecy_graph_new = json.loads(config.get("devices", "ecy-top-graph"))

    ecy_graph_new["properties"]["location"]["value"] = "test-bench"

    ecy_old = BacnetDevice(ecy_graph_old['id'],
                           ecy_graph_old['address'],
                           ecy_graph_old['properties'],
                           False)
    ecy_new = BacnetDevice(ecy_graph_new['id'],
                           ecy_graph_new['address'],
                           ecy_graph_new['properties'],
                           False)

    # verify state for old and new objects before merging
    assert ecy_old.obj["properties"]["location"]["value"] == "top rack"
    assert ecy_new.obj["properties"]["location"]["value"] == "test-bench"

    ecy_old + ecy_new

    # verify old vs new object for equality and merged state
    assert ecy_old.obj["properties"]["location"]["value"] == "test-bench"

import sys
sys.path.insert(0, '../')

from rapidctl.bootstrap.client import CtlClient

def test_container_version():

    client = CtlClient()

    client.container_repo = "example.com/repo/container"
    client.baseline_version = "test"

    print("Container version: %s" % client.container_version)
    assert client.container_version == "example.com/repo/container:test"



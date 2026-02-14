import os
import platform
import rapidctl.connectors

def connect():

    connectors = {
            "Darwin" =  rapidctl.connectors.osx
        }

    return connectors[platform.system()].podman()

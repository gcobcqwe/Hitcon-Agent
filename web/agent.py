# -*- coding: utf-8 -*-
# Copyright (c) 2020 HITCON Agent Contributors
# See CONTRIBUTORS file for the list of HITCON Agent Contributors

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import logging
import grpc
import kofserver_pb2, kofserver_pb2_grpc
from config import Config

class Agent:
    def __init__(self):
        # TODO: Check connection health
        channel = grpc.insecure_channel('%s:%d'%(Config.conf()['agentHost'], Config.conf()['agentPort']))
        logging.info("Agent Connecting...")
        f = grpc.channel_ready_future(channel)
        try:
            f.result(timeout=Config.conf()['agentConnectTimeout'])
            logging.info("Agent Connected")
        except Exception:
            logging.info("Agent failed to connect.")
            return None

        # The gRPC channel
        self.channel = channel
        # The kofserver gRPC stub
        self.stub = kofserver_pb2_grpc.KOFServerStub(self.channel)

    def query_game(self):
        return [
            {"player_name": "jim", "port_uptime": 5, "port_score": 60, "pid_uptime": 10, "pid_score": 200, "total_score": 260},
            {"player_name": "kevin", "port_uptime": 0, "port_score": 0, "pid_uptime": 10, "pid_score": 200, "total_score": 200},
            {"player_name": "kate", "port_uptime": 0, "port_score": 0, "pid_uptime": 0, "pid_score": 0, "total_score": 0}]
        # response = self.stub.QueryGame(kofserver_pb2.QueryGame())
        # if response.error == kofserver_pb2.ErrorCode.ERROR_NONE:
        #     print("query_game successful")
        # else:
        #     print("query_game failed: %s"%(str(response.error),))

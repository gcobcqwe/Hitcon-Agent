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

# This file host the Game class, which contains the primary logic for a game.

import logging
import yaml
import os

import kofserver_pb2, kofserver_pb2_grpc
from kofserver_pb2 import GameState
from vm_manager import VMManager, VM
from config import Config
from guest_agent import GuestAgent

class Game:
    def __init__(self, executor, vmManager, gameName, scenarioName):
        # executor is a concurrent.futures.Executor class that allows us to
        # run stuff.
        self.executor = executor

        # Load the scenario
        self.scenarioName = scenarioName
        self.scenario = Game.LoadScenario(scenarioName)

        # Start the Game Task, which runs anything in the game that need to
        # be done repeatedly, such as scoring the user.
        self.gameTaskExit = False
        self.gameTask = executor.submit(self.GameFunc, self)

        # Create the guest agent proxy.
        self.agent = GuestAgent(self.executor, self.GetIP())

        # The state that the game is in.
        self.state = GameState.GAME_CREATED

        # Create the VM that we'll be using for this game.
        self.vmManager = vmManager
        self.vm = vmManager.CreateVM(self.scenario['vmPath'])
    
    def GameFunc(self):
        # This method runs for the entire time life cycle of the game.
        logging.info("GameFunc for %s running"%(self.gameName,))
        while True:
            if self.gameTaskExit:
                # Time to go
                return True
            
            if self.state == GameState.GAME_CREATED:
                # Nothing to do
                time.sleep(0.5)
                continue
            
            if self.state == GameState.GAME_STARTING:
                # Wait for the guest agent to be connected.
                if self.agent.EnsureConnection():
                    # It's connected, so we can move onto the started state
                    self.state = GameState.GAME_RUNNING
                    continue
                # If agent is responsive, then we don't have to check the VM.
                # Wait and try again.
                time.sleep(0.5)
                continue
            
            if self.state == GameState.GAME_RUNNING:
                # TODO: Gotta score the users.
                pass
            
            if self.state == GameState.GAME_REBOOTING:
                raise Exception("Reboot state not implemented yet")
                # TODO
            
            if self.state == GameState.GAME_DESTROYING:
                # Wait for the VM to get to shutdown state.
                if self.vm.GetState() == VM.VMState.DESTROYED:
                    # It's down, so let's 
                    # TODO
                    pass0
                    
    
    def StopGameFunc(self):
        # Note: Should never be called from GameFunc, or it'll deadlock.
        self.gameTaskExit = True
        # Wait for it to end by asking for its result.
        self.gameTask.result()

    def GetIP(self):
        return self.scenario['ip']

    def RegisterUser(self, username):
        if username in self.users:
            return kofserver_pb2.ERROR_USER_ALREADY_EXISTS
        
        self.users[username] = {}
        
        # Generate a port for the user.
        for i in range(1000000):
            # Not a while True so if something went wrong we know.
            
            port = random.randint(Config.conf()['portStart'], Config.conf()['portEnd'])
            if port in self.portToUser:
                port = -1
                continue
            break
        if port == -1:
            # This shouldn't happen, so it's an Exception not a return code.
            raise Exception("No valid port available")
        self.Users[username]["port"] = port
        self.Users[username]["pid"] = -1 # Not available yet.

        return kofserver_pb2.ERROR_NONE
    
    @staticmethod
    def LoadScenario(scenarioName):
        scenarioDir = Config.conf()['scenarioDir']
        scenarioPath = os.path.join(scenarioDir, scenarioName)
        ymlPath = os.path.join(scenarioPath, "scenario.yml")
        try:
            with open(ymlPath) as f:
                result = yaml.load(f, Loader=yaml.FullLoader)
        except Exception:
            logging.exception("Failed to open scenario.yml file %s"%ymlPath)
        return result

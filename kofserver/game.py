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
import random
import traceback
import time

import kofserver_pb2, kofserver_pb2_grpc
from kofserver_pb2 import GameState
from kofserver_pb2 import ErrorCode as KOFErrorCode
from guest_agent_pb2 import ErrorCode as GuestErrorCode
from vm_manager import VMManager, VM
from config import Config
from guest_agent import GuestAgent
from scorer import Scorer

class Game:
    def __init__(self, executor, vmManager, scoreboard, scanner, gameName, scenarioName):
        self.gameName = gameName
        
        # executor is a concurrent.futures.Executor class that allows us to
        # run stuff.
        self.executor = executor
        
        # Store the scoreboard and scanner for future use.
        self.scoreboard = scoreboard
        self.scanner = scanner
        
        # Load the scenario
        self.scenarioName = scenarioName
        self.scenario = Game.LoadScenario(scenarioName)

        # The state that the game is in, needs to happen before starting gameTask.
        self.state = GameState.GAME_CREATED

        # Start the Game Task, which runs anything in the game that need to
        # be done repeatedly, such as scoring the user.
        self.gameTaskExit = False
        self.gameTask = executor.submit(Game._GameFunc, self)

        # Create the guest agent proxy.
        self.agent = GuestAgent(self.executor, self.GetIP())

        # Init the player variables.
        self.users = {}
        self.portToUser = {}
        self.pidToUser = {}

        # Create the VM that we'll be using for this game.
        self.vmManager = vmManager
        self.vm = vmManager.CreateVM(self.scenario['vmPath'])
        
        # Create the scorer for scoring the users.
        self.scorer = Scorer(self)
    
    # Start the game.
    def Start(self):
        # Set it to we are starting.
        self.state = GameState.GAME_STARTING1
        # GameFunc will handle the rest.
        # ie. Initialize the VM, waiting for guest agent... etc
        return KOFErrorCode.ERROR_NONE

    # Destroy the game.
    def Destroy(self):
        if self.state != GameState.GAME_RUNNING:
            logging.warn("Destroying game not in running state: %s %s"%(self.gameName, str(self.state)))
        self.state = GameState.GAME_DESTROYING1
        return KOFErrorCode.ERROR_NONE

    def PlayerIssueCmd(self, playerName, cmd):
        if self.state != GameState.GAME_RUNNING:
            logging.info("Player %s issued command when game %s is not running."%(playerName, self.gameName))
            return KOFErrorCode.ERROR_GAME_NOT_RUNNING
        if not self.scenario['allowCommand']:
            logging.info("Player %s tried to issue command when game %s doesn't allow."%(playerName, self.gameName))
            return KOFErrorCode.ERROR_GAME_NOT_ALLOW
        if playerName not in self.users:
            logging.info("Player %s not register id game %s."%(playerName, self.gameName))
            return KOFErrorCode.ERROR_USER_NOT_REGISTERED
        res = self.agent.RunCmd(cmd)
        if res.reply.error != GuestErrorCode.ERROR_NONE:
            logging.warning("Executing command '%s' failed due to agent problem %s."%(cmd, res.reply.error))
            return KOFErrorCode.ERROR_AGENT_PROBLEM
        self.SetPlayerPID(playerName, res.pid)
        return KOFErrorCode.ERROR_NONE

    def SetPlayerPID(self, playerName, pid):
        assert playerName in self.users
        self.users[playerName]['pid'] = pid
        self.pidToUser[pid] = playerName

    # Return the Game protobuf for this game.
    def GetGameProto(self):
        result = kofserver_pb2.Game(name=self.gameName, state=self.state)
        return result
    
    def _GameFunc(self):
        # We need to catch the exception because it doesn't showup until
        # very late, when .result() is called.
        try:
            self._GameFuncReal()
        except Exception:
            logging.exception("Exception in GameFunc")

    def _GameFuncReal(self):
        logging.info("GameFunc for %s running"%(self.gameName,))
        # This method runs for the entire time life cycle of the game.
        while True:
            if self.gameTaskExit:
                # Time to go
                return True
            
            if self.state == GameState.GAME_CREATED:
                # Nothing to do
                time.sleep(0.5)
                continue
            
            if self.state == GameState.GAME_STARTING1:
                if self.vm.GetState() == VM.VMState.CREATED:
                    # Init and start the VM
                    res = self.vm.Init()
                    if not res or self.vm.GetState() != VM.VMState.READY:
                        logging.error("Failed to init VM (%s) or invalid VM state after Init() (%s)"%(str(res), str(self.vm.GetState())))
                        self.state = GameState.GAME_ERROR
                        continue

                    res = self.vm.Boot()
                    if not res:
                        logging.error("Failed to boot VM")
                        self.state = GameState.GAME_ERROR
                        continue
                    
                    continue
                else:
                    # We've finished init and start VM step, so wait for it
                    # to be running.
                    if self.vm.GetState() == VM.VMState.RUNNING:
                        logging.info("VM for Game %s is running."%(self.gameName,))
                        self.state = GameState.GAME_STARTING2
                    # Wait some time?
                    time.sleep(0.5)
                
            if self.state == GameState.GAME_STARTING2:
                # Wait for the guest agent to be connected.
                if self.agent.EnsureConnection():
                    # It's connected, so we can move onto the started state
                    logging.info("Agent for Game %s is ready."%(self.gameName,))
                    self.state = GameState.GAME_RUNNING
                    self.scorer.NotifyGameStarted()
                    continue
                # If agent is responsive, then we don't have to check the VM.
                # Wait and try again.
                time.sleep(0.5)
                continue
            
            if self.state == GameState.GAME_RUNNING:
                playerScored = self.scorer.TryScorePlayers()
                if not playerScored:
                    # Don't stress it too much.
                    time.sleep(0.3)
            
            if self.state == GameState.GAME_REBOOTING:
                raise Exception("Reboot state not implemented yet")
                # TODO
            
            if self.state == GameState.GAME_DESTROYING:
                # Shutdown the VM and reset the guest agent.
                self.agent.ResetConnection()
                if self.vm.GetState() == VM.VMState.RUNNING:
                    result = self.vm.Shutdown()
                    if not result:
                        logging.error("Failed to shutdown VM")
                        self.state = GameState.GAME_ERROR
                        continue
                
                if self.vm.GetState() == VM.State.READY:
                    # Let's destroy it.
                    result = self.vm.Destroy()
                    if not result:
                        logging.error("Failed to destroy VM")
                        self.state = GameState.GAME_ERROR
                        continue
                    self.state = GameState.GAME_DESTROYED
                
                # Wait for the VM to get to shutdown state.
                if self.vm.GetState() == VM.VMState.DESTROYED:
                    # It's down, so let's 
                    # TODO
                    pass
                    
    
    def StopGameFunc(self):
        # Note: Should never be called from GameFunc, or it'll deadlock.
        self.gameTaskExit = True
        # Wait for it to end by asking for its result.
        self.gameTask.result()

    def GetIP(self):
        return self.scenario['ip']

    def RegisterPlayer(self, username):
        if username in self.users:
            return KOFErrorCode.ERROR_USER_ALREADY_EXISTS
        
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
        self.portToUser[port] = username
        self.users[username]["port"] = port
        self.users[username]["pid"] = -1 # Not available yet.
        self.users[username]["pidUp"] = False # User's pid up when we last check?
        self.users[username]["portUp"] = False # User's port up when we last check?

        return KOFErrorCode.ERROR_NONE
    
    def QueryPlayerInfo(self, playerName):
        if playerName != "":
            return [self.GetPlayerInfoProto(playerName),]
        # playerName == "", so we retrieve all the players.
        res = []
        for p in self.users:
            res.append(self.GetPlayerInfoProto(p))
        return res

    def GetPlayerInfoProto(self, playerName):
        if playerName not in self.users:
            raise Exception("Invalid player %s for GetPlayerInfoProto"%playerName)
        
        result = kofserver_pb2.PlayerInfo(playerName=playerName)
        result.port = udict["port"]
        result.pid = udict["pid"]
        result.portUp = udict["portUp"]
        result.pidUp = udict["pidUp"]
        return result

    def Shutdown(self):
        self.gameTaskExit = True
        # Wait for it to terminate
        self.gameTask.result()

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

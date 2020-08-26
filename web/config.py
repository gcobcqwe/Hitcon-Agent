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

import yaml

# For the real configuration file, see irc.yml

# Config is a singleton class that stores the irc configurations.
# It is in charge of loading config from irc.yml and
# allowing other code to access the config.
# Simply do Config.conf() to get configurations.
class Config:
  __instance = None

  @staticmethod
  def Init():
      # Create the config class and load the configs.
      # Should only be called once at startup.
      Config()

  @staticmethod
  def conf():
      if Config.__instance == None:
          raise Exception("Config not initialized")
      return Config.__instance.conf

  def __init__(self):
      if Config.__instance != None:
          raise Exception("Multiple Config instantiation")
      else:
          Config.__instance = self
      
      # Now load the config.
      with open('./web.yml') as f:
          self.conf = yaml.load(f, Loader=yaml.FullLoader)
import time
import threading
import serial


class Plugin:
  CONFIG=[
    {
      'name': 'device',
      'description': 'set to the device path (alternative to usbid)',
      'default': ''
    },
    {
      'name': 'usbid',
      'description': 'set to the usbid of the device (alternative to device)',
      'default': ''
    },
    {
      'name': 'baud',
      'description': 'baudrate for connection',
      'default': '9600'
    }
  ]
  @classmethod
  def pluginInfo(cls):
    """
    the description for the module
    @return: a dict with the content described below
            parts:
               * description (mandatory)
               * data: list of keys to be stored (optional)
                 * path - the key - see AVNApi.addData, all pathes starting with "gps." will be sent to the GUI
                 * description
    """
    return {
      'description': 'seatalk remote control',
      'config': cls.CONFIG,
      'data': [
      ]
    }

  def __init__(self,api):
    """
        initialize a plugins
        do any checks here and throw an exception on error
        do not yet start any threads!
        @param api: the api to communicate with avnav
        @type  api: AVNApi
    """
    self.api = api # type: AVNApi
    #we register an handler for API requests
    self.api.registerRequestHandler(self.handleApiRequest)
    self.lastReceived=0
    self.isConnected=False
    self.connection=None
    self.device=None
    self.baud=None
    self.isBusy=False
    self.condition=threading.Condition()
    if hasattr(self.api,'registerEditableParameters'):
      self.api.registerEditableParameters(self.CONFIG,self._changeConfig)
    if hasattr(self.api,'registerRestart'):
      self.api.registerRestart(self._apiRestart)
    self.changeSequence=0
    self.startSequence=0

  def _apiRestart(self):
    self.startSequence+=1
    self.changeSequence+=1

  def _changeConfig(self,newValues):
    self.api.saveConfigValues(newValues)
    self.changeSequence+=1

  def getConfigValue(self,name):
    defaults=self.pluginInfo()['config']
    for cf in defaults:
      if cf['name'] == name:
        return self.api.getConfigValue(name,cf.get('default'))
    return self.api.getConfigValue(name)

  def run(self):
    startSequence=self.startSequence
    while startSequence == self.startSequence:
      try:
        #only AvNav after 20210224
        self.api.deregisterUsbHandler()
      except:
        pass
      self.runInternal()

  def runInternal(self):
    """
    the run methodhttps://github.com/wellenvogel/esp32-nmea2000/blob/master/lib/exampletask/Readme.md
    this will be called after successfully instantiating an instance
    this method will be called in a separate Thread
    The example simply counts the number of NMEA records that are flowing through avnav
    and writes them to the store every 10 records
    @return:
    """
    changeSequence=self.changeSequence
    seq=0
    self.api.log("started")
    enabled=self.getConfigValue('enabled')
    if enabled is not None and enabled.lower()!='true':
      self.api.setStatus("INACTIVE", "disabled by config")
      return
    usbid=None
    try:
      self.baud=int(self.getConfigValue('baud'))
      self.device=self.getConfigValue('device')
      usbid=self.getConfigValue('usbid')
      if usbid == '':
        usbid=None
      if self.device == '':
        self.device=None
      if self.device is None and usbid is None:
        raise Exception("missing config value device or usbid")

      if self.device is not None and usbid is not None:
        raise Exception("only one of device or usbid can be set")
    except Exception as e:
      self.api.setStatus("ERROR", "config error %s "%str(e))
      while changeSequence == self.changeSequence:
        time.sleep(0.5)
      return
    if usbid is not None:
      self.api.registerUsbHandler(usbid,self.deviceConnected)
      self.api.setStatus("STARTED", "using usbid %s, baud=%d" % (usbid, self.baud))
    else:
      self.api.setStatus("STARTED","using device %s, baud=%d"%(self.device,self.baud))
    connectionHandler=threading.Thread(target=self.handleConnection, name='seatalk-remote-connection')
    connectionHandler.setDaemon(True)
    connectionHandler.start()
    while changeSequence == self.changeSequence:
      seq,data=self.api.fetchFromQueue(seq,10,filter="$RMB")
      if len(data) > 0:
        self.lastReceived=time.time()

  def handleConnection(self):
    changeSequence=self.changeSequence
    errorReported=False
    lastDevice=None
    while changeSequence == self.changeSequence:
      if self.device is not None:
        if self.device != lastDevice:
          self.api.setStatus("STARTED", "trying to connect to %s at %d" % (self.device, self.baud))
          lastDevice=self.device
        #on windows we would need an integer as device...
        try:
          pnum = int(self.device)
        except:
          pnum = self.device
        self.isConnected=False
        self.isBusy=False
        try:
          self.connection = serial.Serial(port=pnum, baudrate=self.baud, timeout=5)
          self.api.setStatus("NMEA","connected to %s at %d"%(self.device,self.baud))
          self.api.log("connected to %s at %d" % (self.device, self.baud))
          self.isConnected=True
          errorReported=False
          #continously read data to get an exception if disconnected
          while changeSequence == self.changeSequence:
            self.connection.readline(10)
        except Exception as e:
          if not errorReported:
            self.api.setStatus("ERROR","unable to connect/connection lost to %s: %s"%(self.device, str(e)))
            self.api.error("unable to connect/connection lost to %s: %s" % (self.device, str(e)))
            errorReported=True
          self.isConnected=False
          time.sleep(1)
      time.sleep(1)
    try:  
      self.connection.close()  
    except:
      pass
    self.connection=None

  def deviceConnected(self,device):
    if self.device == device:
      return
    try:
      if self.connection is not None:
        self.connection.close()
    except:
      pass
    self.connection=None
    self.api.log("device connected %s",device)
    self.device=device
  def sendCommand(self,val):
    #we avoid blocking multiple threads here
    canWrite=False
    self.condition.acquire()
    if not self.isBusy:
      self.isBusy=True
      canWrite=True
    self.condition.release()
    if not canWrite:
      raise Exception("busy")
    try:
      self.connection.write((val+"\n").encode('ascii'))
    except Exception as e:
      self.condition.acquire()
      self.isBusy=False
      self.condition.release()
      raise
    self.condition.acquire()
    self.isBusy = False
    self.condition.release()

  def handleApiRequest(self,url,handler,args):
    """
    handler for API requests send from the JS
    @param url: the url after the plugin base
    @param handler: the HTTP request handler
                    https://docs.python.org/2/library/basehttpserver.html#BaseHTTPServer.BaseHTTPRequestHandler
    @param args: dictionary of query arguments
    @return:
    """
    if url == 'status':
      now=time.time()
      hasRMB=False
      if (self.lastReceived + 5) >= now:
        hasRMB=True
      return {'status': 'OK',
              'hasRmb':hasRMB,
              'connected':self.isConnected,
              'device':self.device}
    if url[0:3] == 'key':
      #we simply use an url of /plugins/...setalk-remote/api/keyp1
      #this way we do not need to parse query param
      key=url[3:]
      KEYMAP={
        'p1':'+1',
        'm1':'-1',
        'p10':'+10',
        'm10':'-10',
        'A':'A',
        'S':'S'
      }
      keyval=KEYMAP.get(key)
      if keyval is None:
        return {'status':'invalid key'}
      if not self.isConnected:
        return {'status': 'not connected'}
      try:
        self.sendCommand(keyval)
        return {'status':'OK'}
      except Exception as e:
        return {'status':'Exception: %s'%str(e)}

    return {'status','unknown request'}

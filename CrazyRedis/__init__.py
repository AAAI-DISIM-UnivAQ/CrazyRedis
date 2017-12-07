
import sys
import time
from threading import Timer

import redis

from cflib.crazyflie import Crazyflie
from cflib.crazyflie.log import LogConfig
import cflib.crtp

class CrazyRedis:
    __host = None  # The default value is localhost
    __password = None
    __db = None  # This is the database we are using
    __port = None
    __inputChannel = None  # The channel we eventually want to listen to
    __outputChannel = None  # The channel we have to put outputs into
    __redis = None  # Redis object

    def __init__(self, host='127.0.0.1', password='', db=0, port=6379, inChannel='CrazyInCh', outChannel='CrazyOutCh'):
        assert isinstance(host, str)
        assert isinstance(password, str)
        assert isinstance(db, int)
        assert isinstance(port, int)
        assert isinstance(inChannel, str)
        assert isinstance(outChannel, str)
        self.__host = host
        self.__password = password
        self.__db = db
        self.__port = port
        self.__inputChannel = inChannel
        self.__outputChannel = outChannel

    def getHost(self):
        return self.__host

    def setHost(self, newHost):
        assert isinstance(newHost, str)
        self.__host = newHost

    def getPassword(self):
        return self.__password

    def setPassword(self, newPassword):
        assert isinstance(newPassword, str)
        self.__password = newPassword

    def getDB(self):
        return self.__db

    def setDB(self, newDB):
        assert isinstance(newDB, int)
        self.__db = newDB

    def getPort(self):
        return self.__port

    def setPort(self, newPort):
        assert isinstance(newPort, int)
        self.__port = newPort

    def getInputChannel(self):
        return self.__inputChannel

    def setInputChannel(self, newInputChannel):
        assert isinstance(newInputChannel, str)
        self.__inputChannel = newInputChannel

    def getOutputChannel(self):
        return self.__outputChannel

    def setOutputChannel(self, newOutputChannel):
        assert isinstance(newOutputChannel, str)
        self.__outputChannel = newOutputChannel

    def connect(self):
        self.__redis = redis.Redis(host=self.__host, port=self.__port, db=self.__db, password=self.__password)
        if self.__redis.info():
            print('Successfully Connected to Redis.')
        else:
            print('Redis Connection Failed!')

    def redisPublish(self, toPublish):
        str(toPublish)
        self.__redis.publish(channel=self.__outputChannel, message=toPublish)

    def addToRedisQueue(self, queueName, item):
        assert isinstance(queueName, str)
        str(item)
        self.__redis.rpush(queueName, item)


class CrazyMaster:
    __crazyFlie = Crazyflie() # A Crazyflie object.
    __uri = None  # The URI of __CrazyFlie.
    __isConnected = False  # Says if __CrazyFlie is connected or not (boolean).
    __logConf = None  # A LogConfig object.
    __logVariableList = None  # The list of the variable we want to monitor.
                                # Every element is a tuple of strings (variable_name, variableType)
    __crazyRedis = None

    def __init__(self, link_uri, logName='logs', msPeriod=1000, variableList=[],
                 crazyRedis=CrazyRedis( host='127.0.0.1', password='', db=0, port=6379, inChannel='CrazyInCh', outChannel='CrazyOutCh')):
        """ Initialize and run with the specified link_uri """
        # Initialize the low-level drivers (don't list the debug drivers)
        cflib.crtp.init_drivers(enable_debug_driver=False)
        self.setUri(link_uri)
        self.setLogVariableList(variableList)
        self.setLogConf(logName=logName, msPeriod=msPeriod)
        self.setCrazyRedis(crazyRedis)

    def connectToRedis(self):
        self.__crazyRedis.connect()

    def publishToRedis(self, toPublish):
        self.__crazyRedis.publish(toPublish)

    def connectToCrazyFlie(self):
        '''
        Try to connect to __crazyflie
        :param uri: string
        :return:
        '''
        uri = self.getUri()
        print('Connecting to %s' % uri)
        # Try to connect to the Crazyflie
        print('Scanning interfaces for Crazyflies...')
        available = cflib.crtp.scan_interfaces()
        print('Available Crazyflies:')
        trovato = False
        for i in available:
            print(i[0])
            if i[0] == uri:
                trovato = True
        if trovato:
            print('CrazyFlie found!')
            self.__crazyFlie.open_link(uri)
            # Variable used to keep main loop occupied until disconnect
            self.__isConnected = True
            print('Connected to Crazyflie.')
        else:
            print('CrazyFlie NOT found!')

    def getCrazyFlie(self):
        return self.__crazyFlie

    def setCrazyFlie(self, newCrazyFlie):
        assert newCrazyFlie.__class__.__name__ == "Crazyflie"
        self.__crazyFlie = newCrazyFlie

    def getUri(self):
        return self.__uri

    def setUri(self, newUri):
        assert isinstance(newUri, str)
        self.__uri = newUri

    def getIsConnected(self):
        return self.__isConnected

    def setIsConnected(self, newIsConnected):
        '''
        Update the value of __isConnected.
        :param newIsConnected: Boolean.
        :return:
        '''
        assert isinstance(newIsConnected, bool)
        self.__isConnected = newIsConnected

    def getLogVariableList(self):
        return self.__logVariableList

    def setLogVariableList(self, newLogVarList):
        assert isinstance(newLogVarList, list)
        for newElem in newLogVarList:
            assert isinstance(newElem, tuple)
            assert isinstance(newElem[0], str)
            assert isinstance(newElem[1], str)
        self.__logVariableList = newLogVarList

    def addToLogVariableList(self, newVariable):
        assert isinstance(newVariable, tuple)
        assert isinstance(newVariable[0], str)
        assert isinstance(newVariable[1], str)
        self.__logVariableList.append(newVariable)

    def getLogConf(self):
        return self.__logConf

    def setLogConf(self, logName='log', msPeriod=1000):
        '''
        Sets __logConf, the logging configuration.
        :param logName: The name of the logging.
        :param msPeriod: The period in milliseconds.
        :return:
        '''
        assert isinstance(logName, str)
        assert isinstance(msPeriod, int) or isinstance(msPeriod, float)
        self.__logConf = LogConfig(name=logName, period_in_ms=msPeriod)
        variables = self.getLogVariableList()
        if variables:
            for var in variables:
                self.__logConf.add_variable(var[0], var[1])

    def getCrazyRedis(self):
        return self.__crazyRedis

    def setCrazyRedis(self, newCrazyRedis):
        assert newCrazyRedis.__class__.__name__ == 'CrazyRedis'
        self.__crazyRedis = newCrazyRedis

    def addConnectionCallback(self, callback):
        '''
        Assigns a callback to connection event.
        :param callback: The callback function (we want to execute in case of connection).
        :return:
        '''
        try:
            self.__crazyFlie.connected.add_callback(callback)
            print('Connection CB assigned.')  # Test
        except:
            print("Unexpected error: ", sys.exc_info()[0])

    def addDisconnectionCallback(self, callback):
        '''
            Assigns a callback to disconnection event.
            :param callback: The callback function (we want to execute in case of disconnection).
            :return:
        '''
        try:
            self.__crazyFlie.disconnected.add_callback(callback)
            print('Disconnection CB assigned.')  # Test
        except:
            print("Unexpected error: ", sys.exc_info()[0])

    def addConnectionFailedCallback(self, callback):
        '''
            Assigns a callback to failed connection event.
            :param callback: The callback function (we want to execute in case of failed connection).
            :return:
        '''
        try:
            self.__crazyFlie.connection_failed.add_callback(callback)
            print('Connection Failed CB assigned.')  # Test
        except:
            print("Unexpected error: ", sys.exc_info()[0])

    def addConnectionLostCallback(self, callback):
        '''
            Assigns a callback to connection lost event.
            :param callback: The callback function (we want to execute in case of connection lost).
            :return:
        '''
        try:
            self.__crazyFlie.connection_lost.add_callback(callback)
            print('Connection Lost CB assigned.')  # Test
        except:
            print("Unexpected error: ", sys.exc_info()[0])

    def addLinkEstablishedCallback(self, callback):
        '''
            Assigns a callback to link established event.
            :param callback: The callback function (we want to execute in case of link established).
            :return:
        '''
        try:
            self.__crazyFlie.link_established.add_callback(callback)
            print('Link Established CB assigned.')  # Test
        except:
            print("Unexpected error: ", sys.exc_info()[0])

    def addCallback(self, eventName, callback):
        '''
        Binds an event and a callback with the appropriate __crazyFlie object method.
        :param eventName: The name (high level) of the triggering event.
        :param callback: The callback.
        :return:
        '''
        callbackDict = {"Connection": "connected"}  # Da completare
        assert isinstance(eventName, str)
        eventName.title() .replace(" ", "") # Set the first letter of each word uppercase and remove white spaces.
        assert eventName in ["Connection", "Disconnection", "ConnectionFailed", "ConnectionLost", "LinkEstablished"]
        # Da completare con altre API e rifare con Dictionary!!!!!!!!!!!
        methodName = "add" + eventName + "Callback"
        method = getattr(self, methodName)
        method(callback)

    # ------------ Default callbacks, you can modify them (be carefull) or add new ones

    def connected(self, link_uri):
        """ This callback is called form the Crazyflie API when a Crazyflie
        has been connected and the TOCs have been downloaded."""
        print('Connected to %s' % link_uri)
        # Redis Report
        sUnixTimeStamp = int(time.time())
        queue = str(self.getUri()) + '_connection'
        message = [sUnixTimeStamp]
        self.__crazyRedis.addToRedisQueue(queueName=queue, item=str(message))

    def startLogging(self, link_uri):
        '''
        Keep log data.
        You can use this function in a connection callback, because it can work after CrazyFlie connection only.
        :return:
        '''
        # Adding the configuration cannot be done until a Crazyflie is
        # connected, since we need to check that the variables we
        # would like to log are in the TOC.
        print('Starting Logging...')
        try:
            self.__crazyFlie.log.add_config(self.__logConf)
            # This callback will receive the data
            self.__logConf.data_received_cb.add_callback(self.receivedLogData)
            # This callback will be called on errors
            self.__logConf.error_cb.add_callback(self.loggingError)
            # Start the logging
            self.__logConf.start()
        except KeyError as e:
            print('Could not start log configuration,'
                  '{} not found in TOC'.format(str(e)))
        except AttributeError:
            print('Could not add log config, bad configuration.')
        # Redis Report
        sUnixTimeStamp = int(time.time())
        queue = self.getUri() + '_startLogging'
        message = [sUnixTimeStamp]
        self.__crazyRedis.addToRedisQueue(queueName=queue, item=str(message))


    def loggingError(self, logconf, msg):
        """Callback from the log API when an error occurs"""
        print('Error when logging %s: %s' % (logconf.name, msg))
        # Redis Report
        sUnixTimeStamp = int(time.time())
        message = [sUnixTimeStamp, (logconf.name, msg)]
        queue = self.getUri() + 'loggingError'
        self.__crazyRedis.addToRedisQueue(queueName=queue, item=str(message))

    def receivedLogData(self, timestamp, data, logconf):
        """Callback froma the log API when data arrives"""
        #acc = data['acc.z']
        z = data['range.zrange']
        #self.controller(z, acc)
        print('[%d][%s]: %s' % (timestamp, logconf.name, data))
        # Redis Report
        queue = self.getUri() + '_' + str(logconf.name)
        message = [timestamp, data]
        self.__crazyRedis.addToRedisQueue(queueName=queue, item=str(message))
        self.stableFly()

    def takeOff(self, z):
        for i in range(3):
            self.__crazyFlie.commander.send_hover_setpoint(0, 0, 0, z+(i/10))
        self.stableFly()

    def stableFly(self):
        self.__crazyFlie.commander.send_hover_setpoint(0, 0, 0, 1)

    def controller(self, z, acc):
        if acc > 1.2:
            if z < 1:
                self.__crazyFlie.commander.send_stop_setpoint()
            else:
                self.__crazyFlie.commander.send_hover_setpoint(0, 0, 0, 1)
        time.sleep(0.1)

    def connectionFailed(self, link_uri, msg):
        """Callback when connection initial connection fails (i.e no Crazyflie
        at the speficied address)"""
        sUnixTimeStamp = int(time.time())
        print('Connection to %s failed: %s' % (link_uri, msg))
        self.setIsConnected(newIsConnected=False)
        # Redis Report
        queue = self.getUri() + '_connectionFailed'
        message = [sUnixTimeStamp, msg]
        self.__crazyRedis.addToRedisQueue(queueName=queue, item=message)

    def connectionLost(self, link_uri, msg):
        """Callback when disconnected after a connection has been made (i.e
        Crazyflie moves out of range)"""
        sUnixTimeStamp = int(time.time())
        print('Connection to %s lost: %s' % (link_uri, msg))
        # Redis Report
        queue = self.getUri() + '_connectionLost'
        message = [sUnixTimeStamp, msg]
        self.__crazyRedis.addToRedisQueue(queueName=queue, item=message)

    def disconnected(self, link_uri):
        """Callback when the Crazyflie is disconnected (called in all cases)"""
        sUnixTimeStamp = int(time.time())
        print('Disconnected from %s' % link_uri)
        self.is_connected = False
        # Redis Report
        queue = self.getUri() + '_disconnection'
        message = [sUnixTimeStamp]
        self.__crazyRedis.addToRedisQueue(queueName=queue, item=message)



# TEST
''' # TEST
varList = [('stabilizer.roll', 'float'),
           ('stabilizer.pitch', 'float'),
           ('stabilizer.yaw', 'float'),
           ('pm.vbat', 'float'),
           ('acc.z', 'float')]
'''
varList = [('range.zrange', 'float'),
           ('acc.z', 'float')]
cr = CrazyRedis(host='127.0.0.1', password='', db=0, port=6379, inChannel='CrazyInCh', outChannel='CrazyOutCh')
cm = CrazyMaster('radio://0/80/1M', logName='logData', msPeriod=100, variableList=varList,
                 crazyRedis=cr)
cm.addCallback(eventName='Connection', callback=cm.startLogging)
cm.addCallback(eventName='Connection', callback=cm.connected)
cm.addCallback('ConnectionFailed', cm.connectionFailed)
cm.connectToRedis()
cm.connectToCrazyFlie()


# The Crazyflie lib doesn't contain anything to keep the application alive,
# so this is where your application should do something. In our case we
# are just waiting until we are disconnected.
while True:
    time.sleep(100000000)


# --------------------------------------------------------------------------- #
# import the modbus libraries we need
# --------------------------------------------------------------------------- #
from pymodbus.version import version
from pymodbus.server.asynchronous import StartTcpServer
from pymodbus.device import ModbusDeviceIdentification
from pymodbus.datastore import ModbusSequentialDataBlock
from pymodbus.datastore import ModbusSlaveContext, ModbusServerContext
from pymodbus.transaction import ModbusRtuFramer, ModbusAsciiFramer

# --------------------------------------------------------------------------- #
# import the twisted libraries we need
# --------------------------------------------------------------------------- #
from twisted.internet.task import LoopingCall

# --------------------------------------------------------------------------- #
# import the other libraries we need
# --------------------------------------------------------------------------- #
import pygame
import os
import time
import netifaces

# --------------------------------------------------------------------------- #
# configure the service logging
# --------------------------------------------------------------------------- #
import logging
logging.basicConfig()
log = logging.getLogger()
log.setLevel(logging.DEBUG)


# --------------------------------------------------------------------------- #
# initialize pygame joystick library
# --------------------------------------------------------------------------- #
pygame.init()
pygame.joystick.init()


#---------------------------------------------------------------------#
# checks if there's a joystick, returns controller obj once detected
# only runs on startup and then infrequently, as it is slow and messes
# with the stick position if run too often
#---------------------------------------------------------------------#    
def wait_for_joy():
    try:
        pygame.joystick.quit()
        pygame.joystick.init()
        if pygame.joystick.get_count() < 1:
            while pygame.joystick.get_count() < 1:
                print("no joystick found")
                pygame.joystick.quit()
                pygame.joystick.init()
                time.sleep(1)
            joy = pygame.joystick.Joystick(0)
            joy.init()
        else:
            joy = pygame.joystick.Joystick(0)
            joy.init()
        return joy
    except Exception as e:
        log.debug(e)
    
    
#----------------------------------------------------------------------#
# returns controller obj without checking for disconnect, much faster
# this is the function used most for updating stick position
#----------------------------------------------------------------------#
def return_joy():
    try:
        joy = pygame.joystick.Joystick(0)
        joy.init()
        return joy
    except Exception as e:
        log.debug(e)


#----------------------------------------------------------------------#
# not currently used, throws error when no screen is connected
#----------------------------------------------------------------------#
class TextPrint:
    def __init__(self):
        self.reset()
        self.font = pygame.font.Font(None, 25)
        

    def tprint(self, screen, text):
        text_bitmap = self.font.render(text, True, (0, 0, 0))
        screen.blit(text_bitmap, (self.x, self.y))
        self.y += self.line_height

    def reset(self):
        self.x = 10
        self.y = 10
        self.line_height = 15

    def indent(self):
        self.x += 10

    def unindent(self):
        self.x -= 10
    

#----------------------------------------------------------------------#
# grabs, scales, and sign masks stick positions from passed in joy obj
#----------------------------------------------------------------------#
def get_axes(joy):
    axis_array = [1] * 10
    pygame.event.pump()
    for i in range(joy.get_numaxes()):
        axis_array[i] = int (joy.get_axis(i) * 10000) & 0xFFFF #sign mask
    return axis_array
    
    
#----------------------------------------------------------------------#
# not currently used, throws errors when no screen is connected
#----------------------------------------------------------------------#    
def draw_screen(joy):
    screen.fill((255, 255, 255))
    text_print.reset()
    pygame.event.pump()
    print ("# Joysticks:", pygame.joystick.get_count())
    print ("Joystick initialized:", pygame.joystick.get_init())
    print (joy.get_name())
    print (joy.get_numaxes())
    for i in range(joy.get_numaxes()):
        text_print.tprint(screen, str(round(joy.get_axis(i), 2) * 1000))
    pygame.display.flip()
    
    
# function for try/catch loop. Ideally this will let it run forever
def try_main():
    
    try:
        #initialize joystick
        wait_for_joy()
        run_updating_server()
    except Exception as e:
        print("Crash detected, restarting in 5 seconds...")
        print(e)
        loop.stop()
        loopControllerCheck.stop()
        StopTcpServer()


# --------------------------------------------------------------------------- #
# define your callback process 
# --------------------------------------------------------------------------- #
def updating_writer(a):
    try:
        """ A worker process that runs every so often and
        updates live values of the context. It should be noted
        that there is a race condition for the update.

        :param arguments: The input arguments to the call
        """
        joy = return_joy()
        pygame.event.pump()
        log.debug("updating the context")
        context = a[0]
        register = 3
        slave_id = 0x00
        address = 0x00
        values = get_axes(joy)
        log.debug("Left Joystick: " + str(values[0:2]))
        log.debug("Right Joystick: " + str(values[3:5]))
        log.debug("numControllers : "+ str(pygame.joystick.get_count()))
        context[slave_id].setValues(register, address, values)
    except Exception as e:
        log.debug(e)


def run_updating_server():
    # ----------------------------------------------------------------------- # 
    # initialize your data store
    # ----------------------------------------------------------------------- # 
    
    store = ModbusSlaveContext(
        di=ModbusSequentialDataBlock(0, [17]*100),
        co=ModbusSequentialDataBlock(0, [17]*100),
        hr=ModbusSequentialDataBlock(0, [17]*100),
        ir=ModbusSequentialDataBlock(0, [17]*100))
    context = ModbusServerContext(slaves=store, single=True)
    
    # ----------------------------------------------------------------------- # 
    # initialize the server information
    # ----------------------------------------------------------------------- # 
    identity = ModbusDeviceIdentification()
    identity.VendorName = 'pymodbus'
    identity.ProductCode = 'PM'
    identity.VendorUrl = 'http://github.com/riptideio/pymodbus/'
    identity.ProductName = 'pymodbus Server'
    identity.ModelName = 'pymodbus Server'
    identity.MajorMinorRevision = version.short()
    ip = netifaces.ifaddresses('eth0')[netifaces.AF_INET][0]['addr']
    
    # ----------------------------------------------------------------------- # 
    # run the server you want
    # ----------------------------------------------------------------------- # 
    time = 0.2  # 1 seconds delay
    timeControllerCheck = 5
    loopControllerCheck = LoopingCall(f=wait_for_joy)
    loop = LoopingCall(f=updating_writer, a=(context,))
    loop.start(time, now=False) # initially delay by time
    loopControllerCheck.start(timeControllerCheck, now=False)
    StartTcpServer(context, identity=identity, address=(ip, 5020))


if __name__ == "__main__":
    while(True):
        try_main()
        time.sleep(5)

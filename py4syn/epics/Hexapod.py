"""Hexapod Class
Python class to control hexapod devices.
:platform: Unix
:synopsis: Python Class for hexapod devices
.. moduleauthor:: João Marcos Suckow de B. Rodrigues <joao.rodrigues@lnls.br,jm@suckow.com.br> """

from epics import PV, Device, ca
from py4syn.epics.IScannable import IScannable
from py4syn.epics.StandardDevice import StandardDevice
from py4syn.epics.MotorClass import Motor
import time
from threading import Thread 

class HexapodMotor(Motor):
	"""
	Class to control hexapod devices via EPICS.
	"""
	def __init__(self, mnemonic, axis, pvMotor, hexapodPV):

		"""self.hexapod = Device(hexapodPV + ':',
					 ('STATE#PANEL:SET','STATE#PANEL:GET','STATE#PANEL:BUTTON','MOVE#PARAM:'+axis,'CFG#CS:1','CFG#CS:2', 'STATE#POSVALID', 'CFG#CS?:1', 'CFG#CS?:2', 'CFG#CS?:3', 'CFG#CS?:4','CFG#CS?:5','CFG#CS?:6','CFG#CS?:7','CFG#CS?:8','CFG#CS?:9','CFG#CS?:10','CFG#CS?:11','CFG#CS?:12','CFG#CS?:13' ))"""

		# Specific PVs for Hexopod

		self.moveMode = PV(hexapodPV+':MOVE#PARAM:CM')           # 0: ABSOLUTE; 1: RELATIVE TO OBJECT; 2: RELATIVE TO USER;
		self.moveVal  = PV(hexapodPV+':MOVE#PARAM:' + axis)
		self.rbv      = PV(hexapodPV+':POSUSER:' + axis + '.VAL')
		self.proc     = PV(hexapodPV+':POSUSER:' + axis + '.PROC')
		self.cmdButton  = PV(hexapodPV+':STATE#PANEL:BUTTON')                                                                       
		self.cmdSet   = PV(hexapodPV+':STATE#PANEL:SET')                                                                                                    
		self.cmdGet   = PV(hexapodPV+':STATE#PANEL:GET')

		self.axis = axis;

		super().__init__(pvMotor,mnemonic)	
		self.threadWait = None


		self.enable()	
		
	def __str__(self):
		self.info(verbose=True)
		if(self.isEnabled()):
			print("Status: Enabled")
		else:
			print("Status: Disabled")
	

	def enable(self):
		self.cmdButton.put(0)
		self.cmdSet.put(0)

	def disable(self):
		self.cmdButton.put(1) 
		self.cmdSet.put(0)	

	def isEnabled(self):
		if (self.cmdButton.get() == 0):
			return True
		else:
			return False

	def __setPanelState(self, stateNumber):
		self.cmdSet.put(stateNumber, wait=True)
		#self.cmdSet.put(0,wait=True)
		finished = self.cmdGet.get()	
		while(finished != 0):
			finished = self.cmdGet.get()

		#if(finished < 0):
		#	raise Exception("An error occurred when setting panel state: Error code:"+ str(finished))

	def stopAllMovements(self): #2
		self.__setPanelState(2)

	def enableMotorControl(self): #3
		self.__setPanelState(3)

	def disableMotorControl(self): #4
		self.__setPanelState(4)

	def move(self, value, waitComplete=False): #11
		self.moveVal.put(value, wait=waitComplete)
		self.__setPanelState(11) 

	def setMoveMode(self, mode, waitComplete=False):
		# 0: ABSOLUTE; 1: RELATIVE TO OBJECT; 2: RELATIVE TO USER;
		if(mode!=0 and mode!=1 and mode!=2):
			raise ValueError("Invalid value for mode argument. It should be between 0 and 2")
		else:
			self.moveMode.put(mode, wait=waitComplete)


	"""Motor Methods"""

	def isMovingPV(self):
		moving = False                                                                                   
		try:                                                                             
			moving = self.cmdGet.get() !=0
		except AttributeError:
			print("Error - Attribute")
			pass
		return moving


	def getRealPosition(self): 
		self.proc.put(1)
		time.sleep(0.1)
		self.proc.put(0)

		return self.rbv.get()

	def getPosition(self):
        	return self.getRealPosition()


	def setAbsolutePosition(self, pos, waitComplete=False):
		if (self.getRealPosition() == pos):
			return;

		self._moving = True

		# Just to guarantee the command will be received
		self.enable()

		# Configure to absolute moviment
		self.setMoveMode(0, waitComplete=waitComplete)

		self.move(pos, waitComplete=waitComplete)

		if (waitComplete):
			self.wait()
		else:
			if (self.threadWait == None):
				self.threadWait = Thread(target=self.wait)
				self.threadWait.daemon = True
				self.threadWait.start()

	def stop(self):
		self.__setPanelState(0)
		
		self._moving = False


	def wait(self):
		# Wait it completes
		while (self.cmdGet.get() == 0):
			time.sleep(1)
			delta = abs(float(self.getRealPosition()) - float(self.moveVal.get()))

			if (delta < 1e-4):
				break

		# Forces stopping
		self.stop()

		# Updates threadWait attribute
		self.threadWait = None

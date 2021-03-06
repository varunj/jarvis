import time
import RPi.GPIO as GPIO
import requests
import serial
import subprocess
#AC/Heater range [18,45]

def toBool(inpBool):
	if (inpBool == "true"):
		return True
	return False

# BCM for GPIO pins (read nos in rectangles)
GPIO.setmode(GPIO.BCM)

# Set pins for usage
GPIO.setup(18, GPIO.OUT)
GPIO.setup(23, GPIO.OUT)
GPIO.setup(24, GPIO.OUT)
GPIO.setup(21, GPIO.OUT)
GPIO.setup(17, GPIO.OUT)
GPIO.setup(27, GPIO.OUT)

#serialTemp = serial.Serial('/dev/ttyACM3',9600)							# BEWARE use lsusb to see bus number (USB0/ USB1....)

countRoomEmpty = 0 			# Number of seconds for which nobody in room
roomIsEmpty = 0 			# If room empty: 1, else: 0


applianceGPIO = [18, 23, 24, 21] 											#Assuming 4 appliances on 18,23,24,25 respectively
applianceName = {18:'Fridge', 23:'Charger', 24:'Oven', 21:'Garage Opener'}
applianceOn = [True, True, True, True] 										#Tells whether appliance is ON or OFF
appliancePrev = True
requests.post("http://1.1.1.4:3000/postApp",params={'0':applianceOn[0], '1':applianceOn[1], '2':applianceOn[2], '3':applianceOn[3]})	# Get Appliance State

acTemp = 22 			# Temperature required
requests.post("http://1.1.1.4:3000/acTempSend",params={'actemp':acTemp})
nosPeoplePrev = 0 			# Number of people in the room before scanning the file

subprocess.Popen(["pico2wave", "--lang=en-US", "--wave=/home/pi/Desktop/ied/jarvis/intro.wav", "Booting up system"])
subprocess.Popen(["mplayer", "intro.wav"])

while(1):
	try:
		# tempSensor = int(serialTemp.readline().split(" ")[0][:-3])
		# humSensor = int(serialTemp.readline().split(" ")[1][:-4])
		# requests.post("http://1.1.1.4:3000/temp",params={'temp':tempSensor, 'humidity':humSensor})			# Post Temp, Hum
		# print "Temp: "+ str(tempSensor)
		# print "Humd: "+ str(humSensor)

		# Get appliance states from server
		applianceOn = map(toBool,requests.get("http://1.1.1.4:3000/data")._content.split(","))								# Get Appliance State
		print "Appliance    : " + str(applianceOn)

		# Get no. of people from server
		nosPeople = int(requests.get("http://1.1.1.4:3000/nosPeople2")._content)
		print "Nos of People: " + str(nosPeople)

		for i in range(3):
			if not applianceOn[i]:
				GPIO.output(applianceGPIO[i], GPIO.LOW)
			else:
				GPIO.output(applianceGPIO[i], GPIO.HIGH)	

		if(nosPeople == 0):
			if(not roomIsEmpty):
				countRoomEmpty = countRoomEmpty + 1
			else:
				countRoomEmpty = 0
		print "Room Em Sec: " + str(countRoomEmpty)

		# Power Down if no people for >= 4 cycles
		if(countRoomEmpty == 4):
			for i in range(3):
				GPIO.output(applianceGPIO[i],GPIO.LOW)
				applianceOn[i] = False
			countRoomEmpty = 0	
			roomIsEmpty = 0
			requests.post("http://1.1.1.4:3000/postApp",params={'0':applianceOn[0], '1':applianceOn[1], '2':applianceOn[2], '3':applianceOn[3]})

		# If fire, Sound Alarm, Power all devices down
		if(int(requests.get("http://1.1.1.4:3000/panic")._content) == 1):
			for i in range(3):
				GPIO.output(applianceGPIO[i],GPIO.LOW)
				applianceOn[i] = False
				time.sleep(0.5)
			subprocess.Popen(["mplayer", "panic.wav"])
			requests.post("http://1.1.1.4:3000/postApp",params={'0':applianceOn[0], '1':applianceOn[1], '2':applianceOn[2], '3':applianceOn[3]})


		# Open Garage
		if (applianceOn[3] == True):
			GPIO.output(21, GPIO.LOW)
		else:
			GPIO.output(21, GPIO.HIGH)
			

		acTemp = int(requests.get("http://1.1.1.4:3000/acTempRec")._content)
		if (acTemp > 15 and acTemp < 46):
			acTemp = acTemp - (nosPeople - nosPeoplePrev)*5

		# Control Fan
		if (nosPeople == 0):
			GPIO.output(17, GPIO.LOW)
			GPIO.output(27, GPIO.LOW)
		elif (nosPeople == 1):
			GPIO.output(17, GPIO.HIGH)
			GPIO.output(27, GPIO.LOW)
		elif (nosPeople == 2):
			GPIO.output(17, GPIO.LOW)
			GPIO.output(27, GPIO.HIGH)
		else:
			GPIO.output(17, GPIO.HIGH)
			GPIO.output(27, GPIO.HIGH)

		# send the ac temperature to server
		requests.post("http://1.1.1.4:3000/acTempSend",params={'actemp':acTemp}) 			# Send AC Temp
		nosPeoplePrev = nosPeople
		time.sleep(0.5)


	except:
		pass

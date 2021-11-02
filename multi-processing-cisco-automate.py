#/usr/bin/python3
##########################################################################################################
#                                                                                                        #
#   Example code to do large scale network automation.                                                   #
#   The code is optimized for large enviorments where it is benifical to run multiple threads to speed   #
#   up the execution of the script. in this case i'm just finding all switches with a switch 2 in the    #
#   stack. The code should be documented well enough to be modified to do pretty much anything with some #
#   understanding of python. The code is tested on ubuntu but should work on all platforms               #
#                                                                                                        #
#   Author: Anders Ballegaard                                                                            #
#   Github repo:  https://github.com/AndersBallegaard/python-network-automation-example                  #
#   Website: anderstb.dk                                                                                 #
#                                                                                                        #
########################################################################################################## 

#import modules 
from netmiko import ConnectHandler
from getpass import getpass
import multiprocessing
import datetime
import requests

#input username for both infoblox and switches and routers
username = input("Username: ")

#input and verify password
password = ""
ptrue = True
while(ptrue):
	password = getpass("Password: ")
	pcheck = getpass("verify password: ")
	if(pcheck == password):
		ptrue = False
	else:
		print("something went wrong")

#print the time. This is mostly for telling how long and when your script ran
print(datetime.datetime.now())

#now to the star of the show. The function that runs for every device
#this function is called with only the device ip or dns name. 
#there is nothing to handle output from this so just handle it your self
def actionps(sw):
    #some things just fail so catch it
    try:
        #define the switch object. This will be used to connect to the device
        ios_switch = {
            #ios is pretty good for ios and ios xe, look up netmiko supported devices for other needs
            'device_type': 'cisco_ios', 
            #ip or dns name for the device
            'ip': sw,
            #let's just use the global creds for everything
            'username': username,
            'password': password,
        }
        #connect to the device
        connection = ConnectHandler(**ios_switch)
        #run a sh it status and save the output in a string
        rawout = connection.send_command("sh int status")
        #just as an example let's see if we have a 2/0/1 interface and output something if we do
        if ("2/0/1" in rawout):
            print(sw + " have atleast 2 switches")
    #as said eailer everything fails including your network and my code
    except Exception as e:
        print(str(e))

#ask infoblox.example.com's dns server for everything in the sw.example.com internal view
r = requests.get('https://infoblox.example.com/wapi/v2.1/record:a?_max_results=50000&zone=sw.example.com&view=Internal',auth=(username,password),verify=False)

#store the json
output = r.json()

#swlist is the list of switches. if you don't use infoblox just make sure all switch names/ip's are as string here
swlist = []

#parse the json output for the switch dns names and append to swlist
for s in output:
    swlist.append(s['name'])

#ok this is fun, my attention span is way to short so i'm doing 128 devices at a time instead of one
#and this is the best way i have found to do it
#start by defining a multithreading pool
p = multiprocessing.Pool(128)
#then map actionps and the swlist to it and watch the magic happen
p.map(actionps, swlist)

#when it's all done output the time again
print(datetime.datetime.now())

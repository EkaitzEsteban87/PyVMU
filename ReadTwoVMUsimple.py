# -*- coding: utf-8 -*-
"""
Created on Wed Nov 21 09:21:05 2018

Simple example Script:
    
Reading data from two VMU931 devices running in parallel.
It can be extended to multiple VMU931 devices...

Information about pyVMU toolkit: https://pyvmu.readthedocs.io/en/latest/

@author: E. Esteban
"""

import matplotlib.pyplot as plt
from pyvmu.vmu931 import VMU931Parser
from pyvmu import messages
    
ts_points = []
x_points = []
y_points = []
z_points = []

ts2_points = []
x2_points = []
y2_points = []
z2_points = []
  
def TwoVMUlauncher():
    with VMU931Parser(device="COM4",euler=True) as vp, VMU931Parser(device="COM5",euler=True) as vp2:
        while True: # The program never ends... will be killed when master is over.
            pkt = vp.parse()
            pkt2 = vp2.parse()
            
            if isinstance(pkt2, messages.Status):
                print(pkt2)
                
            if isinstance(pkt, messages.Status):
                print(pkt)
               
            if isinstance(pkt, messages.Euler):
                ts, x, y, z = pkt
                ts_points.append(ts)
                x_points.append(x)
                y_points.append(y)
                z_points.append(z)
            
            if isinstance(pkt2, messages.Euler):
                ts, x, y, z = pkt2
                ts2_points.append(ts)
                x2_points.append(x)
                y2_points.append(y)
                z2_points.append(z)
                
            if len(ts_points) % 100 == 0:
                print(x_points)
                print(x2_points)
                
TwoVMUlauncher()     

plt.figure(1)
plt.plot(x_points)
plt.plot(x2_points)
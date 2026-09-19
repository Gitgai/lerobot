import scservo_sdk as scs, time, os, sys
port_name=os.environ.get("FOLLOWER_PORT","/dev/ttyACM1")
port=scs.PortHandler(port_name)
if not port.openPort(): print("cannot open", port_name); sys.exit(0)
port.setBaudRate(1000000); ph=scs.PacketHandler(0)
cleared=[]
for i in range(1,7):
    m,res,err=ph.ping(port,i)
    if res==0 and err:
        ph.write1ByteTxRx(port,i,40,0)      # TorqueEnable=0 clears latched error
        time.sleep(0.2); m,res,err=ph.ping(port,i)
        cleared.append((i,"cleared" if err==0 else f"STILL err={err}"))
port.closePort()
print("cleared:", cleared if cleared else "nothing to clear (all err=0)")

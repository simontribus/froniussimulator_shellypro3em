import threading
import struct
import time
import datetime
import requests
from pymodbus.device import ModbusDeviceIdentification
from pymodbus.datastore import ModbusSparseDataBlock
from pymodbus.datastore import ModbusSlaveContext
from pymodbus.datastore import ModbusServerContext
from pymodbus.server import StartTcpServer, ModbusTcpServer
import asyncio  # Add asyncio for handling the event loop

# Configuration for Shelly Pro 3EM REST API
shelly_config = {
    'base_url': "http://<your-shelly-ip-here>/rpc/Shelly.GetStatus"
}

modbus_port = 502
lock = threading.Lock()

leistung = 0.0
netzbezug = 0.0
einspeisung = 0.0

l1 = 0.0
l2 = 0.0
l3 = 0.0

l1_v = 0.0
l2_v = 0.0
l3_v = 0.0

current = 0.0

l1_c = 0.0
l2_c = 0.0
l3_c = 0.0

avg_freq = 0.0

aparent_power = 0.0

l1_aprt_pw = 0.0
l2_aprt_pw = 0.0
l3_aprt_pw = 0.0

def fetch_shelly_data():
    global leistung, netzbezug, einspeisung, current, l1, l2, l3, l1_aprt_pw, l2_aprt_pw, l3_aprt_pw, aparent_power, l1_v, l2_v, l3_v, avg_freq, l1_c, l2_c, l3_c

    try:
        response = requests.get(shelly_config['base_url'])
        response.raise_for_status()
        data = response.json()

        # Extract required values from the API response
        leistung = data['em:0']['total_act_power']
        netzbezug = data['emdata:0']['total_act']
        einspeisung = data['emdata:0']['total_act_ret']
        
        l1 = data['em:0']['a_act_power']
        l2 = data['em:0']['b_act_power']
        l3 = data['em:0']['c_act_power']
        
        l1_v = data['em:0']['a_voltage']
        l2_v = data['em:0']['b_voltage']
        l3_v = data['em:0']['c_voltage']
        
        current = data['em:0']['total_current']

        l1_c = data['em:0']['a_current']
        l2_c = data['em:0']['b_current']
        l3_c = data['em:0']['c_current']
        
        l1_aprt_pw = data['em:0']['a_aprt_power']
        l2_aprt_pw = data['em:0']['b_aprt_power']
        l3_aprt_pw = data['em:0']['c_aprt_power']

        avg_freq =  (data['em:0']['a_freq']+data['em:0']['b_freq']+data['em:0']['c_freq'])/3.0
        
        aparent_power = data['em:0']['total_aprt_power']
    except requests.RequestException as e:
        print(f"{datetime.datetime.now()}: Error fetching data from Shelly: {e}")


def calculate_register(value_float):
    int1 = 0
    int2 = 0
    try:
        if value_float == 0:
            int1 = 0
            int2 = 0
        else:
            value_hex = hex(struct.unpack('<I', struct.pack('<f', value_float))[0])
            value_hex_part1 = str(value_hex)[2:6]
            value_hex_part2 = str(value_hex)[6:10]
            int1 = int(value_hex_part1, 16)
            int2 = int(value_hex_part2, 16)
    except requests.RequestException as e:
        print(f"{datetime.datetime.now()}: Error calculating register: {e}")
    return (int1, int2)

def updating_writer(a_context):
    global leistung, netzbezug, einspeisung, current, l1, l2, l3, l1_aprt_pw, l2_aprt_pw, l3_aprt_pw, aparent_power, l1_v, l2_v, l3_v, avg_freq, l1_c, l2_c, l3_c

    lock.acquire()
    fetch_shelly_data()

    ep_int1, ep_int2 = calculate_register(leistung)
    ti_int1, ti_int2 = calculate_register(netzbezug)
    exp_int1, exp_int2 = calculate_register(einspeisung)

    l1_int1, l1_int2 = calculate_register(l1)
    l2_int1, l2_int2 = calculate_register(l2)
    l3_int1, l3_int2 = calculate_register(l3)
    
    l1_v_int1, l1_v_int2 = calculate_register(l1_v)
    l2_v_int1, l2_v_int2 = calculate_register(l2_v)
    l3_v_int1, l3_v_int2 = calculate_register(l3_v)

    current_int1, current_int2 = calculate_register(current)

    l1_c_int1, l1_c_int2 = calculate_register(l1_c)
    l2_c_int1, l2_c_int2 = calculate_register(l2_c)
    l3_c_int1, l3_c_int2 = calculate_register(l3_c)

    avg_freq_int1, avg_freq_int2 = calculate_register(avg_freq)

    l1_aprt_pw_int1, l1_aprt_pw_int2 = calculate_register(l1_aprt_pw)
    l2_aprt_pw_int1, l2_aprt_pw_int2 = calculate_register(l2_aprt_pw)
    l3_aprt_pw_int1, l3_aprt_pw_int2 = calculate_register(l3_aprt_pw)
    
    aprt_power_int1, aprt_power_int2 = calculate_register(aparent_power)

    context = a_context[0]
    register = 3
    slave_id = 0x01
    address = 0x0047
    values = [
        current_int1, current_int2,               # Ampere - AC Total Current Value [A]
        l1_c_int1, l1_c_int2,               # Ampere - AC Current Value L1 [A]
        l2_c_int1, l2_c_int2,               # Ampere - AC Current Value L2 [A]
        l3_c_int1, l3_c_int2,               # Ampere - AC Current Value L3 [A]
        0, 0,               # Voltage - Average Phase to Neutral [V]
        l1_v_int1, l1_v_int2,               # Voltage - Phase L1 to Neutral [V]
        l2_v_int1, l2_v_int2,               # Voltage - Phase L2 to Neutral [V]
        l3_v_int1, l3_v_int2,               # Voltage - Phase L3 to Neutral [V]
        0, 0,               # Voltage - Average Phase to Phase [V]
        0, 0,               # Voltage - Phase L1 to L2 [V]
        0, 0,               # Voltage - Phase L2 to L3 [V]
        0, 0,               # Voltage - Phase L1 to L3 [V]
        avg_freq_int1, avg_freq_int2,               # AC Frequency [Hz]
        ep_int1, ep_int2,   # AC Power value (Total) [W]
        l1_int1, l1_int2,   # AC Power Value L1 [W]
        l2_int1, l2_int2,   # AC Power Value L2 [W]
        l3_int1, l3_int2,   # AC Power Value L3 [W]
        aprt_power_int1, aprt_power_int2,               # AC Apparent Power [VA]
        l1_aprt_pw_int1, l1_aprt_pw_int2,               # AC Apparent Power L1 [VA]
        l2_aprt_pw_int1, l2_aprt_pw_int2,                # AC Apparent Power L2 [VA]
        l3_aprt_pw_int1, l3_aprt_pw_int2,                # AC Apparent Power L3 [VA]
        0, 0,               # AC Reactive Power [VAr]
        0, 0,               # AC Reactive Power L1 [VAr]
        0, 0,               # AC Reactive Power L2 [VAr]
        0, 0,               # AC Reactive Power L3 [VAr]
        exp_int1, exp_int2, # Total Watt Hours Exported [Wh]
        0, 0,               # Watt Hours Exported L1 [Wh]
        0, 0,               # Watt Hours Exported L2 [Wh]
        0, 0,               # Watt Hours Exported L3 [Wh]
        ti_int1, ti_int2,   # Total Watt Hours Imported [Wh]
        0, 0,               # Watt Hours Imported L1 [Wh]
        0, 0,               # Watt Hours Imported L2 [Wh]
        0, 0,               # Watt Hours Imported L3 [Wh]
        0, 0,               # Total VA hours Exported [VA]
        0, 0,               # VA hours Exported L1 [VA]
        0, 0,               # VA hours Exported L2 [VA]
        0, 0,               # VA hours Exported L3 [VA]
        0, 0,               # Total VAr hours Imported [VAr]
        0, 0,               # VAr hours Imported L1 [VAr]
        0, 0,               # VAr hours Imported L2 [VAr]
        0, 0                # VAr hours Imported L3 [VAr]
    ]

    context.setValues(register, address, values)
    time.sleep(1)
    lock.release()

class CustomModbusTcpServer(ModbusTcpServer):
    """Custom ModbusTcpServer that logs requests."""
    
    def handle_request(self, request):
        print(f"{datetime.datetime.now()}: Modbus request received: {request}")
        super().handle_request(request)  # Process the request as usual

async def run_updating_server():
    global modbus_port
    lock.acquire()
    datablock = ModbusSparseDataBlock({

        1:  [21365, 28243],
        3:  [1],
        4:  [65],
        5:  [70,114,111,110,105,117,115,0,0,0,0,0,0,0,0,0,         #Manufacturer "Fronius
                83,109,97,114,116,32,77,101,116,101,114,32,54,51,65,0, #Device Model "Smart Meter
                0,0,0,0,0,0,0,0,                                       #Options N/A
                0,0,0,0,0,0,0,0,                                       #Software Version  N/A
                48,48,48,48,48,48,48,50,0,0,0,0,0,0,0,0,               #Serial Number: 00000 (should be different if there are more Smart Meters)
                240],                                                  #Modbus TCP Address: 240?
        70: [213],
        71: [124],
        72: [0,0,0,0,0,0,0,0,0,0,
                0,0,0,0,0,0,0,0,0,0,
                0,0,0,0,0,0,0,0,0,0,
                0,0,0,0,0,0,0,0,0,0,
                0,0,0,0,0,0,0,0,0,0,
                0,0,0,0,0,0,0,0,0,0,
                0,0,0,0,0,0,0,0,0,0,
                0,0,0,0,0,0,0,0,0,0,
                0,0,0,0,0,0,0,0,0,0,
                0,0,0,0,0,0,0,0,0,0,
                0,0,0,0,0,0,0,0,0,0,
                0,0,0,0,0,0,0,0,0,0,
                0,0,0,0],

        196: [65535, 0],
    })

    slave_store = ModbusSlaveContext(
        di=datablock,
        co=datablock,
        hr=datablock,
        ir=datablock,
    )

    lock.release()
    
    a_context = ModbusServerContext(slaves=slave_store, single=True)

    rt = RepeatedTimer(2, updating_writer, a_context)

    print(f"{datetime.datetime.now()}: ### Starting Modbus server on port {modbus_port}")
    print(f"{datetime.datetime.now()}: ### Version 1.0.2 {modbus_port}")

    address = ("0.0.0.0", modbus_port)

    server = CustomModbusTcpServer(context=a_context, address=address)
    await server.serve_forever()
    
class RepeatedTimer:
    def __init__(self, interval, function, *args, **kwargs):
        self._timer = None
        self.interval = interval
        self.function = function
        self.args = args
        self.kwargs = kwargs
        self.is_running = False
        self.start()

    def _run(self):
        self.is_running = False
        self.start()
        self.function(*self.args, **self.kwargs)

    def start(self):
        if not self.is_running:
            self._timer = threading.Timer(self.interval, self._run)
            self._timer.start()
            self.is_running = True

    def stop(self):
        self._timer.cancel()
        self.is_running = False

asyncio.run(run_updating_server())

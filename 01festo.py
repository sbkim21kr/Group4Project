import time
import pymcprotocol

# --- Configuration for PLC devices ---
PLC_CONFIG = {
    "connection": {
        "ip": "192.168.3.39",
        "port": 4001,
    },
    "devices": {
        "start_trigger": "M400",   # Start device
        "end":   "M401",   # End device for success outcomes or empty tray
        "start_logitech":      "M402",   # End device for fail outcomes
        "end_success":   "M403",   
        "end_fail":      "M404",  
        "outcomes": {              # 5 possible outcomes
            # "tray_empty":  "M000",
            "orange_pass": "M403",
            # "orange_fail": "M404",
            "brown_pass":  "M403",
            # "brown_fail":  "M404",
        }
    },
    "io": {
        "bit_switch1": "Y68",
        "bit_switch2": "Y6A",
        "bit_switch3": "Y6C",
        "trigger":     "Y6E",
        "ready":       "X0A",
        "validate":    "X0C",
        "result_job1_3": "X06",
        "result_job2_4": "X08",
    }
}


class FestoSensorWorker:
    def __init__(self, config=PLC_CONFIG):
        self.config = config
        self.PLC_IP   = config["connection"]["ip"]
        self.PLC_PORT = config["connection"]["port"]
        self.io       = config["io"]
        self.devices  = config["devices"]

    # --- Helper functions ---
    def reset_all_y(self):
        for y in [self.io["bit_switch1"], self.io["bit_switch2"], self.io["bit_switch3"]]:
            self.plc.batchwrite_bitunits(headdevice=y, values=[0])
            val = self.plc.batchread_bitunits(y, 1)[0]
            #print(f"[Festo] Reset {y}=0 → Confirmed {val}")
        time.sleep(0.2)

    def pulse_bit(self, address, on_time=0.5, off_time=0.5):
        self.plc.batchwrite_bitunits(headdevice=address, values=[1])
        val = self.plc.batchread_bitunits(address, 1)[0]
        #print(f"[Festo] Wrote {address}=1 → Confirmed {val}")
        time.sleep(on_time)
        self.plc.batchwrite_bitunits(headdevice=address, values=[0])
        val = self.plc.batchread_bitunits(address, 1)[0]
        print(f"[Festo] Wrote {address}=0 → Confirmed {val}")
        time.sleep(off_time)

    def set_plc_bit(self, address):
        try:
            self.plc.batchwrite_bitunits(headdevice=address, values=[1])
            val = self.plc.batchread_bitunits(address, 1)[0]
        except Exception as e:
            print(f"Error setting {address} to {val}: {e}")

    def wait_ready(self):
        while True:
            val = int(self.plc.batchread_bitunits(self.io["ready"], 1)[0])
            if val == 1:
                #print("[Festo] Ready (X0A=1)")
                return
            time.sleep(0.5)

    def wait_validate(self):
        while True:
            val = int(self.plc.batchread_bitunits(self.io["validate"], 1)[0])
            if val == 1:
                #print("[Festo] Validate (X0C=1)")
                return
            time.sleep(0.5)

    # --- Job routines ---
    def run_job1(self):
        print("[Festo] Running Job1: Tray empty check")
        self.plc.batchwrite_bitunits(self.io["bit_switch1"], [1])
        self.wait_ready()
        self.pulse_bit(self.io["trigger"])
        self.wait_validate()
        val = int(self.plc.batchread_bitunits(self.io["result_job1_3"], 1)[0])
        print(f"[Festo] Job1 result (X06)={val}")
        self.reset_all_y()
        return val

    def run_job2(self):
        print("[Festo] Running Job2: Orange vs Brown")
        self.plc.batchwrite_bitunits(self.io["bit_switch2"], [1])
        self.wait_ready()
        self.pulse_bit(self.io["trigger"])
        self.wait_validate()
        val = int(self.plc.batchread_bitunits(self.io["result_job2_4"], 1)[0])
        print(f"[Festo] Job2 result (X08)={val}")
        self.reset_all_y()
        return val

    def run_job3(self):
        print("[Festo] Running Job3: Orange defect check")
        self.plc.batchwrite_bitunits(self.io["bit_switch1"], [1])
        self.plc.batchwrite_bitunits(self.io["bit_switch2"], [1])
        self.wait_ready()
        self.pulse_bit(self.io["trigger"])
        self.wait_validate()
        val = int(self.plc.batchread_bitunits(self.io["result_job1_3"], 1)[0])
        print(f"[Festo] Job3 result (X06)={val}")
        self.reset_all_y()
        return val

    def run_job4(self):
        print("[Festo] Running Job4: Brown defect check")
        self.plc.batchwrite_bitunits(self.io["bit_switch3"], [1])
        self.wait_ready()
        self.pulse_bit(self.io["trigger"])
        self.wait_validate()
        val = int(self.plc.batchread_bitunits(self.io["result_job2_4"], 1)[0])
        print(f"[Festo] Job4 result (X08)={val}")
        self.reset_all_y()
        return val

    # --- Main run loop ---
    def run(self):
        print("[Festo] Worker started")
        self.plc = pymcprotocol.Type3E()
        try:
            self.plc.connect(self.PLC_IP, self.PLC_PORT)
            print("[Festo] Connected to PLC")
        except Exception as e:
            print(f"[Festo] Initial PLC connection failed: {e}")
            return

        start_device = self.devices["start_trigger"]

        while True:
            try:
                trigger_val = int(self.plc.batchread_bitunits(start_device, 1)[0])
            except Exception as e:
                print(f"[Festo] PLC read error: {e}")
                time.sleep(1)
                continue

            if trigger_val == 1:
                print(f"\n[Festo] Trigger received ({start_device}=1) → running jobs")

                outcome = None

                # Job1
                job1_val = self.run_job1()
                if job1_val == 1:
                    print("[Festo] Tray empty outcome")
                    outcome = "tray_empty"
                else:
                    job2_val = self.run_job2()
                    if job2_val == 1:
                        job3_val = self.run_job3()
                        if job3_val == 1:
                            print("[Festo] Orange pass outcome")
                            outcome = "end_success"
                        else:
                            print("[Festo] Orange fail outcome")
                            outcome = "end_fail"
                    else:
                        job4_val = self.run_job4()
                        if job4_val == 1:
                            print("[Festo] Brown pass outcome")
                            outcome = "end_success"
                        else:
                            print("[Festo] Brown fail outcome")
                            outcome = "end_fail"

                # End pulse depends on outcome
                if outcome in ["end_success"]:
                    print("[Festo] Pulsing end device M401 (success group)")
                    self.pulse_bit(self.devices["end"], 0.5, 0.5)
                    self.set_plc_bit(self.devices["end_success"])
                elif outcome in ["end_fail"]:
                    print("[Festo] Pulsing end device M402 (fail group)")
                    self.pulse_bit(self.devices["start_logitech"], 0.5, 0.5)
                    self.set_plc_bit(self.devices["end_fail"])
                elif outcome in ["tray_empty"]:
                    print("[Festo] Pulsing end device M402 (fail group)")
                    self.set_plc_bit(self.devices["end"])
             
                print("[Festo] Waiting for next trigger...")
            else:
                print(f"\r[Festo] Waiting for {start_device}=1...", end="", flush=True)
                time.sleep(1)


# --- Harness to run directly ---
if __name__ == "__main__":
    worker = FestoSensorWorker()
    try:
        worker.run()
    except KeyboardInterrupt:
        print("\nStopping worker...")

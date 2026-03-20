import subprocess
import sys
import shutil
import os

def run_python_simulation():
    print("=== Step 1: Running Python Placement Algorithms ===")
    result = subprocess.run([sys.executable, "main.py"], capture_output=False)
    if result.returncode != 0:
        print("Python simulation failed!")
        sys.exit(1)

def run_ns3_simulation(mode):
    json_file = f"topology_{mode}.json"
    print(f"\n=== Step 2 & 3: Executing ns-3 Simulation for {mode.upper()} mode ===")
    
    try:
        shutil.copy(json_file, "topology.json")
    except FileNotFoundError:
        print(f"Error: {json_file} missing. Did main.py run successfully?")
        return

    # In a real environment, you run the waf/ns3 script within the ns-3 root directory
    cmd = ["./ns3", "run", "scratch/upf-sim"]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            print(f"ns-3 run failed or ./ns3 is not recognized (this is expected if not run inside the ns-3-dev folder).")
            # print(res.stderr)
        else:
            print(res.stdout)
            print("ns-3 run successful.")
            
        # Try to rename the generated outputs if they exist
        if os.path.exists("flowmon.xml"):
            shutil.move("flowmon.xml", f"flowmon_{mode}.xml")
        if os.path.exists("upf-animation.xml"):
            shutil.move("upf-animation.xml", f"{mode}.xml")
            print(f"Generated {mode}.xml for NetAnim.")
            
    except Exception as e:
        print("Could not run ./ns3, skipping ns-3 execution. Please ensure this project is placed inside the ns-3-dev folder.")

def main():
    run_python_simulation()
    
    run_ns3_simulation("static")
    run_ns3_simulation("predictive")
    
    print("\n=== Step 4 & 5: Parsing Results and Generating Plots ===")
    print("Metrics plotted by main.py -> python_metrics.png")
    
    print("\n=== DEMO HIGHLIGHTS ===")
    print("- Detailed latency and energy comparisons are visualized in python_metrics.png.")
    print("- To view NetAnim visualization, load the generated static.xml or predictive.xml (if ns-3 executed successfully).")

if __name__ == "__main__":
    main()

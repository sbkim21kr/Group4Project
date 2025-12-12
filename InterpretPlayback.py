import xml.etree.ElementTree as ET
import csv
import sys
import os

def load_playback_file(filename):
    """
    Load playback file (XML format).
    Extract waypoints: x, y, z, r, vel, accel, suction/gripper, dwell_time
    """
    try:
        if not os.path.exists(filename):
            print(f"Error: File not found at '{filename}'")
            return None

        tree = ET.parse(filename)
        root = tree.getroot()
    except ET.ParseError as e:
        print(f"Error: Failed to parse XML file '{filename}'. Details: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred while loading the file: {e}")
        return None

    waypoints = []
    for row in root:
        if row.tag.startswith("row"):  # only process rows like <row0>, <row1>, ...
            try:
                x = float(row.find("item_2").text)
                y = float(row.find("item_3").text)
                z = float(row.find("item_4").text)
                r = float(row.find("item_5").text)

                # Default vel to 50.0 if item_10 is missing
                vel = float(row.find("item_10").text) if row.find("item_10") is not None and row.find("item_10").text else 50.0
                accel = vel  # accel is set equal to vel in the original logic

                # suction/gripper is item_12
                suction_gripper = int(row.find("item_12").text) if row.find("item_12") is not None and row.find("item_12").text else 0

                # NEW: dwell time (default 1.0)
                dwell_time = 1.0

                # 8 parameters total
                wp = (x, y, z, r, vel, accel, suction_gripper, dwell_time)
                waypoints.append(wp)
            except Exception as e:
                print(f"Skipping {row.tag} due to error during data extraction: {e}")
    
    return waypoints

def show_waypoints(waypoints):
    """Prints the extracted waypoints to the console."""
    if not waypoints:
        print("\nNo waypoints to display.")
        return
    
    print("\n--- Extracted Waypoints ---")
    for i, wp in enumerate(waypoints, start=1):
        (x, y, z, r, vel, accel, sg, dwell) = wp
        print(f"Point{i:03d}: (X:{x:6.2f}, Y:{y:6.2f}, Z:{z:6.2f}, R:{r:6.2f}, Vel:{vel:5.1f}, Accel:{accel:5.1f}, Gripper:{sg}, Dwell:{dwell:4.1f})")
    print("---------------------------\n")

def export_to_csv(waypoints, original_filename):
    """Exports the waypoints to a CSV-like file in tuple format with fixed precision."""
    if not waypoints:
        print("Cannot export: Waypoints list is empty.")
        return
        
    base_name = os.path.splitext(original_filename)[0]
    csv_filename = base_name + ".csv"
    
    try:
        with open(csv_filename, 'w', newline='') as csvfile:
            for i, wp in enumerate(waypoints):
                formatted = ",".join(f"{val:.4f}" if isinstance(val, float) else str(val) for val in wp)
                # If it's the last waypoint, don't add the trailing comma
                if i == len(waypoints) - 1:
                    line = f"({formatted})\n"
                else:
                    line = f"({formatted}),\n"
                csvfile.write(line)
            
        print(f"✅ Successfully exported {len(waypoints)} waypoints to **{csv_filename}**")
        return csv_filename
    except Exception as e:
        print(f"Error writing to CSV file: {e}")
        return None


if __name__ == "__main__":
    while True:
        try:
            filename = input("📝 Please enter the XML or .playback filename (e.g., my_path.xml): ").strip()
            if not filename:
                print("Filename cannot be empty. Please try again.")
                continue

            if not (filename.lower().endswith(".xml") or filename.lower().endswith(".playback")):
                if "." not in filename:
                    print("Assuming '.xml' extension.")
                    filename += ".xml"
                else:
                    print("⚠️ Warning: File extension is neither .xml nor .playback. Attempting to load anyway.")
            break
        except EOFError:
            print("\nInput cancelled by user. Exiting.")
            sys.exit(0)
        except Exception as e:
            print(f"An error occurred during input: {e}")
            
    print(f"\nAttempting to load data from: **{filename}**")
    waypoints = load_playback_file(filename)
    
    if waypoints is not None:
        show_waypoints(waypoints)
        export_to_csv(waypoints, filename)

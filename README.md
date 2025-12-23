# VisionFlip

Multi-robot PLC and vision integration project using Dobot arms, Festo sensors, and YOLOv8 camera, with explicit PLC interlocks for pass/fail handling, threaded vision inference, and concurrent robot execution.

---

## 🚀 Overview
This project integrates **industrial robots, PLC control, and vision AI** into a single workflow.  
A Mitsubishi PLC coordinates robots and sensors via flags, while Python workers execute robot motion, sensor checks, and threaded YOLOv8 inference.  
The system enforces interlocks so robot actions and inference never conflict, while allowing multiple robots (R1, R2, R3) to run in parallel.

---

## ✨ Features
- **PLC coordination:** Uses Mitsubishi PLC flags (M400, M401, M402) to orchestrate flow and enforce interlocks.
- **Pass/fail handling:**  
  - **Pass (M401):** Festo pass → interlocks M400, executes robot motions, then clears interlock.  
  - **Fail (M402):** Festo fail → interlocks M400, triggers Logitech camera, runs YOLOv8 in a separate thread, then clears M400 after inference.
- **Threaded vision inference:** YOLOv8 runs on a separate thread so the orchestrator remains responsive while M400 stays interlocked.
- **Concurrent robot control:** R1, R2, R3 each have start/busy/end flags, allowing simultaneous execution like threads.
- **Reproducible environment:** Clean dependency management with `pyproject.toml` and `uv sync`.

---

## 🛠️ Requirements
- Python **3.13.7**
- [uv package manager](https://github.com/astral-sh/uv)
- Windows 10/11 (tested)
- NVIDIA GPU with CUDA drivers (optional, for YOLO acceleration)

---

## 📦 Installation
Clone the repository and install dependencies:

```bash
uv sync
```

---

## ▶️ Running the Project
```bash
uv run python 00main.py     # Orchestrates PLC + robots, enforces M400 interlocks
uv run python 01festo.py    # Festo sensor worker, sets M401 (pass) or M402 (fail)
uv run python 02logitech.py # Vision worker; threaded YOLOv8 on M402 fail path
```

---

## 🔄 PLC‑driven flow and interlocks

```text
          +-------------------+
          |   Mitsubishi PLC  |
          |  M400 M401 M402   |
          +-------------------+
                   |
                   | (cycle start / state flags)
                   v
        +---------------------------+
        | 00main.py Orchestrator   |
        | - Reads M400/M401/M402   |
        | - Interlocks M400        |
        | - Commands R1/R2/R3      |
        +---------------------------+
             |                 |
             |                 | (Festo read)
             |                 v
             |        +-------------------+
             |        | 01festo.py        |
             |        | Festo Sensor      |
             |        +-------------------+
             |                 |
             |      +----------+----------+
             |      |                     |
             v      v                     v
   PASS PATH (M401=1)             FAIL PATH (M402=1)
   --------------------           --------------------
   - Set M401                     - Set M402
   - Interlock M400               - Interlock M400
   - Execute R1/R2/R3             - Trigger 02logitech.py
   - Clear interlock when done    - Start YOLO thread (non-blocking)
                                   - Keep M400 interlocked during inference
                                   - On result: update PLC flags, release M400
```

---

## 🤖 Robot Start/Busy/End Devices

Each robot has **three PLC flags** to synchronize execution:

- **R1 (Robot 1):**
  - `R1_START` → PLC sets when robot should begin motion.
  - `R1_BUSY` → Robot worker sets while motion is in progress.
  - `R1_END` → Robot worker sets when motion completes; PLC clears interlock.

- **R2 (Robot 2):**
  - `R2_START` → PLC sets when robot should begin motion.
  - `R2_BUSY` → Robot worker sets while motion is in progress.
  - `R2_END` → Robot worker sets when motion completes; PLC clears interlock.

- **R3 (Robot 3):**
  - `R3_START` → PLC sets when robot should begin motion.
  - `R3_BUSY` → Robot worker sets while motion is in progress.
  - `R3_END` → Robot worker sets when motion completes; PLC clears interlock.

---

## 📊 Parallel Timeline Example

Robots can run **concurrently**, similar to threads:

```text
Time →
R1_START: |■■■■■■■■■■| END
R2_START:     |■■■■■■■■■■■■■■| END
R3_START:         |■■■■■■■■| END

Legend:
■ = Robot motion (BUSY flag high)
START = PLC raises R*_START
END   = Worker sets R*_END, clears BUSY
```

- R1 starts first, runs for a while, then ends.  
- R2 starts slightly later but overlaps with R1.  
- R3 starts even later, overlapping with both.  
- PLC monitors BUSY/END flags independently.  
- Only global interlock **M400** can pause all robots (e.g., during YOLO inference).

---

## 🖼️ Customer-Friendly Demo Diagram

For presentations and sales demos, here’s a simplified view:

```text
   +---------+       +---------+       +---------+       +-------------+
   |   PLC   | --->  | Robots  | --->  | Camera  | --->  | Dashboard   |
   +---------+       +---------+       +---------+       +-------------+

PLC decides → Robots move → Camera inspects → Dashboard shows results
```

This version avoids technical flags and focuses on the **value chain** customers care about:  
**Automation → Inspection → Insight.**

---

## 📄 License
MIT License.

---

## 👤 Author
Sangbum Kim  
Contact: sbkim21@gmail.com
```

README.md

````md id="v3whct"
# 💡 Light Puzzle Challenge

A hidden-state switch puzzle game built using Python, Tkinter, and pygame.

The player must discover the correct hidden switch configuration to turn the bulb ON. The internal states remain hidden during gameplay, making the puzzle a logic-based challenge focused on experimentation, memory, and deduction.

---

# 🎮 Features

- Interactive GUI using Tkinter
- Animated starfield background
- Hidden binary switch mechanics
- Multiple difficulty levels
- Hint system
- Reveal mode
- Score tracking system
- Persistent leaderboard using CSV
- Background music and sound effects
- Victory animations

---

# 🛠 Technologies Used

- Python 3.x
- Tkinter
- pygame
- CSV file handling

---

# 📂 Project Structure

```text
LightPuzzleChallenge/
│
├── main.py
├── requirements.txt
├── README.md
├── scores.csv
├── click.wav
├── win.wav
└── bg.mp3
````

---

# 🚀 How to Run

## 1. Clone Repository

```bash
git clone https://github.com/Ali-Hassan-63/Neon-Light-Puzzle
```

## 2. Navigate to Project Folder

```bash
cd light-puzzle-challenge
```


## 3. Run the Game

```bash
python sourcecode.py
```

---

# 🎯 Game Objective

The objective is to match the hidden target switch configuration.

* Every switch contains a hidden ON/OFF state.
* Clicking switches changes internal binary values.
* The bulb lights up only when all switch states match the hidden target configuration exactly.

---

# 🏆 Scoring System

| Action        | Effect     |
| ------------- | ---------- |
| Switch Click  | -5 Points  |
| Hint Usage    | -50 Points |
| Puzzle Solved | +200 Bonus |

Players are encouraged to solve the puzzle using the fewest clicks and hints possible.



---

# 📄 License

This project is developed for academic and educational purposes.

---

# 👨‍💻 Author
Syed Ali Hassan    
    Developed as a Python GUI puzzle game project using Tkinter and pygame.


````

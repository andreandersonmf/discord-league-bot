# 🏐 Discord League Management Bot

A Discord bot built in **Python** to manage a competitive **Roblox Volleyball League** server.  
It automates roster changes, transaction requests, role sync, and league operations to reduce manual work and keep everything organized.

---

## ✨ Highlights

- Real-world project used for league management
- Clear business rules (Captain/Vice Captain permissions)
- Database-driven roster and transactions
- Consistent embeds for better UX inside Discord

---

## 🚀 Features

- Transaction system (add / remove / transfer requests)
- Roster management per team (database)
- Role synchronization (Captain / Vice Captain / Player)
- Permission control by role (and admin overrides)
- Custom embeds for success/error feedback
- Optional: Match scheduling and result posting modules

---

## 🧰 Tech Stack

- Python  
- discord.py  
- SQLAlchemy  
- SQLite (can be adapted to PostgreSQL)

---

## 🔐 Environment Variables

Create a `.env` file based on `.env.example`:

```env
DISCORD_TOKEN=your_token_here
```

---

## ▶️ How to Run Locally

```bash
# 1) Create virtual environment
python -m venv .venv

# 2) Activate (Windows - Git Bash)
source .venv/Scripts/activate

# 3) Install dependencies
pip install -r requirements.txt

# 4) Run the bot
python bot.py
```

---

## 📌 Permission Rules (Summary)

- Captains / Vice Captains → Can request roster transactions for their own team  
- Admins → Full access and overrides  
- Optional Referee/Media roles → Post match results  

---

## 📷 Demo

Add screenshots or GIFs here showing:

- Transaction request embed  
- Successful transfer embed  
- Permission error embed  
- Roster display  

---

## 🗺️ Roadmap (Next Improvements)

- Add transaction approval logs (audit trail)
- Add unit tests for permission rules
- Docker deployment guide
- Improve validation and edge-case handling

---

Developed by **André Anderson**

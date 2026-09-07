# Alternative & Metal Releases (AMR)

A comprehensive music release tracking and management system for Alternative & Metal music. This project automates the process of discovering, cataloging, and publishing information about new and upcoming music releases from various streaming platforms.

## 🎯 Features

- **New Releases Tracking**: Automatically fetches and catalogs new album releases weekly
- **Coming Soon Alerts**: Tracks upcoming releases with advance notifications
- **Multi-Platform Support**: Integrates with Apple Music, Yandex.Music, and Zvuk.com
- **Telegram Integration**: Sends automated updates to Telegram channels with categorized topics
- **Cover Art Management**: Downloads and organizes album cover artwork
- **Database Management**: SQLite-based storage with automatic backup functionality
- **Smart Recommendations**: AI-powered release type classification
- **Static Website Generation**: Creates HTML pages organized by year/month

## 📁 Project Structure

```
├── Python Scripts/          # All automation scripts
│   ├── AMR_NewReleases.py   # Weekly new releases processor
│   ├── AMR_LookApp.py       # Apple Music Lookup API integration
│   ├── AMR_ZVYM.py          # Yandex.Music & Zvuk lookup
│   ├── AMR_Recommender.py   # Release recommendation engine
│   ├── AMR_CoversDownloader.py  # Cover art downloader
│   ├── AMR_CoversRenamer.py     # Cover art organizer
│   ├── AMR_DB_Backup.py     # Database backup utility
│   ├── amr_functions.py     # Shared utility functions
│   └── requirements.txt     # Python dependencies
├── Website/                 # Generated static website
│   ├── index.html           # Main page
│   ├── Resources/           # CSS, favicons, icons
│   └── AMRs/                # Release pages by year
│       ├── 2022/
│       ├── 2023/
│       ├── 2024/
│       ├── 2025/
│       └── 2026/
├── Databases/               # SQLite database and backups
│   ├── music_releases.db    # Main database
│   └── Backups/             # JSON backups of database tables
├── .github/workflows/       # GitHub Actions CI/CD
└── status.log               # Execution logs
```

## 🛠️ Scripts Overview

### Core Scripts

| Script | Purpose |
|--------|---------|
| `AMR_NewReleases.py` | Processes new releases, updates database, generates HTML pages, sends Telegram notifications |
| `AMR_LookApp.py` | Uses Apple Music Lookup API to fetch release metadata and cover art |
| `AMR_ZVYM.py` | Searches for releases on Yandex.Music and Zvuk.com platforms |
| `AMR_Recommender.py` | Classifies releases by type using AI recommendations |

### Utility Scripts

| Script | Purpose |
|--------|---------|
| `AMR_CoversDownloader.py` | Downloads high-resolution cover art for new releases |
| `AMR_CoversRenamer.py` | Organizes and renames cover files with standardized naming |
| `AMR_DB_Backup.py` | Exports database tables to JSON backup files |
| `amr_functions.py` | Shared utilities: Telegram messaging, logging, database operations |

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- pip package manager
- SQLite3
- Telegram Bot Token
- Yandex.Music API Token (optional)
- Zvuk.com API Token (optional)

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/mushroomoff/mushroomoff.github.io.git
   cd mushroomoff.github.io
   ```

2. **Install dependencies**:
   ```bash
   cd "Python Scripts"
   pip install -r requirements.txt
   ```

3. **Configure environment variables**:
   Create a `.env` file in the root directory:
   ```env
   tg_token=YOUR_TELEGRAM_BOT_TOKEN
   tg_channel_id=YOUR_CHANNEL_ID
   tg_logger_id=YOUR_LOGGER_CHAT_ID
   ym_token=YOUR_YANDEX_MUSIC_TOKEN
   zv_token=YOUR_ZVUK_TOKEN
   ```

### Configuration

Edit the `ROOT_FOLDER` variable in each script to match your local path:
```python
ROOT_FOLDER = '/your/path/to/repository/'
```

For GitHub Actions, this is automatically set to empty string.

## ⚙️ GitHub Actions Workflows

### AMR Weekly Update
- **Schedule**: Every Friday at 07:00 Moscow time
- **Actions**:
  - Runs `AMR_LookApp.py` to fetch Apple Music data
  - Runs `AMR_NewReleases.py` to process new releases
  - Commits and pushes changes automatically

### AMR Recommender
- **Trigger**: On push to main branch when AMR files change
- **Actions**:
  - Runs `AMR_Recommender.py` to classify new releases
  - Commits and pushes updates

## 📊 Database Schema

The SQLite database (`music_releases.db`) contains the following tables:

- **artists**: Artist information and metadata
- **my_releases**: Personal collection tracking
- **new_releases**: Newly discovered releases
- **soon_releases**: Upcoming releases

Each table stores release information including artist names, album titles, release dates, cover art URLs, and platform links.

## 🌐 Website

The project generates a static website with:
- **Main Page** (`Website/index.html`): Overview and navigation
- **Monthly Archives** (`Website/AMRs/YYYY/AMR YYYY-MM.html`): Detailed release listings
- **Resources**: CSS stylesheets, favicons, and touch icons

## 📱 Telegram Integration

Messages are sent to organized topics:
- **New Updates** (ID: 6)
- **Top Releases** (ID: 10)
- **Coming Soon** (ID: 3)
- **New Releases** (ID: 2)
- **Next Week Releases** (ID: 80)
- **General** (ID: 0)

## 🔧 Usage Examples

### Run New Releases Processor
```bash
cd "Python Scripts"
python AMR_NewReleases.py
```

### Backup Database
```bash
python AMR_DB_Backup.py
```

### Download Covers
```bash
python AMR_CoversDownloader.py
```

## 📦 Dependencies

- **requests** (>=2.32.5): HTTP library for API calls
- **pandas** (>=2.3.3): Data manipulation and analysis
- **python-dotenv** (>=1.0.0): Environment variable management
- **yandex-music** (>=2.2.0): Yandex.Music API client

## 📝 Logging

All scripts log to `status.log` with timestamps and script identifiers. Log entries include:
- Execution start/end times
- Processing statistics
- Error messages and tracebacks
- Telegram notification status

## 🤝 Contributing

This is a personal automation project. Feel free to fork and adapt for your own music tracking needs.

## 📄 License

This project is for personal use. Please respect API terms of service for Apple Music, Yandex.Music, and Zvuk.com.

## 🆘 Troubleshooting

### Common Issues

1. **API Token Errors**: Verify tokens in `.env` file are valid and not expired
2. **Database Lock**: Ensure no other process is accessing `music_releases.db`
3. **Path Issues**: Check `ROOT_FOLDER` paths match your system
4. **Telegram Rate Limits**: Implement delays if sending many messages

### Debug Mode

Add print statements or check `status.log` for detailed execution information.

---

**Version**: 2.026.07  
**Last Updated**: 2025  
**Author**: mushroomoff

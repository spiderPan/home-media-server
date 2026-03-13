# Home Media Server Stack

A pre-configured, dockerized media server stack featuring media management, automated downloads, and a beautiful dashboard. Now updated to support external disk storage and automatic Chinese subtitles!

## 🚀 Included Services

- **[Plex](https://www.plex.tv/)**: Media streaming and organization.
- **[Radarr](https://radarr.video/)**: Automatic movie discovery and downloading.
- **[Sonarr](https://sonarr.tv/)**: Automatic TV show discovery and downloading.
- **[Bazarr](https://www.bazarr.media/)**: Subtitle manager (best for automatic Chinese captions).
- **[Prowlarr](https://prowlarr.com/)**: Indexer manager for torrent trackers.
- **[qBittorrent](https://www.qbittorrent.org/)**: Lightweight BitTorrent client.
- **[FlareSolverr](https://github.com/FlareSolverr/FlareSolverr)**: Proxy server to bypass Cloudflare protection.
- **[Homepage](https://gethomepage.dev/)**: A highly customizable dashboard for your server.

---

## 🛠️ Prerequisites

- **Docker** and **Docker Compose** installed on your host system.
- Basic knowledge of Linux terminal commands.

---

## 📦 Setup Instructions

### 1. Clone the Repository
```bash
git clone https://github.com/spiderPan/home-media-server.git
cd home-media-server
```

### 2. Configure Environment Variables
Copy the example environment file and edit it with your specific values:
```bash
cp .env.example .env
nano .env
```

**Key variables to set:**
- `MEDIA_DISK`: The absolute path to your external drive (e.g., `/media/user/MyPassport`).
- `PUID` & `PGID`: Run `id` in your terminal to find your user and group IDs.
- `PLEX_CLAIM`: Get your token from [plex.tv/claim](https://www.plex.tv/claim/).
- `TZ`: Set your timezone (e.g., `Europe/London`).

### 3. Initialize Dashboard Configuration
Homepage requires its service configuration. Use the provided template:
```bash
cp config/homepage/services.yaml.example config/homepage/services.yaml
```

### 4. Start the Stack
Run the following command to start all services in the background:
```bash
docker-compose up -d
```

---

## 🌐 Accessing Your Services

Once the stack is running, you can access your services at the following ports:

| Service | Port | URL |
| :--- | :--- | :--- |
| **Homepage** | `80` | [http://localhost](http://localhost) |
| **Plex** | `32400` | [http://localhost:32400/web](http://localhost:32400/web) |
| **Radarr** | `7878` | [http://localhost:7878](http://localhost:7878) |
| **Sonarr** | `8989` | [http://localhost:8989](http://localhost:8989) |
| **Bazarr** | `6767` | [http://localhost:6767](http://localhost:6767) |
| **Prowlarr** | `9696` | [http://localhost:9696](http://localhost:9696) |
| **qBittorrent** | `8080` | [http://localhost:8080](http://localhost:8080) |

---

## 📂 Storage Structure (on External Disk)

The stack expects the following structure on your `${MEDIA_DISK}`:
- `/media-server/data/media/movies`: Movie Library.
- `/media-server/data/media/tv`: TV Library.
- `/media-server/data/torrents`: Active download storage.

---

## 🔒 Security Note

**Never commit your `.env` file or actual config files to GitHub.** They contain sensitive API keys and passwords. 

---

## 🤝 Contributing

Feel free to open issues or submit pull requests to improve the stack!

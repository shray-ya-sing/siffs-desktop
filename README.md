# Siffs - Fast File Search Desktop Application

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Platform: Windows](https://img.shields.io/badge/Platform-Windows%20x64-lightgrey.svg)](https://github.com/shray-ya-sing/siffs-desktop)

**Siffs** is a powerful search engine designed for intelligently searching vast corpuses of PowerPoint presentations. Search thousands of presentations in seconds and retrieve the exact slides you're looking for with precision.


## Quick Start

### Download & Installation

#### Option 1: Official Website
Download the latest installer from [www.fastfilesearch.com](https://www.fastfilesearch.com)

#### Option 2: GitHub Releases  
Download from [GitHub Releases](https://github.com/shray-ya-sing/siffs-desktop/releases)

### System Requirements

- **OS**: Windows x64
- **RAM**: 4GB minimum (8GB recommended)
- **Storage**: 500MB free space
- **Internet**: Required for initial setup and authentication

### Installation Steps

1. **Download** the installer from one of the sources above
2. **Run** the installer as Administrator (if prompted)
3. **Follow** the installation wizard
4. **Launch** Siffs from your desktop or Start menu

### First-Time Setup

1. **Create Account** - Sign up with your email address (required)
2. **Verify Email** - Check your inbox and verify your account
3. **Connect Folders** - Point Siffs to your PowerPoint presentation folders
4. **Index Files** - Let Siffs analyze your presentations (this may take some time for large collections)
5. **Start Searching!** - Begin finding slides instantly

## Usage

### Basic Search
1. Open Siffs
2. Type your search query in the search bar
3. Hit `Enter` or click search

## Configuration

### Connecting Folders
1. Click the "New Folder" button in the sidebar
2. Enter or browse to your presentation folder path
3. Wait for indexing to complete
4. Folders are automatically saved for future sessions

## Development

### Building from Source

```bash
# Clone the repository
git clone https://github.com/shray-ya-sing/siffs-desktop.git
cd siffs-desktop

# Install dependencies
npm install

# Install Python dependencies
cd src/python-server
pip install -r requirements.txt

# Start development
npm run start
```

## FAQ

### General

**Q: What file types does Siffs support?**  
A: Currently, Siffs is optimized for PowerPoint presentations (.pptx files).

**Q: Do I need PowerPoint installed?**  
A: No, Siffs works independently and doesn't require PowerPoint to be installed.

**Q: Is there a cost to use Siffs?**  
A: Siffs is free to use, but requires account registration.

### Setup & Installation

**Q: Why is setup taking so long?**  
A: Initial indexing can take time depending on the number and size of your presentations. This is normal for large document collections.

**Q: Can I use Siffs offline?**  
A: After initial setup and authentication, Siffs works offline for searching your indexed presentations.

### Privacy & Data

**Q: Where is my data stored?**  
A: All your presentation data and search indexes are stored locally on your computer.

**Q: What data does Siffs access?**  
A: Siffs only reads presentation content to create searchable indexes. No personal data is collected beyond account registration.

## Contributing

We welcome contributions! Please feel free to submit issues or pull requests.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## Support

- **Website**: [www.fastfilesearch.com](https://www.fastfilesearch.com)
- **GitHub Issues**: [Report bugs or request features](https://github.com/shray-ya-sing/siffs-desktop/issues)
- **Email**: github.suggest277@passinbox.com

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

---

© 2025 Siffs. All rights reserved.

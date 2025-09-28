# 🐘 PgMallowDB - PostgreSQL Web Manager

A sleek, web-based PostgreSQL database management tool built with Flask.

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-2.0+-green.svg)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Supported-blue.svg)

## ✨ Features

- **📊 Dashboard Overview** - Database stats, table sizes, and connection info
- **🗂️ Table Management** - Browse, view, and manage all your tables
- **⚡ SQL Editor** - Execute custom queries with real-time results
- **📤 Export Data** - Download table data as CSV
- **🔧 Data Operations** - Insert new records and manage existing data
- **🎯 Clean UI** - Simple, intuitive interface for database operations

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- PostgreSQL database
- `DATABASE_URL` environment variable

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/42Wor/PgMallowDB.git
cd PgMallowDB
```

2. **Install dependencies**
```bash
pip install flask psycopg2-binary pandas
```

3. **Set up environment**
```bash
export DATABASE_URL="postgresql://username:password@host:port/database"
```

4. **Run the application**
```bash
python main.py
```

5. **Open your browser**
```
http://localhost:5000
```

## 🛠️ Usage

### Dashboard
- View database size, table counts, and active connections
- Quick access to all tables with row counts and sizes

### Table Explorer
- Browse all tables in your database
- View table structures and column information
- Paginated data viewing with customizable page sizes

### SQL Editor
- Execute any SQL query directly
- Real-time results for SELECT queries
- Support for INSERT, UPDATE, DELETE operations

### Data Management
- Export table data to CSV
- Insert new records through web forms
- Safe data deletion with confirmation prompts

## 🔧 Configuration

Set your database connection via environment variable:

```bash
export DATABASE_URL="postgresql://user:pass@localhost:5432/mydb"
```

Or create a `config.py` file:
```python
DATABASE_URL = "postgresql://user:pass@localhost:5432/mydb"
```

## 📁 Project Structure

```
PgMallowDB/
├── main.py                 # Main application file
├── templates/            # HTML templates
│   ├── index.html        # Dashboard
│   ├── tables.html       # Table list
│   ├── table_data.html   # Table data view
│   ├── sql_editor.html   # SQL query interface
│   └── ...
└── README.md
```

## 🔒 Security Notes

- ⚠️ **Production Warning**: This tool provides direct database access
- 🔑 Change the default secret key in production
- 🔒 Use in secure environments only
- 📝 Consider adding authentication for production use

## 🤝 Contributing

Contributions welcome! Feel free to:
- Report bugs
- Suggest new features
- Submit pull requests

## 👨‍💻 Author

**Maaz Waheed**
- GitHub: [@42Wor](https://github.com/42Wor)
- Email: maaz.waheed@mbktechstudio.com

## 📄 License

This project is open source and available under the [MIT License](LICENSE).

---

**⭐ Star this repo if you find it useful!**
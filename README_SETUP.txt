ONLINE COURSE REGISTRATION SYSTEM — ONE FILE VERSION
====================================================

This version is designed to be easy to start from VS Code without Eclipse,
Tomcat, Maven, MySQL, or third-party Python packages.

REQUIREMENT
-----------
Python 3.10 or newer.
Download: https://www.python.org/downloads/
During Windows installation, tick "Add python.exe to PATH".

HOW TO RUN
----------
1. Extract this ZIP file.
2. Open the extracted folder in VS Code.
3. Open Terminal > New Terminal.
4. Run one of these commands:

Windows:
    py app.py

Or:
    python app.py

macOS/Linux:
    python3 app.py

5. The browser should open automatically. If it does not, open:
    http://127.0.0.1:5000

6. Register a student account, log in, register for a course, and open My Dashboard.

DATABASE
--------
The SQLite database file `course_registration.db` is created automatically in
the same folder when the app starts. Course data is inserted automatically.

IMPORTANT
---------
- Keep the terminal open while using the website.
- Stop the app with Ctrl+C in the terminal.
- This is a local educational demo, not a production-ready public website.
- It uses Python's built-in HTTP server and SQLite for easy setup.
- Sessions are stored in memory and will end when the app restarts.

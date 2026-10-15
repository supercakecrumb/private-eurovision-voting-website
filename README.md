# Private Eurovision Voting Website

A web application for Eurovision Song Contest enthusiasts to vote for their favorite performances and view rankings.

## Overview

Private Eurovision Voting Website is a Flask-based web application that allows users to:
- Log in with a simple username
- Vote for Eurovision performances across different stages (Semi-finals and Final)
- View rankings based on all users' votes
- Track their own voting history

## Features

- **Simple Authentication**: Users can log in with just a username
- **Multiple Stages**: Support for Semi-final 1, Semi-final 2, and Final stages
- **Voting System**: Grade performances from 1-12 points (Eurovision style)
- **Real-time Rankings**: View current standings based on all votes
- **Responsive Design**: Mobile-optimized UI that works seamlessly on all devices
- **CSV Data Import**: Paste CSV data to populate the database with Eurovision contestants

## Technical Stack

- **Backend**: Python 3.12 with Flask framework
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Frontend**: HTML, Bootstrap 5.1.3
- **Containerization**: Docker and Docker Compose for easy deployment

## Project Structure

```
private-eurovision-voting-website/
├── app/                      # Application package
│   ├── __init__.py           # Flask app initialization
│   ├── db_init.py            # Database initialization module
│   ├── forms.py              # WTForms definitions
│   ├── models.py             # SQLAlchemy database models
│   ├── routes.py             # Flask routes and view functions
│   └── templates/            # Jinja2 HTML templates
│       ├── base.html         # Base template with common elements
│       ├── index.html        # Login and stage selection page
│       └── stage.html        # Voting and rankings page
├── data/                     # Local storage directory (for SQLite if used)
├── .env.example              # Example environment variables configuration
├── docker-compose.yml        # Docker Compose configuration with PostgreSQL
├── Dockerfile                # Docker container definition
├── fill_db.py                # Script to populate the database with initial data
├── README.md                 # Project documentation
└── requirements.txt          # Python dependencies
```

## Installation and Setup

### Local Development

1. Clone the repository:
   ```
   git clone https://github.com/supercakecrumb/private-eurovision-voting-website.git
   cd private-eurovision-voting-website
   ```

2. Create a virtual environment and install dependencies:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Set up a PostgreSQL database or use SQLite for development:
   
   **Option 1: Use SQLite (easier for development)**
   ```
   mkdir data  # Create a data directory for the SQLite database
   ```
   
   **Option 2: Use PostgreSQL (recommended for production-like environment)**
   ```
   # Install PostgreSQL on your system
   # Create a database named 'eurovision'
   # Set the DATABASE_URL environment variable to point to your PostgreSQL database
   ```

4. Create a `.env` file with your configuration:
   ```
   # Database connection (use one of these)
   # For SQLite:
   DATABASE_URL=sqlite:///data/my-eurovision-table.db
   # For PostgreSQL:
   # DATABASE_URL=postgresql://username:password@localhost:5432/eurovision
   
   # Auto-initialization
   AUTO_INIT_DB=1
   USE_REAL_EUROVISION_DATA=1
   
   # Security
   SECRET_KEY=your_development_secret_key
   ```

5. Run the application:
   ```
   flask run
   ```
   
   The application will automatically initialize the database if `AUTO_INIT_DB=1` is set.
   
   Alternatively, you can manually initialize the database:
   ```
   python fill_db.py
   ```

6. Access the application at http://localhost:5000

### Docker Deployment

#### Option 1: Using Docker Compose (Local Build)

1. Clone the repository:
   ```
   git clone https://github.com/supercakecrumb/private-eurovision-voting-website.git
   cd private-eurovision-voting-website
   ```

2. (Optional) Create a `.env` file to override environment variables:
   ```
   # Database connection
   DATABASE_URL=postgresql://postgres:postgres@db:5432/eurovision
   
   # Auto-initialization
   AUTO_INIT_DB=1
   USE_REAL_EUROVISION_DATA=1
   
   # Security
   SECRET_KEY=your_secure_secret_key_here
   ```

3. Build and run using Docker Compose:
   ```
   docker-compose up -d
   ```

4. Access the application at http://localhost:5024

#### Option 2: Using Pre-built Image from GitHub Container Registry

1. Create a `docker-compose.yml` file:
   ```yaml
   version: '3.8'
   
   services:
     web:
       image: ghcr.io/supercakecrumb/private-eurovision-voting-website:1.0.0  # Use a specific version tag
       ports:
         - "5024:5000"
       environment:
         - DATABASE_URL=postgresql://postgres:postgres@db:5432/eurovision
         - AUTO_INIT_DB=1
         - USE_REAL_EUROVISION_DATA=1
         - SECRET_KEY=your_secure_secret_key_here
       depends_on:
         - db
   
     db:
       image: postgres:15
       environment:
         - POSTGRES_USER=postgres
         - POSTGRES_PASSWORD=postgres
         - POSTGRES_DB=eurovision
       volumes:
         - postgres_data:/var/lib/postgresql/data
   
   volumes:
     postgres_data:
   ```

2. Pull and run the containers:
   ```
   docker-compose up -d
   ```

3. Access the application at http://localhost:5024

The application will automatically:
- Set up a PostgreSQL database
- Initialize the database with Eurovision data (if `AUTO_INIT_DB=1` is set)
- Use real Eurovision 2023 data (if `USE_REAL_EUROVISION_DATA=1` is set)

#### Database Persistence

PostgreSQL data is stored in a Docker volume (`postgres_data`), ensuring your data persists across container restarts.

## Usage

1. Log in with your username on the homepage
2. Select a stage (Semi-final 1, Semi-final 2, or Final)
3. Vote for each country's performance by assigning points (1-12)
4. View the current rankings in the Rankings tab
5. View other users' votes by clicking on their usernames

### Importing Data from CSV

1. Log in to the application
2. Click on the "Fill DB" button in the navigation bar
3. Select the stage you want to import data for (Semi-final 1, Semi-final 2, or Final)
4. Paste CSV data with the following format:
   ```
   country,artist,song
   Sweden,Loreen,Tattoo
   Finland,Käärijä,Cha Cha Cha
   ...
   ```
5. Review the preview of the data
6. Click "Confirm and Save to Database" to import the data

You can copy a sample CSV format from the Fill Database page with a single click.

## Recent Improvements

### Bug Fixes

1. **Contestant Ordering**: Countries are now sorted by their total score in both the voting and rankings tabs.
2. **Routing Fix**: Corrected redirects to non-existent 'login' route to properly redirect to 'index'.
3. **Type Conversion**: Added proper type conversion and validation for grade values.
4. **Security Enhancement**: Replaced hardcoded secret key with environment variable and secure random fallback.
5. **Flash Messages**: Added flash message display to the base template for better user feedback.
6. **Code Cleanup**: Fixed duplicate import in fill_db.py.

### UI Enhancements

1. **Modern Design**: Implemented a modern, Eurovision-themed design with custom colors and styling.
2. **Responsive Layout**: Fully optimized mobile experience with no horizontal scrolling.
3. **Visual Hierarchy**: Enhanced visual hierarchy with cards, shadows, and spacing.
4. **Interactive Elements**: Added hover effects and transitions for a more interactive feel.
5. **Icons**: Integrated Font Awesome icons throughout the interface for visual cues.
6. **Rankings Visualization**: Added special styling for top 3 ranked countries with crown, award, and medal icons.
7. **Improved Navigation**: Enhanced navigation with back buttons and clearer tab interfaces.

### Data Enhancements

1. **Real Eurovision Data**: Added support for real Eurovision 2023 data through an environment variable (`USE_REAL_EUROVISION_DATA=1`).
2. **Auto-Initialization**: Added automatic database initialization with the `AUTO_INIT_DB=1` environment variable.
3. **Docker Integration**: Integrated environment variables in docker-compose.yml for easy deployment with real data.
4. **Testing Mode**: Implemented a testing mode with comprehensive data from previous Eurovision contests.
5. **Improved Feedback**: Enhanced console output during database initialization for better visibility.
6. **GitHub Actions**: Added automated Docker image building and publishing to GitHub Container Registry.
7. **CSV Import**: Added a user-friendly interface for importing Eurovision contestant data by pasting CSV content.
8. **Mobile Optimization**: Enhanced mobile experience with optimized tables, compact buttons, and responsive text sizing.

## Remaining Limitations

- **Authentication**: The login system is very basic with no password protection.
- **Data Persistence**: The SQLite database is stored in a Docker volume. For production, consider using a more robust database solution.
- **Form Validation**: The grade input validation in the form (0-12) doesn't match the HTML input (1-12).

## Future Improvements

- Add proper user authentication with passwords
- Implement user profiles with voting history
- Add admin interface for managing stages and countries
- Implement real-time updates using WebSockets
- Add more detailed statistics and visualizations
- Improve error handling and user feedback
- Set up comprehensive CI/CD pipeline with testing

## License

© 2024 Aurorass. All rights reserved.

## CI/CD with GitHub Actions

This project uses GitHub Actions for continuous integration and delivery:

1. **Automated Docker Builds**: Every new Git tag (v*.*.* format) triggers a build of the Docker image
2. **Container Registry**: Images are automatically pushed to GitHub Container Registry (ghcr.io)
3. **Versioned Tags**: Images are tagged with semantic version from Git tags
4. **GitHub Releases**: Automatically creates a GitHub release for each new tag

To use the GitHub Actions workflow:

1. Fork or clone this repository
2. Create and push a new tag to trigger the workflow:
   ```
   git tag v1.0.0
   git push origin v1.0.0
   ```
3. The workflow will automatically build the Docker image, push it to ghcr.io, and create a GitHub release

The workflow file is located at `.github/workflows/docker-build.yml`
### Administrative access

Database imports, clearing stage entries, and order changes require HTTP Basic
administrator authentication in addition to the voting session. Set
`ADMIN_USERNAME` and a random `ADMIN_PASSWORD` of at least 24 characters through
the deployment secret manager. Serve the app over HTTPS. An unset password
disables administrative routes. Browser forms and AJAX requests use CSRF tokens.
For local HTTP development only, set `SESSION_COOKIE_SECURE=false`.

Voting remains a shared nickname-based party activity: nicknames are not verified
identities, and votes remain visible to other participants. Do not use that guest
flow as administrative authentication.

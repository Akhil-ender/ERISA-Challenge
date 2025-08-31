# ERISA Claims Management System

A modern web application for managing ERISA claims with advanced filtering, flagging, and note-taking capabilities.

## Features

- **Claims Management**: View, filter, and manage insurance claims
- **Enhanced Dashboard**: Advanced statistics including total flagged claims and average underpayment
- **CSV Data Management**: Upload new CSV files with append/overwrite options and export functionality
- **User Authentication**: Simple login system with user-specific annotations and activity tracking
- **Interactive UI**: Built with HTMX and Alpine.js for responsive interactions
- **User-Generated Data**: Add flags, notes, and comments to claims with user tracking
- **Real-time Updates**: Live search and status updates
- **Modern Design**: Bootstrap-based responsive UI
- **Admin Interface**: Django admin for data management

## Tech Stack

- **Backend**: Python with Django 5.2+
- **Database**: SQLite (lightweight, no setup required)
- **Frontend**: HTML/CSS with HTMX and Alpine.js
- **Styling**: Bootstrap 5.3 CSS framework

## Quick Start

### Prerequisites

- Python 3.11+
- Conda (for environment management)

### Installation

1. **Create and activate conda environment:**
   ```bash
   conda create -n erisa_challenge python=3.11 -y
   conda activate erisa_challenge
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run database migrations:**
   ```bash
   python manage.py migrate
   ```

4. **Create a superuser (optional):**
   ```bash
   python manage.py createsuperuser
   ```

5. **Start the development server:**
   ```bash
   python manage.py runserver
   ```

6. **Visit the application:**
   - Main application: Will run on Port 8000
   - Admin interface: /admin/
   - Login/Register: /login/ or /register/

## Data Structure

### Claim List Fields (Table view data)
- `id` (Claim ID)
- `patient_name`
- `billed_amount`
- `paid_amount`
- `status` (pending, approved, denied, processing, review)
- `insurer_name`
- `discharge_date`

### Claim Detail Fields (Detailed view data)
- `id` (Detail ID)
- `cpt_codes` (comma-separated)
- `denial_reason`

### User-Generated Data
- **Flags**: Users can flag claims for review with reasons
- **Notes**: Custom annotations and comments
- **Timestamps**: When flags/notes were created
- **User ID**: Who created the flag/note

## Application Structure

```
erisa_challenge/
├── claims/                 # Main Django app
│   ├── models.py          # Data models (Claim, ClaimDetail, ClaimNote, ClaimFlag)
│   ├── views.py           # View functions with HTMX endpoints
│   ├── urls.py            # URL routing
│   ├── admin.py           # Admin interface configuration
│   └── templates/claims/  # HTML templates
│       ├── base.html      # Base template with HTMX/Alpine.js
│       ├── dashboard.html # Dashboard with statistics
│       ├── claim_list.html# Claims list with filtering
│       └── claim_detail.html # Detailed claim view
├── erisa_claims/          # Django project settings
├── manage.py              # Django management script
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

## Key Features Explained

### 1. Dashboard
- Summary statistics and charts
- Quick access to different claim views
- Recent claims overview

### 2. Claims List
- Paginated table view with 25 claims per page
- Search by patient name, insurer, or claim ID
- Filter by status and flag status
- Toggle between table and card views
- Quick status updates and flagging

### 3. Claim Detail View
- Complete claim information
- CPT codes display
- Notes and comments system
- Flag management with reasons
- Metadata and audit trail

### 4. Interactive Features
- **HTMX**: Live updates without page reload
- **Alpine.js**: Client-side reactivity
- **Real-time search**: Instant results as you type
- **Status updates**: Click to change claim status
- **Flag toggling**: One-click flag/unflag with reasons

### 5. User Management
- User tracking for all modifications
- Timestamps for all changes
- Audit trail for flags and notes
- User registration and authentication
- User-specific activity profiles

### 6. Enhanced Dashboard Features
- **Financial Analytics**: Total underpayment calculations and averages
- **Top Insurers**: Analysis by claim count and payment ratios
- **Denial Analytics**: Breakdown of denial reasons and statistics
- **Recent Activity**: Real-time feed of notes and flags
- **Monthly Trends**: Claims volume and financial trends

### 7. CSV Data Management
- **Upload Interface**: Web-based CSV file upload with validation
- **Append/Overwrite Modes**: Choose to add to existing data or replace it
- **File Validation**: Automatic CSV structure and format checking
- **Export Functionality**: Download current data in CSV format
- **Progress Tracking**: Real-time import progress and error reporting

## Development

### Adding Sample Data

Use the Django admin interface to add sample claims:

1. Go to http://127.0.0.1:8000/admin/
2. Navigate to Claims > Claims
3. Add new claims with the required fields

### Customizing

- **Models**: Modify `claims/models.py` for data structure changes
- **Views**: Update `claims/views.py` for business logic
- **Templates**: Customize HTML in `claims/templates/claims/`
- **Styling**: Update CSS in `base.html` template

### API Endpoints

The application includes HTMX endpoints for:
- `/claims/{id}/toggle-flag/` - Toggle claim flag status
- `/claims/{id}/add-note/` - Add notes to claims
- `/claims/{id}/update-status/` - Update claim status
- `/search/` - Live search functionality

## Production Deployment

For production deployment:

1. Set `DEBUG = False` in settings
2. Configure a production database (PostgreSQL recommended)
3. Set up static file serving
4. Configure environment variables for secrets
5. Use a production WSGI server (gunicorn, uWSGI)

## License

This project is developed for the ERISA challenge and is for demonstration purposes.

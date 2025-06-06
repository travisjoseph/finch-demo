# Finch Demo

This project is a submission for the DSE Role.

> Tested on Python 3.10.12 and assumes you have venv installed.


## Usage
1. Clone the repo
2. Add your envirnement variables in a `.env.local` file (an example file has been provided). Credentials can be found [here](https://dashboard.tryfinch.com/), after creating an account.
3. On the Dasbhaord, add `http://localhost:5000/authorize` to your Redirect URIs.
4. Set up a vitual enviroment
```
python3 -m venv venv
source venv/bin/activate
```
4. Install requirements
```
pip install -r requirements.txt
```
5. Launch the application
```
python3 app.py
```
6. Navigate to `localhost:5000` in your browser to start connecting to providers.

The app should be running on `localhost:5000`. If it is not, please update the `REDIRECT_URI` in `.env.local` and on the Dashboard accordingly.
You can use demo credentials found [here](https://developer.tryfinch.com/implementation-guide/Test/Finch-Sandbox#simulating-credential-flows) in order to connect to providers in Connect.


## Features
- After connecting a provider, displays company information. 
- Users can navigate to the employee directory which lists out all employees.
- Selecting an employee from the directory will display individual (personal) and employment information.
- If a provider does not support a specific field (`null`or `None`), it will display as *unavailable*.
- If a provider does not support an endpoint, a custom *unsupported for provider* error is displayed.
- Connect scopes are limited to the endpoints required for this demo.
- This app stores tokens in a `.csv` locally. **This is not inteded for production use**. If the `tokens.csv` file does not exist, the app will create one. If multiple providers are connected, the applicaiton will fetch data from the most recent connected provider by default.

## Changelog

### Comprehensive Payroll Integration and Enhanced Search
- **Full Payroll Data Access**: Added complete payroll integration with payment and pay statement endpoints
- **Employee Payments Tab**: New Payments tab in employee drawer displays detailed payroll information including:
  - Payment summaries with date ranges and totals
  - Detailed pay statements with gross/net pay, hours, and payment methods
  - Color-coded breakdowns for earnings (blue), taxes (yellow), deductions (pink), and employer contributions (green)
  - Proper currency formatting and error handling for unsupported providers
- **Smart Reauthentication System**: Intelligent payroll scope management with:
  - "Add Payroll" buttons that appear only when payroll scopes are missing
  - "✓ Payroll" indicators for connections that already have payroll permissions
  - Seamless reauthentication flow that updates existing connections instead of creating duplicates
  - Automatic scope detection and visual feedback
- **Enhanced Employee Search**: Upgraded search functionality to include:
  - Employee ID search capability for cross-referencing payment data
  - Name and department search (existing functionality)
  - Updated placeholder text to reflect expanded search capabilities
- **Production-Ready Architecture**: Clean, professional implementation with:
  - Comprehensive API endpoints for employee payment data (`/api/employee/<id>/payments`)
  - Proper error handling and loading states throughout
  - Removed all debug endpoints and temporary development tools
  - Responsive design that works seamlessly on mobile and desktop

### Streamlined Home Page Navigation
- **Removed Redundant Buttons**: Eliminated "View Company Info" and "View Org Chart" buttons from home page
- **Simplified User Flow**: Streamlined navigation to focus on employee directory as the primary entry point
- **Cleaner Interface**: Updated home page messaging and button styling for better user experience
- **Consistent Architecture**: Aligned home page with modern application structure where company info is integrated into directory

### Modern Employee Details Drawer Implementation
- **Revolutionary UX Upgrade**: Replaced traditional page navigation with a beautiful slide-out drawer
- **Click-to-View**: Entire employee table rows are now clickable to open employee details
- **Modern Design**: Gradient header with employee profile, status badges, and professional styling
- **Tabbed Interface**: Organized information into Overview and Employment tabs for better navigation
- **Card-Based Layout**: Information displayed in clean, modern cards with icons and proper hierarchy
- **API Integration**: New `/api/employee/<id>` endpoint provides JSON data for seamless drawer functionality
- **Responsive Design**: Drawer adapts to mobile (full-screen) and desktop (520px width) perfectly
- **Enhanced Animations**: Smooth slide-in transitions and hover effects throughout
- **Removed Redundancy**: Eliminated action column and separate employee detail page for cleaner interface

### Streamlined Application Architecture
- **Removed Organization Chart**: Eliminated org chart functionality to focus on core employee directory features
- **Cleaner Navigation**: Simplified navigation with fewer buttons and clearer user flow
- **Code Optimization**: Removed unused routes, templates, and helper functions for better maintainability
- **Focused User Experience**: Streamlined application provides better performance and usability

### Redesigned Employee Directory with Modern UI
- Complete redesign of employee directory page with Weave-inspired modern interface
- Added beautiful gradient avatar initials for each employee
- Implemented real-time search functionality for filtering employees by name or department
- Enhanced table design with improved typography, spacing, and visual hierarchy
- Added color-coded status badges for active/inactive employees
- Implemented hover effects, smooth transitions, and loading animations
- Created responsive design that works seamlessly on mobile and desktop
- Improved navigation with modern button styling and better user experience
- Added professional enterprise-grade styling suitable for HR applications

### Enhanced Provider Navigation and Multi-Connection Management
- Added comprehensive navigation system across all pages
- Implemented provider selection and switching functionality  
- Enhanced home page with direct access to company data and directory
- Added consistent navigation bars with "Back to Provider Selection" options
- Improved user experience for managing multiple provider connections
- Updated CSV structure to track active provider connections

### Integrated Company Information Card in Employee Directory
- Added comprehensive company information card displayed above employee table
- Shows key company details including name, EIN, contact information, and statistics
- Displays department count, location count, and employee count in an organized layout
- Integrated detailed company sections for contact info, departments, and locations
- Features modern card design with professional styling that matches the directory interface
- Provides immediate company context while browsing employees for better user experience
- Maintains all existing directory functionality including search and employee details
- Responsive design ensures optimal viewing on both desktop and mobile devices

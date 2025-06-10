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

### Provider Sandbox Selection with Modal Interface
- **Professional Sandbox Selection Modal**: Added elegant modal dialog for choosing testing environments when connecting new providers
- **Two Testing Options**: Clear choice between Finch Sandbox (mock data) and Provider Sandbox (real provider test environments)
  - **🧪 Finch Sandbox**: Instant setup with mock data, perfect for quick development and testing
  - **🏢 Provider Sandbox**: Real provider environments (Gusto, Deel, Square, etc.) requiring demo accounts
- **Enhanced Connect Flow**: Updated `/connect` route to handle `sandbox_type` parameter for dynamic sandbox selection
- **Modern UI/UX**: Professional modal design with:
  - Responsive layout that adapts to mobile and desktop
  - Smooth animations and hover effects
  - Keyboard support (ESC key) and click-outside-to-close
  - Clear visual hierarchy with descriptive text and icons
- **Seamless Integration**: Minimal code changes leveraging existing `sandbox_selection` variable
- **Backward Compatible**: Maintains all existing functionality while adding new testing capabilities
- **Educational Interface**: Helps users understand different Finch testing environments and their use cases

### Intelligent Deductions Management with Smart Scope Handling
- **Complete Deductions Integration**: Added comprehensive deductions/benefits functionality using Finch's benefits API
- **New Deductions Tab**: Professional tab interface alongside Employee List for viewing all company benefits
- **Modern Benefits Cards**: Beautiful card-based UI with color-coded icons for different benefit types:
  - Retirement plans (401k, 403b, 457, SIMPLE IRA) with bank icons
  - Health benefits (HSA, FSA, Section 125) with medical icons  
  - Commuter benefits with transportation icons
  - Custom deductions with appropriate categorization
- **Intelligent Scope Management**: Revolutionary error handling that detects insufficient permissions and guides users through reauthentication
  - Automatic detection of 403 insufficient_scope_error responses
  - Professional reauth prompts with clear messaging and direct action buttons
  - "🔓 Add Benefits Access" button for seamless OAuth flow integration
  - Smart fallback handling for edge cases and connection management
- **Enhanced Search & Filter**: Real-time search functionality for filtering benefits by type or description
- **Company Contribution Details**: Comprehensive display of employer matching with tier information and thresholds
- **Copy-to-Clipboard Integration**: Benefit IDs can be easily copied with visual feedback
- **Responsive Design**: Fully responsive interface that works seamlessly on desktop and mobile
- **Production-Ready Architecture**: Clean API endpoints, proper error handling, and professional UI/UX

### Professional UI/UX Enhancements and Navigation Improvements
- **Human-Readable Date Formatting**: All dates throughout the application now display in "Month DD, YYYY" format instead of numeric format
  - Employee dates of birth, employment start/end dates, and income history dates
  - Payment dates and pay period dates in payroll data
  - Payment summary date ranges with proper formatting
- **Copy-to-Clipboard Functionality**: Added convenient copy buttons for all ID fields
  - Employee IDs in directory table and employee drawer
  - Manager IDs in employment details
  - Payment IDs in payroll statements
  - Modern clipboard API with fallback support for older browsers
  - Visual feedback with success notifications and button state changes
- **Clean Data Presentation**: Replaced "unavailable" text with professional "-" placeholder for missing data
- **Streamlined Payment Cards**: Removed redundant "Payment X -" prefix from payment statement titles
- **Optimized Navigation Flow**: Direct routing from provider selection and authentication to employee directory
  - Eliminated redundant company page navigation
  - Integrated company information directly into directory page
  - Maintained backend API routes for future extensibility

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

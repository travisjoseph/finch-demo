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

### Added Interactive Organization Chart Feature
- Implemented beautiful hierarchical organization chart visualization
- Added /org-chart route with employee hierarchy based on manager relationships
- Created interactive employee cards with gradient styling and hover effects
- Integrated job titles from employment API data
- Added department color coding and legend
- Implemented click-to-navigate functionality from org chart to employee details
- Added org chart navigation links across all pages
- Built responsive design that works on mobile and desktop

### Enhanced Provider Navigation and Multi-Connection Management
- Added comprehensive navigation system across all pages
- Implemented provider selection and switching functionality  
- Enhanced home page with direct access to company data and directory
- Added consistent navigation bars with "Back to Provider Selection" options
- Improved user experience for managing multiple provider connections
- Updated CSV structure to track active provider connections

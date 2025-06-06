from flask import Flask, render_template, redirect, request, jsonify 
from finch import Finch, APIError 
from dotenv import load_dotenv
import os
import uuid
import csv


load_dotenv(dotenv_path='.env.local')

app = Flask(__name__)

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_FILE_PATH = os.path.join(BASE_DIR, 'tokens.csv')

def get_all_connections():
    """Get all connections from CSV file"""
    if not os.path.exists(CSV_FILE_PATH):
        return []
    
    connections = []
    with open(CSV_FILE_PATH, mode='r', newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            connections.append(row)
    return connections

def get_active_connection():
    """Get the currently active connection"""
    connections = get_all_connections()
    if not connections:
        return None
    
    # Look for active connection first
    for conn in connections:
        if conn.get('active') == 'True':
            return conn
    
    # If no active connection set, return the most recent one
    return connections[-1]

def get_latest_access_token():
    """Get access token for active connection"""
    active_conn = get_active_connection()
    if not active_conn:
        return "Error: No token data found in file.", 500
    return active_conn['access_token']

def set_active_connection(connection_id):
    """Set a connection as active"""
    connections = get_all_connections()
    if not connections:
        return False
    
    # Update active status
    for conn in connections:
        conn['active'] = 'True' if conn['connection_id'] == connection_id else 'False'
    
    # Write back to CSV
    header = ['access_token', 'token_type', 'connection_id', 'customer_id',
              'account_id', 'client_type', 'company_id', 'connection_type',
              'products', 'provider_id', 'active']
    
    with open(CSV_FILE_PATH, mode='w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=header)
        writer.writeheader()
        writer.writerows(connections)
    
    return True

def get_connection_details(access_token):
    """Get provider and company details for a connection"""
    try:
        client = Finch(access_token=access_token)
        company_data = client.hris.company.retrieve()
        return {
            'company_name': company_data.legal_name or 'Unknown Company',
            'status': 'Active'
        }
    except Exception as e:
        return {
            'company_name': 'Unknown Company',
            'status': 'Error'
        }


@app.route('/')
def home():
    connections = get_all_connections()
    active_conn = get_active_connection()
    
    # Get details for each connection
    connection_details = []
    for conn in connections:
        details = get_connection_details(conn['access_token'])
        connection_details.append({
            'connection_id': conn['connection_id'],
            'provider_id': conn['provider_id'],
            'company_name': details['company_name'],
            'status': details['status'],
            'is_active': conn.get('active') == 'True' or (active_conn and conn['connection_id'] == active_conn['connection_id'])
        })
    
    return render_template('index.html', connections=connection_details)

@app.route('/select_provider/<connection_id>')
def select_provider(connection_id):
    success = set_active_connection(connection_id)
    if success:
        return redirect('/company')
    else:
        return redirect('/')


@app.route('/connect')
def connect():
    scopes = ["company", "directory", "individual", "employment"]
    
    client = Finch(
        client_id= CLIENT_ID,
        client_secret= CLIENT_SECRET
    )

    response = client.connect.sessions.new(
        customer_id = str(uuid.uuid4()),
        customer_name="x",
        products=scopes,
        redirect_uri = REDIRECT_URI    
    )

    return redirect(response.connect_url)

@app.route('/authorize')
def authorize():
    auth_code = request.args.get('code')
    
    client = Finch(
        client_id= CLIENT_ID,
        client_secret= CLIENT_SECRET
    )
    create_access_token_response = client.access_tokens.create(
        code=auth_code,
        redirect_uri=REDIRECT_URI
    )

    # Storing locally in a csv for demo purposes
    header = ['access_token', 'token_type', 'connection_id', 'customer_id',
              'account_id', 'client_type', 'company_id', 'connection_type',
              'products', 'provider_id', 'active']

    products_str = "|".join(create_access_token_response.products)

    # Set new connection as active, deactivate others
    file_exists = os.path.exists(CSV_FILE_PATH)
    if file_exists:
        # Deactivate existing connections
        connections = get_all_connections()
        for conn in connections:
            conn['active'] = 'False'
        
        # Write back existing connections
        with open(CSV_FILE_PATH, mode='w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=header)
            writer.writeheader()
            writer.writerows(connections)

    row_data = [
        create_access_token_response.access_token,
        create_access_token_response.token_type,
        create_access_token_response.connection_id,
        create_access_token_response.customer_id,
        create_access_token_response.account_id,
        create_access_token_response.client_type,
        create_access_token_response.company_id,
        create_access_token_response.connection_type,
        products_str,
        create_access_token_response.provider_id,
        'True'  # New connection is active
    ]
    
    with open(CSV_FILE_PATH, mode='a', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        if not file_exists:
            writer.writerow(header)
        writer.writerow(row_data)

    # Redirect to company route
    return redirect('/company')

@app.route('/company')
def company():

    client = Finch(
        access_token=get_latest_access_token(),
    )

    # Get compnay data, handles compatibility issues with custom message
    company_data = None 
    error_message = None
    try:
        company_data = client.hris.company.retrieve()
    except APIError as e:
        if hasattr(e, 'status_code') and e.status_code == 501:
            error_message = "Company data unsupported for provider"
            print(f"{e}")
        else:
            error_message = "Could not load company data."
            print(f"{e}")
    except Exception as e:
        error_message = "Encountered an unexpected error."
        print(f"{e}")

    return render_template('company.html', company_data=company_data, error_message=error_message)

@app.route('/directory')
def directory():

    client = Finch(
        access_token=get_latest_access_token(),
    )

    # Get individual data, handles compatibility issues with custom message
    individuals = []
    error_message = None
    try:
        individuals = client.hris.directory.list().individuals
    except APIError as e:
        if hasattr(e, 'status_code') and e.status_code == 501:
            error_message = "Directory data unsupported for provider"
            print(f"{e}")
        else:
            error_message = "Could not load directory data."
            print(f"{e}")
    except Exception as e:
        error_message = "Encountered an unexpected error."
        print(f"{e}")

    return render_template('directory.html', directory_data=individuals, error_message=error_message)


@app.route('/directory/employee/<employee_id>')
def employee_detail(employee_id):
    
    client = Finch(
        access_token=get_latest_access_token(),
    )

    employment_data = None
    employment_error = None 

    # Get employment data, handles compatibility issues with custom message
    try:
        page = client.hris.employments.retrieve_many(
            requests=[{
                    "individual_id" : employee_id
                }
            ]
        )
        employment_data = page.responses[0].body
    except APIError as e:
        if hasattr(e, 'status_code') and e.status_code == 501:
            employment_error = "Employment data unsupported for provider"
            print(f"{e}")
        else:
            employment_error = "Could not load employment data."
            print(f"{e}")
    except Exception as e:
        employment_error = "Encountered an unexpected error."
        print(f"{e}")

    # Get individual data, handles compatibility issues with custom message
    individual_data = None
    individual_error = None
    try:
        page = client.hris.individuals.retrieve_many(
            requests=[{
                "individual_id" : employee_id
            }]
        )
        individual_data = page.responses[0].body
    except APIError as e:
        if hasattr(e, 'status_code') and e.status_code == 501:
            individual_error = "Individual data unsupported for provider"
            print(f"{e}")
        else:
            individual_error = "Could not load individual data."
            print(f"{e}")
    except Exception as e:
        individual_error = "Encountered an unexpected error."
        print(f"{e}")

    return render_template('employee_detail.html',
                           individual=individual_data,
                           employment=employment_data,
                           individual_error=individual_error,
                           employment_error=employment_error)

if __name__ == '__main__':
    app.run(debug=True)

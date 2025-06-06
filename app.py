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
        
        # Check if connection has payroll scopes
        products = conn.get('products', '').split('|') if conn.get('products') else []
        has_payroll = 'payment' in products and 'pay_statement' in products
        
        connection_details.append({
            'connection_id': conn['connection_id'],
            'provider_id': conn['provider_id'],
            'company_name': details['company_name'],
            'status': details['status'],
            'is_active': conn.get('active') == 'True' or (active_conn and conn['connection_id'] == active_conn['connection_id']),
            'has_payroll': has_payroll,
            'products': products
        })
    
    return render_template('index.html', connections=connection_details)

@app.route('/select_provider/<connection_id>')
def select_provider(connection_id):
    success = set_active_connection(connection_id)
    if success:
        return redirect('/directory')
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

@app.route('/reauth/<connection_id>')
def reauth(connection_id):
    """Reauthenticate a connection with additional payroll scopes"""
    # Include payroll scopes for accessing payment and pay statement data
    scopes = ["company", "directory", "individual", "employment", "payment", "pay_statement"]
    
    client = Finch(
        client_id= CLIENT_ID,
        client_secret= CLIENT_SECRET
    )

    try:
        response = client.connect.sessions.reauthenticate(
            connection_id=connection_id,
            products=scopes,
            redirect_uri=REDIRECT_URI
        )
        return redirect(response.connect_url)
    except Exception as e:
        print(f"Reauth error: {e}")
        return redirect('/')

@app.route('/introspect')
def introspect():
    """Debug endpoint to see current connection details and scopes"""
    client = Finch(
        access_token=get_latest_access_token(),
    )
    
    try:
        introspection = client.account.introspect()
        print("\n" + "="*80)
        print("CONNECTION INTROSPECTION")
        print("="*80)
        print(f"Connection ID: {introspection.connection_id}")
        print(f"Provider ID: {introspection.provider_id}")
        print(f"Current Products: {introspection.products}")
        print(f"Connection Status: {introspection.connection_status.status if introspection.connection_status else 'Unknown'}")
        print(f"Full Introspection: {introspection}")
        
        return jsonify({
            'connection_id': introspection.connection_id,
            'provider_id': introspection.provider_id,
            'products': introspection.products,
            'connection_status': introspection.connection_status.status if introspection.connection_status else None,
            'message': 'Connection details logged to server console'
        })
    except Exception as e:
        error_msg = f"Error introspecting connection: {e}"
        print(f"INTROSPECT ERROR: {error_msg}")
        return jsonify({'error': error_msg}), 500

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
    connection_id = create_access_token_response.connection_id

    # Check if this connection already exists (reauthentication case)
    file_exists = os.path.exists(CSV_FILE_PATH)
    connections = get_all_connections() if file_exists else []
    
    existing_connection_index = None
    for i, conn in enumerate(connections):
        if conn['connection_id'] == connection_id:
            existing_connection_index = i
            break
    
    if existing_connection_index is not None:
        # Update existing connection with new token and products
        print(f"Updating existing connection: {connection_id}")
        connections[existing_connection_index].update({
            'access_token': create_access_token_response.access_token,
            'token_type': create_access_token_response.token_type,
            'products': products_str,
            'active': 'True'
        })
        
        # Deactivate other connections
        for i, conn in enumerate(connections):
            if i != existing_connection_index:
                conn['active'] = 'False'
        
        # Write back all connections
        with open(CSV_FILE_PATH, mode='w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=header)
            writer.writeheader()
            writer.writerows(connections)
    else:
        # New connection - add it
        print(f"Adding new connection: {connection_id}")
        
        # Deactivate existing connections
        for conn in connections:
            conn['active'] = 'False'
        
        # Write back existing connections first
        if connections:
            with open(CSV_FILE_PATH, mode='w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=header)
                writer.writeheader()
                writer.writerows(connections)

        # Add new connection
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

    # Redirect to directory route
    return redirect('/directory')

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
    directory_error = None
    try:
        individuals = client.hris.directory.list().individuals
    except APIError as e:
        if hasattr(e, 'status_code') and e.status_code == 501:
            directory_error = "Directory data unsupported for provider"
            print(f"{e}")
        else:
            directory_error = "Could not load directory data."
            print(f"{e}")
    except Exception as e:
        directory_error = "Encountered an unexpected error."
        print(f"{e}")

    # Get company data for the top card
    company_data = None 
    company_error = None
    try:
        company_data = client.hris.company.retrieve()
    except APIError as e:
        if hasattr(e, 'status_code') and e.status_code == 501:
            company_error = "Company data unsupported for provider"
            print(f"{e}")
        else:
            company_error = "Could not load company data."
            print(f"{e}")
    except Exception as e:
        company_error = "Encountered an unexpected error."
        print(f"{e}")

    return render_template('directory.html', 
                         directory_data=individuals, 
                         directory_error=directory_error,
                         company_data=company_data,
                         company_error=company_error)


def get_employee_data(employee_id):
    """Shared function to get employee data for both API and template routes"""
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

    return {
        'individual': individual_data,
        'employment': employment_data,
        'individual_error': individual_error,
        'employment_error': employment_error
    }

@app.route('/api/employee/<employee_id>')
def api_employee_detail(employee_id):
    """API endpoint that returns employee data as JSON"""
    try:
        data = get_employee_data(employee_id)
        
        # Convert Finch objects to dictionaries for JSON serialization
        result = {
            'individual': data['individual'].__dict__ if data['individual'] else None,
            'employment': data['employment'].__dict__ if data['employment'] else None,
            'individual_error': data['individual_error'],
            'employment_error': data['employment_error']
        }
        
        # Handle nested objects that might need conversion
        if result['individual']:
            # Convert nested objects to dicts
            for key, value in result['individual'].items():
                if hasattr(value, '__dict__'):
                    result['individual'][key] = value.__dict__
                elif isinstance(value, list) and value and hasattr(value[0], '__dict__'):
                    result['individual'][key] = [item.__dict__ for item in value]
        
        if result['employment']:
            # Convert nested objects to dicts
            for key, value in result['employment'].items():
                if hasattr(value, '__dict__'):
                    result['employment'][key] = value.__dict__
                elif isinstance(value, list) and value and hasattr(value[0], '__dict__'):
                    result['employment'][key] = [item.__dict__ for item in value]
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/employee/<employee_id>/payments')
def api_employee_payments(employee_id):
    """API endpoint that returns payment data for a specific employee"""
    try:
        client = Finch(
            access_token=get_latest_access_token(),
        )
        
        # Get payments for the last 90 days to have a good range
        from datetime import datetime, timedelta
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
        
        # Get all payments
        payments = client.hris.payments.list(
            start_date=start_date,
            end_date=end_date
        )
        
        employee_payments = []
        
        # Filter payments that include this employee
        for payment in payments:
            if payment.individual_ids and employee_id in payment.individual_ids:
                # Get pay statements for this payment
                try:
                    pay_statement_response = client.hris.pay_statements.retrieve_many(
                        requests=[{
                            "payment_id": payment.id
                        }]
                    )
                    
                    # Find the pay statement for this specific employee
                    employee_pay_statement = None
                    if (pay_statement_response.responses and 
                        pay_statement_response.responses[0].body and 
                        pay_statement_response.responses[0].body.pay_statements):
                        
                        for pay_statement in pay_statement_response.responses[0].body.pay_statements:
                            if pay_statement.individual_id == employee_id:
                                employee_pay_statement = pay_statement
                                break
                    
                    # Convert to dict for JSON serialization
                    payment_data = {
                        'payment_id': payment.id,
                        'pay_date': payment.pay_date,
                        'pay_period': {
                            'start_date': payment.pay_period.start_date if payment.pay_period else None,
                            'end_date': payment.pay_period.end_date if payment.pay_period else None
                        } if payment.pay_period else None,
                        'pay_statement': None,
                        'pay_statement_error': None
                    }
                    
                    if employee_pay_statement:
                        # Convert pay statement to dict
                        pay_statement_dict = employee_pay_statement.__dict__.copy()
                        
                        # Handle nested objects
                        for key, value in pay_statement_dict.items():
                            if hasattr(value, '__dict__'):
                                pay_statement_dict[key] = value.__dict__
                            elif isinstance(value, list) and value and hasattr(value[0], '__dict__'):
                                pay_statement_dict[key] = [item.__dict__ for item in value]
                        
                        payment_data['pay_statement'] = pay_statement_dict
                    else:
                        payment_data['pay_statement_error'] = 'No pay statement found for this employee'
                    
                    employee_payments.append(payment_data)
                    
                except Exception as pay_stmt_error:
                    # Still include the payment even if pay statement fails
                    payment_data = {
                        'payment_id': payment.id,
                        'pay_date': payment.pay_date,
                        'pay_period': {
                            'start_date': payment.pay_period.start_date if payment.pay_period else None,
                            'end_date': payment.pay_period.end_date if payment.pay_period else None
                        } if payment.pay_period else None,
                        'pay_statement': None,
                        'pay_statement_error': f'Error fetching pay statement: {str(pay_stmt_error)}'
                    }
                    employee_payments.append(payment_data)
        
        # Sort by pay date (most recent first)
        employee_payments.sort(key=lambda x: x['pay_date'] or '', reverse=True)
        
        return jsonify({
            'employee_id': employee_id,
            'payments': employee_payments,
            'date_range': f'{start_date} to {end_date}',
            'total_payments': len(employee_payments)
        })
        
    except APIError as e:
        error_msg = f"API Error: {e}"
        if hasattr(e, 'status_code') and e.status_code == 501:
            error_msg = "Payment data unsupported for this provider"
        return jsonify({'error': error_msg}), 400
    except Exception as e:
        error_msg = f"Unexpected error: {e}"
        return jsonify({'error': error_msg}), 500




if __name__ == '__main__':
    app.run(debug=True, port=5000)

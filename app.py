from flask import Flask, render_template, redirect, request, jsonify 
from finch import Finch, APIError 
from dotenv import load_dotenv
import os
import uuid
import csv
from datetime import datetime, timedelta


load_dotenv(dotenv_path='.env.local')

app = Flask(__name__)

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_FILE_PATH = os.path.join(BASE_DIR, 'tokens.csv')
JOBS_CSV_PATH = os.path.join(BASE_DIR, 'jobs.csv')

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
        return None
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

# Jobs CSV Management Functions
def get_jobs_csv_headers():
    """Get the headers for the jobs CSV file"""
    return ['job_id', 'connection_id', 'provider_id', 'job_type', 'status', 
            'created_at', 'scheduled_at', 'started_at', 'completed_at', 
            'job_url', 'allowed_refreshes', 'remaining_refreshes', 'error_message']

def save_job_to_csv(job_data):
    """Save new job to CSV"""
    headers = get_jobs_csv_headers()
    file_exists = os.path.exists(JOBS_CSV_PATH)
    
    # Ensure all required fields are present
    row_data = {}
    for header in headers:
        row_data[header] = job_data.get(header, '')
    
    with open(JOBS_CSV_PATH, mode='a', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row_data)

def get_jobs_for_connection(connection_id):
    """Get all jobs for a specific connection"""
    if not os.path.exists(JOBS_CSV_PATH):
        return []
    
    jobs = []
    with open(JOBS_CSV_PATH, mode='r', newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if row['connection_id'] == connection_id:
                jobs.append(row)
    
    # Sort by created_at (newest first)
    jobs.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    return jobs

def update_job_status(job_id, status_data):
    """Update job status in CSV"""
    if not os.path.exists(JOBS_CSV_PATH):
        return False
    
    jobs = []
    updated = False
    
    # Read all jobs
    with open(JOBS_CSV_PATH, mode='r', newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if row['job_id'] == job_id:
                # Update this job with new status data
                for key, value in status_data.items():
                    if value is not None:
                        row[key] = value
                updated = True
            jobs.append(row)
    
    if updated:
        # Write back all jobs
        headers = get_jobs_csv_headers()
        with open(JOBS_CSV_PATH, mode='w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=headers)
            writer.writeheader()
            writer.writerows(jobs)
    
    return updated

def cleanup_old_jobs(days_to_keep=30):
    """Remove jobs older than specified days"""
    if not os.path.exists(JOBS_CSV_PATH):
        return 0
    
    cutoff_date = datetime.now() - timedelta(days=days_to_keep)
    jobs_to_keep = []
    removed_count = 0
    
    with open(JOBS_CSV_PATH, mode='r', newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            try:
                created_at = datetime.fromisoformat(row['created_at'].replace('Z', '+00:00'))
                if created_at >= cutoff_date:
                    jobs_to_keep.append(row)
                else:
                    removed_count += 1
            except (ValueError, KeyError):
                # Keep jobs with invalid dates
                jobs_to_keep.append(row)
    
    if removed_count > 0:
        # Write back remaining jobs
        headers = get_jobs_csv_headers()
        with open(JOBS_CSV_PATH, mode='w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=headers)
            writer.writeheader()
            writer.writerows(jobs_to_keep)
    
    return removed_count



@app.route('/')
def home():
    connections = get_all_connections()
    active_conn = get_active_connection()
    
    # Get details for each connection
    connection_details = []
    for conn in connections:
        details = get_connection_details(conn['access_token'])
        
        # Check if connection has payroll and benefits scopes
        products = conn.get('products', '').split('|') if conn.get('products') else []
        has_payroll = 'payment' in products and 'pay_statement' in products
        has_benefits = 'benefits' in products
        
        connection_details.append({
            'connection_id': conn['connection_id'],
            'provider_id': conn['provider_id'],
            'company_name': details['company_name'],
            'status': details['status'],
            'is_active': conn.get('active') == 'True' or (active_conn and conn['connection_id'] == active_conn['connection_id']),
            'has_payroll': has_payroll,
            'has_benefits': has_benefits,
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
    scopes = ["company", "directory", "individual", "employment", "benefits"]
    
    # Get sandbox type from URL parameter and set sandbox_selection accordingly
    sandbox_type = request.args.get('sandbox_type', '')
    if sandbox_type == 'finch':
        sandbox_selection = "finch"
    elif sandbox_type == 'provider':
        sandbox_selection = "provider"
    else:
        sandbox_selection = ""  # Default (production)
    
    client = Finch(
        client_id= CLIENT_ID,
        client_secret= CLIENT_SECRET
    )

    response = client.connect.sessions.new(
        customer_id = str(uuid.uuid4()),
        customer_name="x",
        products=scopes,
        redirect_uri = REDIRECT_URI,
        sandbox = sandbox_selection
    )

    return redirect(response.connect_url)

@app.route('/reauth/<connection_id>')
def reauth(connection_id):
    """Reauthenticate a connection with additional payroll and benefits scopes"""
    # Include all scopes for accessing payment, pay statement, and benefits data
    scopes = ["company", "directory", "individual", "employment", "payment", "pay_statement", "benefits"]
    
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


@app.route('/api/active-connection')
def api_active_connection():
    """API endpoint that returns the current active connection details"""
    try:
        active_conn = get_active_connection()
        if active_conn:
            return jsonify({
                'connection_id': active_conn['connection_id'],
                'provider_id': active_conn['provider_id'],
                'products': active_conn.get('products', '').split('|') if active_conn.get('products') else []
            })
        else:
            return jsonify({'error': 'No active connection found'}), 404
    except Exception as e:
        return jsonify({'error': f'Failed to get active connection: {str(e)}'}), 500


@app.route('/api/deductions')
def api_deductions():
    """API endpoint that returns all company benefits/deductions"""
    print("\n" + "="*80)
    print("DEDUCTIONS API ENDPOINT CALLED")
    print("="*80)
    
    try:
        # Get access token
        access_token = get_latest_access_token()
        print(f"Access token retrieved: {access_token[:20]}..." if access_token else "No access token")
        
        client = Finch(
            access_token=access_token,
        )
        print("Finch client created successfully")
        
        # Get all company benefits/deductions
        print("Attempting to fetch benefits from Finch API...")
        benefits = client.hris.benefits.list()
        print(f"Benefits fetched successfully. Type: {type(benefits)}")
        print(f"Benefits object: {benefits}")
        
        # Convert benefits to list of dictionaries for JSON serialization
        benefits_list = []
        benefit_count = 0
        
        print("Processing benefits...")
        for benefit in benefits:
            benefit_count += 1
            print(f"Processing benefit {benefit_count}: {benefit}")
            print(f"Benefit type: {type(benefit)}")
            print(f"Benefit attributes: {dir(benefit)}")
            
            try:
                benefit_data = {
                    'benefit_id': getattr(benefit, 'benefit_id', None),
                    'type': getattr(benefit, 'type', None),
                    'description': getattr(benefit, 'description', None),
                    'frequency': getattr(benefit, 'frequency', None),
                    'company_contribution': None
                }
                print(f"Basic benefit data: {benefit_data}")
                
                # Handle company contribution if present
                if hasattr(benefit, 'company_contribution') and benefit.company_contribution:
                    print(f"Processing company contribution: {benefit.company_contribution}")
                    contribution_data = {
                        'type': getattr(benefit.company_contribution, 'type', None),
                        'tiers': []
                    }
                    
                    # Handle tiers if present
                    if hasattr(benefit.company_contribution, 'tiers') and benefit.company_contribution.tiers:
                        print(f"Processing tiers: {benefit.company_contribution.tiers}")
                        for tier_idx, tier in enumerate(benefit.company_contribution.tiers):
                            print(f"Processing tier {tier_idx}: {tier}")
                            tier_data = {}
                            if hasattr(tier, 'threshold'):
                                tier_data['threshold'] = tier.threshold
                            if hasattr(tier, 'match'):
                                tier_data['match'] = tier.match
                            contribution_data['tiers'].append(tier_data)
                            print(f"Tier data: {tier_data}")
                    
                    benefit_data['company_contribution'] = contribution_data
                    print(f"Final contribution data: {contribution_data}")
                
                benefits_list.append(benefit_data)
                print(f"Benefit {benefit_count} processed successfully")
                
            except Exception as benefit_error:
                print(f"Error processing benefit {benefit_count}: {benefit_error}")
                print(f"Benefit object that caused error: {benefit}")
                # Continue processing other benefits
                continue
        
        print(f"Total benefits processed: {len(benefits_list)}")
        
        response_data = {
            'benefits': benefits_list,
            'total_benefits': len(benefits_list)
        }
        print(f"Final response data: {response_data}")
        
        return jsonify(response_data)
        
    except APIError as e:
        error_msg = f"Finch API Error: {e}"
        print(f"API ERROR: {error_msg}")
        print(f"API Error details - Status: {getattr(e, 'status_code', 'Unknown')}")
        print(f"API Error details - Response: {getattr(e, 'response', 'Unknown')}")
        print(f"API Error details - Body: {getattr(e, 'body', 'Unknown')}")
        
        # Check for insufficient scope error (403)
        if hasattr(e, 'status_code') and e.status_code == 403:
            # Try to parse the error body for scope information
            error_body = getattr(e, 'body', {})
            if isinstance(error_body, dict):
                error_code = error_body.get('code')
                error_name = error_body.get('name')
                error_message = error_body.get('message', '')
                
                print(f"Error code: {error_code}")
                print(f"Error name: {error_name}")
                print(f"Error message: {error_message}")
                
                if error_name == 'insufficient_scope_error':
                    # Extract missing scopes from the error message
                    missing_scopes = []
                    if 'Missing scopes:' in error_message:
                        # Parse something like "Missing scopes: [benefits]"
                        import re
                        scope_match = re.search(r'Missing scopes:\s*\[([^\]]+)\]', error_message)
                        if scope_match:
                            scopes_str = scope_match.group(1)
                            missing_scopes = [scope.strip().strip('"\'') for scope in scopes_str.split(',')]
                    
                    print(f"Parsed missing scopes: {missing_scopes}")
                    
                    # Get current connection ID for reauth URL
                    active_conn = get_active_connection()
                    connection_id = active_conn['connection_id'] if active_conn else None
                    
                    response_data = {
                        'error_type': 'insufficient_scope',
                        'missing_scopes': missing_scopes,
                        'reauth_url': f'/reauth/{connection_id}' if connection_id else None,
                        'message': f'Additional permissions needed: {", ".join(missing_scopes)}' if missing_scopes else 'Additional permissions needed',
                        'connection_id': connection_id
                    }
                    
                    print(f"Returning structured error response: {response_data}")
                    return jsonify(response_data), 403
        
        if hasattr(e, 'status_code') and e.status_code == 501:
            error_msg = "Benefits/deductions data unsupported for this provider"
        return jsonify({'error': error_msg}), 400
    except Exception as e:
        error_msg = f"Unexpected error: {e}"
        print(f"UNEXPECTED ERROR: {error_msg}")
        print(f"Error type: {type(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return jsonify({'error': error_msg}), 500


# Jobs API Endpoints
@app.route('/api/jobs/enqueue', methods=['POST'])
def enqueue_job():
    """API endpoint to enqueue a new data sync job"""
    print("\n" + "="*80)
    print("ENQUEUE JOB API ENDPOINT CALLED")
    print("="*80)
    
    try:
        # Get active connection
        active_conn = get_active_connection()
        if not active_conn:
            return jsonify({'error': 'No active connection found'}), 400
        
        print(f"Active connection: {active_conn['connection_id']} ({active_conn['provider_id']})")
        
        # Create Finch client
        client = Finch(access_token=active_conn['access_token'])
        
        # Create job via Finch API
        print("Creating data_sync_all job via Finch API...")
        job_response = client.jobs.automated.create(type="data_sync_all")
        print(f"Job created successfully: {job_response}")
        
        # Prepare job data for CSV
        job_data = {
            'job_id': job_response.job_id,
            'connection_id': active_conn['connection_id'],
            'provider_id': active_conn['provider_id'],
            'job_type': 'data_sync_all',
            'status': 'pending',
            'created_at': datetime.now().isoformat(),
            'scheduled_at': getattr(job_response, 'scheduled_at', ''),
            'started_at': '',
            'completed_at': '',
            'job_url': job_response.job_url,
            'allowed_refreshes': job_response.allowed_refreshes,
            'remaining_refreshes': job_response.remaining_refreshes,
            'error_message': ''
        }
        
        # Save to CSV
        print("Saving job to CSV...")
        save_job_to_csv(job_data)
        print("Job saved to CSV successfully")
        
        # Clean up old jobs periodically
        cleanup_old_jobs()
        
        return jsonify({
            'job_id': job_response.job_id,
            'job_url': job_response.job_url,
            'status': 'pending',
            'allowed_refreshes': job_response.allowed_refreshes,
            'remaining_refreshes': job_response.remaining_refreshes,
            'created_at': job_data['created_at'],
            'connection_id': active_conn['connection_id'],
            'provider_id': active_conn['provider_id']
        })
        
    except APIError as e:
        error_msg = f"Finch API Error: {e}"
        print(f"API ERROR: {error_msg}")
        
        if hasattr(e, 'status_code') and e.status_code == 501:
            error_msg = "Automated jobs unsupported for this provider"
        elif hasattr(e, 'status_code') and e.status_code == 403:
            error_msg = "Insufficient permissions to create jobs"
        
        return jsonify({'error': error_msg}), getattr(e, 'status_code', 400)
    except Exception as e:
        error_msg = f"Unexpected error: {e}"
        print(f"UNEXPECTED ERROR: {error_msg}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return jsonify({'error': error_msg}), 500

@app.route('/api/jobs/status/<job_id>')
def get_job_status(job_id):
    """API endpoint to get job status"""
    print(f"\n{'='*80}")
    print(f"GET JOB STATUS API ENDPOINT CALLED")
    print(f"Job ID: {job_id}")
    print(f"{'='*80}")
    
    try:
        # Get active connection details
        active_conn = get_active_connection()
        print(f"Active connection: {active_conn}")
        
        if not active_conn:
            print("ERROR: No active connection found")
            return jsonify({'error': 'No active connection found'}), 400
        
        # Get current status from Finch API
        access_token = get_latest_access_token()
        print(f"Access token from get_latest_access_token(): {access_token[:20] + '...' if access_token else 'None'}")
        print(f"Access token from active_conn: {active_conn['access_token'][:20] + '...' if active_conn.get('access_token') else 'None'}")
        print(f"Connection ID: {active_conn.get('connection_id')}")
        print(f"Provider ID: {active_conn.get('provider_id')}")
        
        if not access_token:
            print("ERROR: No access token available")
            return jsonify({'error': 'No access token available'}), 401
        
        # Use the access token directly from active connection to be sure
        final_access_token = active_conn['access_token']
        print(f"Using final access token: {final_access_token[:20] + '...' if final_access_token else 'None'}")
        
        client = Finch(access_token=final_access_token)
        print("Finch client created successfully")
        print("Fetching job status from Finch API...")
        
        # Add more detailed error handling for the API call
        try:
            job_status = client.jobs.automated.retrieve(job_id)
            print(f"Job status retrieved successfully: {job_status}")
        except APIError as api_error:
            print(f"Finch API Error during retrieve: {api_error}")
            print(f"API Error status code: {getattr(api_error, 'status_code', 'Unknown')}")
            print(f"API Error response: {getattr(api_error, 'response', 'Unknown')}")
            print(f"API Error body: {getattr(api_error, 'body', 'Unknown')}")
            raise api_error
        
        # Update CSV with latest status
        status_data = {
            'status': job_status.status,
            'started_at': getattr(job_status, 'started_at', ''),
            'completed_at': getattr(job_status, 'completed_at', ''),
            'scheduled_at': getattr(job_status, 'scheduled_at', '')
        }
        
        print("Updating job status in CSV...")
        update_job_status(job_id, status_data)
        print("Job status updated in CSV")
        
        # Convert job status to dict for JSON response
        response_data = {
            'job_id': job_status.job_id,
            'job_url': getattr(job_status, 'job_url', ''),
            'type': job_status.type,
            'status': job_status.status,
            'created_at': getattr(job_status, 'created_at', ''),
            'scheduled_at': getattr(job_status, 'scheduled_at', ''),
            'started_at': getattr(job_status, 'started_at', ''),
            'completed_at': getattr(job_status, 'completed_at', ''),
            'params': getattr(job_status, 'params', {})
        }
        
        return jsonify(response_data)
        
    except APIError as e:
        error_msg = f"Finch API Error: {e}"
        print(f"API ERROR: {error_msg}")
        
        if hasattr(e, 'status_code') and e.status_code == 404:
            error_msg = f"Job {job_id} not found"
        elif hasattr(e, 'status_code') and e.status_code == 501:
            error_msg = "Job status retrieval unsupported for this provider"
        
        return jsonify({'error': error_msg}), getattr(e, 'status_code', 400)
    except Exception as e:
        error_msg = f"Unexpected error: {e}"
        print(f"UNEXPECTED ERROR: {error_msg}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return jsonify({'error': error_msg}), 500

@app.route('/api/jobs/list')
def list_jobs():
    """API endpoint to list jobs for active connection"""
    print("\n" + "="*80)
    print("LIST JOBS API ENDPOINT CALLED")
    print("="*80)
    
    try:
        # Get active connection
        active_conn = get_active_connection()
        if not active_conn:
            return jsonify({'error': 'No active connection found'}), 400
        
        print(f"Getting jobs for connection: {active_conn['connection_id']}")
        
        # Get jobs from CSV
        jobs = get_jobs_for_connection(active_conn['connection_id'])
        print(f"Found {len(jobs)} jobs in CSV")
        
        # Format jobs for response
        formatted_jobs = []
        for job in jobs:
            formatted_job = {
                'job_id': job['job_id'],
                'job_type': job['job_type'],
                'status': job['status'],
                'created_at': job['created_at'],
                'scheduled_at': job['scheduled_at'],
                'started_at': job['started_at'],
                'completed_at': job['completed_at'],
                'job_url': job['job_url'],
                'allowed_refreshes': job['allowed_refreshes'],
                'remaining_refreshes': job['remaining_refreshes'],
                'error_message': job['error_message']
            }
            formatted_jobs.append(formatted_job)
        
        return jsonify({
            'jobs': formatted_jobs,
            'connection_id': active_conn['connection_id'],
            'provider_id': active_conn['provider_id'],
            'total_jobs': len(formatted_jobs)
        })
        
    except Exception as e:
        error_msg = f"Unexpected error: {e}"
        print(f"UNEXPECTED ERROR: {error_msg}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return jsonify({'error': error_msg}), 500

@app.route('/api/deductions/<benefit_id>/enrolled')
def api_benefit_enrolled_individuals(benefit_id):
    """API endpoint that returns enrolled individuals for a specific benefit"""
    print(f"\n{'='*80}")
    print(f"BENEFIT ENROLLED INDIVIDUALS API ENDPOINT CALLED")
    print(f"Benefit ID: {benefit_id}")
    print(f"{'='*80}")
    
    try:
        # Get access token
        access_token = get_latest_access_token()
        print(f"Access token retrieved: {access_token[:20]}..." if access_token else "No access token")
        
        client = Finch(
            access_token=access_token,
        )
        print("Finch client created successfully")
        
        # Get enrolled individuals for the benefit
        print(f"Attempting to fetch enrolled individuals for benefit: {benefit_id}")
        enrolled_response = client.hris.benefits.individuals.enrolled_ids(benefit_id)
        print(f"Enrolled individuals response: {enrolled_response}")
        
        # Extract individual IDs
        individual_ids = getattr(enrolled_response, 'individual_ids', [])
        print(f"Individual IDs found: {individual_ids}")
        
        # If no individuals are enrolled, return empty result
        if not individual_ids:
            return jsonify({
                'benefit_id': benefit_id,
                'enrolled_individuals': [],
                'total_enrolled': 0
            })
        
        # Fetch basic employee data for each enrolled individual
        print("Fetching employee data for enrolled individuals...")
        enrolled_employees = []
        
        # Get directory data to match individual IDs with employee info
        try:
            directory_response = client.hris.directory.list()
            directory_individuals = directory_response.individuals
            print(f"Directory individuals count: {len(directory_individuals)}")
            
            # Create a lookup map for quick access
            directory_map = {individual.id: individual for individual in directory_individuals}
            
            for individual_id in individual_ids:
                if individual_id in directory_map:
                    individual = directory_map[individual_id]
                    
                    # Create employee data structure
                    employee_data = {
                        'id': individual.id,
                        'first_name': getattr(individual, 'first_name', None),
                        'last_name': getattr(individual, 'last_name', None),
                        'preferred_name': getattr(individual, 'preferred_name', None),
                        'is_active': getattr(individual, 'is_active', None),
                        'department': None,
                        'manager': None
                    }
                    
                    # Add department info if available
                    if hasattr(individual, 'department') and individual.department:
                        employee_data['department'] = {
                            'name': getattr(individual.department, 'name', None)
                        }
                    
                    # Add manager info if available
                    if hasattr(individual, 'manager') and individual.manager:
                        employee_data['manager'] = {
                            'id': getattr(individual.manager, 'id', None)
                        }
                    
                    enrolled_employees.append(employee_data)
                    print(f"Added employee data for {individual_id}: {employee_data['first_name']} {employee_data['last_name']}")
                else:
                    print(f"Warning: Individual {individual_id} not found in directory")
                    # Still add a minimal record
                    enrolled_employees.append({
                        'id': individual_id,
                        'first_name': None,
                        'last_name': None,
                        'preferred_name': None,
                        'is_active': None,
                        'department': None,
                        'manager': None
                    })
        
        except Exception as directory_error:
            print(f"Error fetching directory data: {directory_error}")
            # Fallback: return just the IDs without enriched data
            enrolled_employees = [{'id': individual_id} for individual_id in individual_ids]
        
        response_data = {
            'benefit_id': benefit_id,
            'enrolled_individuals': enrolled_employees,
            'total_enrolled': len(enrolled_employees)
        }
        
        print(f"Final enrolled individuals response: {response_data}")
        return jsonify(response_data)
        
    except APIError as e:
        error_msg = f"Finch API Error: {e}"
        print(f"API ERROR: {error_msg}")
        print(f"API Error details - Status: {getattr(e, 'status_code', 'Unknown')}")
        print(f"API Error details - Response: {getattr(e, 'response', 'Unknown')}")
        print(f"API Error details - Body: {getattr(e, 'body', 'Unknown')}")
        
        # Check for insufficient scope error (403)
        if hasattr(e, 'status_code') and e.status_code == 403:
            # Try to parse the error body for scope information
            error_body = getattr(e, 'body', {})
            if isinstance(error_body, dict):
                error_code = error_body.get('code')
                error_name = error_body.get('name')
                error_message = error_body.get('message', '')
                
                print(f"Error code: {error_code}")
                print(f"Error name: {error_name}")
                print(f"Error message: {error_message}")
                
                if error_name == 'insufficient_scope_error':
                    # Extract missing scopes from the error message
                    missing_scopes = []
                    if 'Missing scopes:' in error_message:
                        # Parse something like "Missing scopes: [benefits]"
                        import re
                        scope_match = re.search(r'Missing scopes:\s*\[([^\]]+)\]', error_message)
                        if scope_match:
                            scopes_str = scope_match.group(1)
                            missing_scopes = [scope.strip().strip('"\'') for scope in scopes_str.split(',')]
                    
                    print(f"Parsed missing scopes: {missing_scopes}")
                    
                    # Get current connection ID for reauth URL
                    active_conn = get_active_connection()
                    connection_id = active_conn['connection_id'] if active_conn else None
                    
                    response_data = {
                        'error_type': 'insufficient_scope',
                        'missing_scopes': missing_scopes,
                        'reauth_url': f'/reauth/{connection_id}' if connection_id else None,
                        'message': f'Additional permissions needed: {", ".join(missing_scopes)}' if missing_scopes else 'Additional permissions needed',
                        'connection_id': connection_id
                    }
                    
                    print(f"Returning structured error response: {response_data}")
                    return jsonify(response_data), 403
        
        if hasattr(e, 'status_code') and e.status_code == 501:
            error_msg = "Enrolled individuals data unsupported for this provider"
        elif hasattr(e, 'status_code') and e.status_code == 404:
            error_msg = f"Benefit {benefit_id} not found"
        return jsonify({'error': error_msg}), getattr(e, 'status_code', 400)
    except Exception as e:
        error_msg = f"Unexpected error: {e}"
        print(f"UNEXPECTED ERROR: {error_msg}")
        print(f"Error type: {type(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return jsonify({'error': error_msg}), 500




if __name__ == '__main__':
    app.run(debug=True, port=5000)

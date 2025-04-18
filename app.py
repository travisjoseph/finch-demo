from flask import Flask, render_template, redirect, request, jsonify # <-- Added jsonify
from finch import Finch, APIError # <-- Added APIError
import base64
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


@app.route('/')
def home():
    return render_template('index.html')


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

    # For demo purposes, simply sorting tokens in a csv. On prod use a porper DB with encryption!
    header = ['access_token', 'token_type', 'connection_id', 'customer_id',
              'account_id', 'client_type', 'company_id', 'connection_type',
              'products', 'provider_id']

    products_str = "|".join(create_access_token_response.products)

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
        create_access_token_response.provider_id
    ]

    file_exists = os.path.exists(CSV_FILE_PATH)
    
    with open(CSV_FILE_PATH, mode='a', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        if not file_exists:
            writer.writerow(header)
        writer.writerow(row_data)

    # Redirect to logged-in route
    return redirect('/company')

@app.route('/company')
def company():

    # Fetch the most recent access token from the .csv
    access_token = None
    with open(CSV_FILE_PATH, mode='r', newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        all_rows = list(reader)
        if len(all_rows) < 2: 
            return "Error: No token data found in file.", 500
        access_token = all_rows[-1][0]

    client = Finch(
        access_token=access_token,
    )

    # Get data, handles compatibility issues with custom message
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
        error_message = "Could not load company data."
        print(f"{e}")

    return render_template('company.html', company_data=company_data, error_message=error_message)

@app.route('/directory')
def directory():

    # Fetch the most recent access token from the .csv
    access_token = None
    with open(CSV_FILE_PATH, mode='r', newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        all_rows = list(reader)
        if len(all_rows) < 2: 
            return "Error: No token data found in file.", 500
        access_token = all_rows[-1][0]

    client = Finch(
        access_token=access_token,
    )

    # Get data, handles compatibility issues with custom message
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
        error_message = "Could not load directory data."
        print(f"{e}")

    return render_template('directory.html', directory_data=individuals, error_message=error_message)


@app.route('/directory/employee/<employee_id>')
def employee_detail(employee_id):
    
    # Fetch the most recent access token from the .csv
    access_token = None
    with open(CSV_FILE_PATH, mode='r', newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        all_rows = list(reader)
        if len(all_rows) < 2: 
            return "Error: No token data found in file.", 500
        access_token = all_rows[-1][0]

    client = Finch(
        access_token=access_token,
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
        employment_error = "Could not load employment data."
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
        individual_error = "Could not load individual data."
        print(f"{e}")

    return render_template('employee_detail.html',
                           individual=individual_data,
                           employment=employment_data,
                           individual_error=individual_error,
                           employment_error=employment_error)

    return "hi", 200
if __name__ == '__main__':
    app.run(debug=True)

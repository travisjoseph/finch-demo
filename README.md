# Finch Demo

This project is a submission for the DSE Role.


## Usage
1. Clone the repo
2. Add your envirnement variables in a `.env.local` file (an example file has been provided). Credentials can be found [here](https://dashboard.tryfinch.com/), after creating an account. On the Dasbhaord, add `http://localhost:5000/authorize` to your Redirect URIs.
3. Set up a vitual enviroment
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

The app should be running on `localhost:5000`. If it is not, please update the `REDIRECT_URI` in `.env.local`and on the Dashboard accordingly.
You can use demo credential found [here](https://developer.tryfinch.com/implementation-guide/Test/Finch-Sandbox#simulating-credential-flows) in order to connect to providers in Connect.


## Features
- Displays company information after connecting a provider
- Users can navigate to the employee directory
- Selecting an employee from the directory will display individual (personal) and employment information.
- If a provider does not support a specific field (null/None), it will display as *unavailable*.
- If a provider does not support an endpoint, a custom *unsupported for provider* error is displayed.
- Connect scopes are limited to the endpoints required for this demo.
- This app stores tokes in a `.csv` locally. **This is not inteded for production use**. If the tokens file does not exist, it will create one. If multiple providers are connected, the applicaiton will fetch data from the most recent provider by default. 